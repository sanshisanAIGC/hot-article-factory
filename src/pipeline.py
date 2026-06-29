"""流程编排 — 抓热点 → 选话题 → 写文章 → 发布"""
import json
from pathlib import Path
from datetime import datetime

from src.ai.client import DeepSeekClient
from src.ai.selector import TopicSelector
from src.ai.writer import ArticleWriter
from src.ai.checker import FactChecker
from src.hot.fetcher import HotFetcher
from src.hot.parser import HotParser
try:
    from src.toutiao.publisher import ToutiaoPublisher
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    ToutiaoPublisher = None


class HotArticlePipeline:
    def __init__(self, deepseek_api_key: str, deepseek_base_url: str,
                 deepseek_model: str, data_dir: Path = None):
        self.data_dir = data_dir or Path("data")
        self.ai = DeepSeekClient(deepseek_api_key, deepseek_base_url, deepseek_model)
        self.selector = TopicSelector(self.ai)
        self.writer = ArticleWriter(self.ai)
        self.checker = FactChecker(self.ai)
        self.fetcher = HotFetcher()
        self.parser = HotParser()
        self.publisher = ToutiaoPublisher(self.data_dir) if HAS_PLAYWRIGHT else None

        self.topics_file = self.data_dir / "topics_daily.json"
        self.articles_file = self.data_dir / "articles_daily.json"
        self.published_file = self.data_dir / "published.json"

    # ━━━━ 步骤 ━━━━

    def step_fetch(self) -> dict:
        """Step 1 + 2: 抓取热点 + 去重"""
        print("\n" + "="*60)
        print("Step 1-2: 抓取热点 & 去重")
        print("="*60)

        raw = self.fetcher.fetch_all(limit=20)
        total = sum(len(v) for v in raw.values())
        if total == 0:
            raise RuntimeError("未能获取任何热点数据")

        unique = self.parser.deduplicate(raw)
        sorted_topics = self.parser.sort_by_hot(unique)

        # 保存
        self.topics_file.write_text(json.dumps(sorted_topics, ensure_ascii=False, indent=2), "utf-8")
        print(f"已保存 {len(sorted_topics)} 条话题到 {self.topics_file}")
        return {"raw": raw, "topics": sorted_topics}

    def step_select(self, topics: list[dict] = None) -> list[dict]:
        """Step 3: AI 选 3 个话题"""
        print("\n" + "="*60)
        print("Step 3: AI 筛选话题")
        print("="*60)

        if topics is None:
            if self.topics_file.exists():
                topics = json.loads(self.topics_file.read_text("utf-8"))
            else:
                raise RuntimeError("请先运行 step_fetch")

        selected = self.selector.select(topics)
        if not selected:
            raise RuntimeError("AI 未能选出话题")

        return selected

    def step_write(self, selected: list[dict] = None) -> list[dict]:
        """Step 4: AI 写 3 篇文章"""
        print("\n" + "="*60)
        print("Step 4: AI 撰写文章")
        print("="*60)

        if selected is None:
            raise RuntimeError("请先运行 step_select")

        articles = self.writer.write_all(selected)

        # 保存
        self.articles_file.write_text(json.dumps(articles, ensure_ascii=False, indent=2), "utf-8")
        print(f"已保存 {len(articles)} 篇文章到 {self.articles_file}")
        return articles

    def step_check(self, articles: list[dict] = None) -> list[dict]:
        """Step 4.5: AI 事实核查"""
        print("\n" + "="*60)
        print("Step 4.5: AI 事实核查")
        print("="*60)

        if articles is None:
            if self.articles_file.exists():
                articles = json.loads(self.articles_file.read_text("utf-8"))
            else:
                raise RuntimeError("请先运行 step_write")

        check_results = self.checker.check_all(articles)

        # 将核查结果附加到文章
        for article, check in zip(articles, check_results):
            article["fact_check"] = check

        # 重新保存带核查结果的文章
        self.articles_file.write_text(json.dumps(articles, ensure_ascii=False, indent=2), "utf-8")

        # 如有 FAIL，警告
        failed = [a for a in articles if a.get("fact_check", {}).get("verdict") == "FAIL"]
        if failed:
            print(f"\n[警告] {len(failed)} 篇文章事实核查不通过，建议修改后发布")

        return check_results

    def step_publish(self, article_index: int = None) -> list[dict]:
        """Step 5: 发布文章"""
        print("\n" + "="*60)
        print("Step 5: 发布到今日头条")
        print("="*60)

        if not HAS_PLAYWRIGHT:
            print("[警告] Playwright 未安装，无法发布。请运行: pip install playwright && playwright install chromium")
            return [{"success": False, "error": "Playwright not installed"}]

        if not self.articles_file.exists():
            raise RuntimeError("请先运行 step_write")

        articles = json.loads(self.articles_file.read_text("utf-8"))

        if article_index is not None:
            articles = [articles[article_index]]

        results = self.publisher.publish_all(articles)
        self._log_published(articles, results)
        return results

    def run_full(self):
        """完整流程: 抓→选→写→查→存草稿 (不发布, 等调度器分时发布)"""
        self.step_fetch()
        selected = self.step_select()
        articles = self.step_write(selected)
        checks = self.step_check(articles)

        print("\n" + "="*60)
        print("文章已准备就绪（已通过事实核查），等待定时发布:")
        for i, a in enumerate(articles):
            times = ["07:30", "12:00", "18:30"]
            verdict = a.get("fact_check", {}).get("verdict", "?")
            score = a.get("fact_check", {}).get("score", 0)
            print(f"  {times[i]} → 《{a.get('title', '?')[:40]}》({a.get('word_count', 0)}字) [{verdict} {score}分]")
        print("="*60)
        return articles

    # ━━━━ 持久化 ━━━━

    def _log_published(self, articles: list[dict], results: list[dict]):
        """记录已发布"""
        records = []
        if self.published_file.exists():
            records = json.loads(self.published_file.read_text("utf-8"))

        for i, (a, r) in enumerate(zip(articles, results)):
            records.append({
                "title": a.get("title", ""),
                "topic": a.get("topic", ""),
                "word_count": a.get("word_count", 0),
                "published_at": datetime.now().isoformat(),
                "success": r.get("success", False),
                "url": r.get("url", ""),
                "slot": ["07:30", "12:00", "18:30"][i % 3],
            })

        self.published_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), "utf-8")

    def get_daily_articles(self) -> list[dict]:
        """获取今日文章（供调度器分时发布）"""
        if self.articles_file.exists():
            return json.loads(self.articles_file.read_text("utf-8"))
        return []

    def get_stats(self) -> dict:
        """获取发布统计"""
        if self.published_file.exists():
            records = json.loads(self.published_file.read_text("utf-8"))
        else:
            records = []

        today = datetime.now().strftime("%Y-%m-%d")
        today_records = [r for r in records if r.get("published_at", "").startswith(today)]

        return {
            "total_published": len(records),
            "today_published": len(today_records),
            "today_success": sum(1 for r in today_records if r.get("success")),
        }
