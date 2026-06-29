"""热点解析去重"""
import re


class HotParser:
    """热点去重、合并、清洗"""

    @staticmethod
    def deduplicate(data: dict[str, list[dict]]) -> list[dict]:
        """
        三大平台热点去重合并
        通过标题相似度判断是否同一话题
        """
        all_items = []
        for platform, items in data.items():
            for item in items:
                item["platform"] = platform
                all_items.append(item)

        # 简单去重：标题关键词重叠 > 50% 视为重复
        unique = []
        seen_keywords = []

        for item in all_items:
            title = item.get("title", "")
            keywords = set(HotParser._extract_keywords(title))

            is_dup = False
            for prev_kw in seen_keywords:
                if not keywords:
                    continue
                overlap = len(keywords & prev_kw) / max(len(keywords | prev_kw), 1)
                if overlap > 0.5:
                    is_dup = True
                    # 保留热度更高的平台数据
                    for u in unique:
                        if set(HotParser._extract_keywords(u["title"])) == prev_kw:
                            if item.get("hot", 0) > u.get("hot", 0):
                                u.update(item)
                            u["platforms"] = list(set(u.get("platforms", [u["platform"]]) + [item["platform"]]))
                    break

            if not is_dup:
                item["platforms"] = [item["platform"]]
                unique.append(item)
                seen_keywords.append(keywords)

        print(f"[Parser] 去重: {len(all_items)} → {len(unique)} 条")
        return unique

    @staticmethod
    def _extract_keywords(title: str) -> list[str]:
        """从标题提取关键词"""
        # 移除标点、数字、常见停用词
        text = re.sub(r'[^一-鿿]', ' ', title)
        words = [w for w in text.split() if len(w) >= 2]
        # 停用词
        stopwords = {'今天', '一个', '这个', '什么', '怎么', '为什么',
                     '最新', '刚刚', '网友', '真的', '还是', '已经'}
        return [w for w in words if w not in stopwords]

    @staticmethod
    def sort_by_hot(items: list[dict]) -> list[dict]:
        """按热度排序"""
        return sorted(items, key=lambda x: x.get("hot", 0), reverse=True)
