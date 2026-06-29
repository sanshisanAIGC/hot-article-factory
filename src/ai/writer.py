"""文章撰写器 — DeepSeek 驱动的热门文章写作"""
import json
import re
from .client import DeepSeekClient
from .prompts import ARTICLE_WRITE_PROMPT, ARTICLE_WRITE_USER


class ArticleWriter:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def write(self, topic: dict, background: str = "") -> dict:
        """围绕话题撰写一篇文章"""
        print(f"[Writer] 撰写: {topic.get('title', '?')[:40]}...")

        prompt = ARTICLE_WRITE_USER.format(
            topic_title=topic.get("title", ""),
            angle=topic.get("angle", "综合分析与深度评论"),
            background=background or f"来自{topic.get('platforms', ['多个平台'])}的热议话题",
            platforms=", ".join(topic.get("platforms", ["综合"])),
        )

        resp = self.client.chat_with_retry(
            system_prompt=ARTICLE_WRITE_PROMPT,
            user_prompt=prompt,
            temperature=0.8,
            max_tokens=4096,
        )

        article = self._parse_response(resp)

        # 验证字数
        content = article.get("content", "")
        word_count = len(content.replace("\n", "").replace(" ", ""))
        print(f"  《{article.get('title', '?')[:30]}》 {word_count}字")

        article["word_count"] = word_count
        article["topic"] = topic.get("title", "")
        return article

    def write_all(self, topics: list[dict]) -> list[dict]:
        """为所有话题写文章"""
        articles = []
        for topic in topics:
            article = self.write(topic)
            articles.append(article)
        return articles

    @staticmethod
    def _parse_response(resp: str) -> dict:
        m = re.search(r'\{.*\}', resp, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass

        # Fallback: treat as raw text
        lines = resp.strip().split("\n")
        title = lines[0].replace("#", "").strip() if lines else "热评文章"
        return {
            "title": title[:50],
            "content": resp,
            "tags": ["热议", "社会"],
            "summary": title[:50],
        }
