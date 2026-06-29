"""AI 事实核查器 — 文章发布前的最后质量把关"""
import json
import re
from .client import DeepSeekClient
from .prompts import FACT_CHECK_PROMPT, FACT_CHECK_USER


class FactChecker:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def check(self, article: dict, background: str = "") -> dict:
        """核查单篇文章的事实性"""
        title = article.get("title", "")
        print(f"[Checker] 核查: {title[:40]}...")

        prompt = FACT_CHECK_USER.format(
            title=title,
            topic=article.get("topic", ""),
            platforms=", ".join(article.get("topic", {}).get("platforms", ["综合"])) if isinstance(article.get("topic"), dict) else "综合",
            content=article.get("content", "")[:5000],
            background=background or "无额外参考资料",
        )

        resp = self.client.chat_with_retry(
            system_prompt=FACT_CHECK_PROMPT,
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=2048,
        )

        result = self._parse_response(resp)
        verdict = result.get("verdict", "WARN")
        score = result.get("score", 0)

        emoji = {"PASS": "[OK]", "WARN": "[!]", "FAIL": "[X]"}
        print(f"  {emoji.get(verdict, '[?]')} {verdict} ({score}/10)")

        issues = result.get("issues", [])
        for issue in issues[:3]:
            print(f"    [{issue.get('severity','?')}] {issue.get('problem','')[:60]}")

        return result

    def check_all(self, articles: list[dict]) -> list[dict]:
        """核查所有文章，返回核查结果"""
        results = []
        for article in articles:
            result = self.check(article)
            results.append(result)

        # 汇总
        passed = sum(1 for r in results if r.get("verdict") == "PASS")
        failed = sum(1 for r in results if r.get("verdict") == "FAIL")
        avg_score = sum(r.get("score", 0) for r in results) / max(len(results), 1)

        print(f"\n[Checker] 核查完成: PASS {passed} | WARN {len(results)-passed-failed} | FAIL {failed}")
        print(f"[Checker] 平均分: {avg_score:.1f}/10")

        return results

    @staticmethod
    def _parse_response(resp: str) -> dict:
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', resp, re.DOTALL)
        if m:
            resp = m.group(1)
        try:
            return json.loads(resp)
        except json.JSONDecodeError:
            start = resp.find('{')
            end = resp.rfind('}')
            if start >= 0 and end > start:
                return json.loads(resp[start:end + 1])
            return {"verdict": "WARN", "score": 5, "issues": [],
                    "summary": "无法解析核查结果，建议人工复查"}
