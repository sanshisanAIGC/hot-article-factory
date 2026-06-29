"""话题筛选器 — DeepSeek 驱动的热点话题筛选"""
import json
import re
from .client import DeepSeekClient
from .prompts import TOPIC_SELECT_PROMPT, TOPIC_SELECT_USER


class TopicSelector:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def select(self, topics: list[dict]) -> list[dict]:
        """从去重后的热点中选出 3 个最佳话题"""
        # 构建输入文本
        lines = []
        for i, t in enumerate(topics):
            platforms = ", ".join(t.get("platforms", [t.get("platform", "?")]))
            hot = t.get("hot", 0)
            lines.append(f"{i+1}. [{platforms}] {t['title']} (热度:{hot})")

        topics_text = "\n".join(lines)
        print(f"[Selector] 从 {len(topics)} 个话题中筛选...")

        resp = self.client.chat_with_retry(
            system_prompt=TOPIC_SELECT_PROMPT,
            user_prompt=TOPIC_SELECT_USER.format(topics_text=topics_text),
            temperature=0.5,
            max_tokens=2048,
        )

        selected = self._parse_response(resp)
        print(f"[Selector] 选出 {len(selected)} 个话题")
        for s in selected:
            print(f"  {s.get('title','?')} ({s.get('score',0)}分)")

        return selected

    @staticmethod
    def _parse_response(resp: str) -> list[dict]:
        m = re.search(r'\[.*\]', resp, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return []
