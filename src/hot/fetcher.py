"""
热点数据获取器
直接请求各平台热搜接口，无需外部 API 服务
"""
import httpx
import re
import json


class HotFetcher:
    """多平台热搜获取器"""

    def __init__(self):
        self.client = httpx.Client(
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/125.0.0.0 Safari/537.36"
            }
        )

    # ━━━━━ 微博热搜 ━━━━━

    def fetch_weibo(self, limit: int = 20) -> list[dict]:
        """
        微博热搜榜
        接口: https://weibo.com/ajax/side/hotSearch
        """
        try:
            resp = self.client.get(
                "https://weibo.com/ajax/side/hotSearch",
                headers={"Referer": "https://weibo.com/"}
            )
            data = resp.json()
            items = data.get("data", {}).get("realtime", [])
            results = []
            for item in items[:limit]:
                word = item.get("word", "").strip()
                if not word or item.get("label_name") == "广告":
                    continue
                results.append({
                    "title": word,
                    "hot": item.get("num", 0),
                    "url": f"https://s.weibo.com/weibo?q={word}",
                    "platform": "weibo",
                })
            return results
        except Exception as e:
            print(f"[Fetcher] 微博热搜获取失败: {e}")
            return []

    # ━━━━ 知乎热榜 ━━━━━

    def fetch_zhihu(self, limit: int = 20) -> list[dict]:
        """
        知乎热榜
        接口: https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total
        """
        # Try primary API
        try:
            resp = self.client.get(
                "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total",
                params={"limit": limit, "desktop": "true"},
                headers={
                    "Referer": "https://www.zhihu.com/hot",
                    "Accept": "application/json",
                }
            )
            data = resp.json()
            items = data.get("data", [])
            if items:
                results = []
                for item in items[:limit]:
                    target = item.get("target", {})
                    title = target.get("title", "").strip()
                    if not title:
                        continue
                    results.append({
                        "title": title,
                        "hot": int(target.get("follower_count", target.get("hot_score", 0))),
                        "url": target.get("url", f"https://www.zhihu.com/question/{target.get('id', '')}"),
                        "excerpt": target.get("excerpt", "")[:100],
                        "platform": "zhihu",
                    })
                if results:
                    return results
        except Exception:
            pass

        # Fallback: Zhihu hot list via alternative endpoint
        try:
            resp = self.client.get(
                "https://www.zhihu.com/billboard",
                headers={"Referer": "https://www.zhihu.com/"},
                follow_redirects=True,
            )
            html = resp.text
            # Extract from JSON embedded in page
            import re
            match = re.search(r'<script id="js-initialData" type="text/json">(.*?)</script>', html)
            if match:
                data = json.loads(match.group(1))
                hot_list = (data.get("initialState", {})
                           .get("topstory", {})
                           .get("hotList", []))
                results = []
                for item in hot_list[:limit]:
                    title = item.get("target", {}).get("titleArea", {}).get("text", "")
                    if not title:
                        title = item.get("target", {}).get("title", "")
                    if not title:
                        continue
                    results.append({
                        "title": title.strip(),
                        "hot": item.get("target", {}).get("metricsArea", {}).get("text", "0"),
                        "url": item.get("target", {}).get("link", {}).get("url", ""),
                        "platform": "zhihu",
                    })
                return results
        except Exception as e:
            print(f"[Fetcher] 知乎热榜 Fallback 失败: {e}")

        return []

    # ━━━━ 抖音热点 ━━━━━

    def fetch_douyin(self, limit: int = 20) -> list[dict]:
        """
        抖音热点榜
        接口: 第三方聚合 (官方接口需 Token)
        """
        try:
            # 使用可公开访问的第三方聚合
            resp = self.client.get(
                "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/",
                headers={"Referer": "https://www.douyin.com/"}
            )
            data = resp.json()
            items = data.get("word_list", [])
            results = []
            for item in items[:limit]:
                word = item.get("word", "").strip()
                if not word:
                    continue
                results.append({
                    "title": word,
                    "hot": item.get("hot_value", 0),
                    "url": f"https://www.douyin.com/search/{word}",
                    "platform": "douyin",
                })
            return results
        except Exception:
            pass

        # Fallback: 使用备用接口
        try:
            resp = self.client.get(
                "https://tenapi.cn/v2/douyinhot",
                headers={"Referer": "https://tenapi.cn/"}
            )
            data = resp.json()
            if data.get("code") == 200:
                items = data.get("data", [])
                results = []
                for item in items[:limit]:
                    results.append({
                        "title": item.get("name", "").strip(),
                        "hot": item.get("hot_value", item.get("hot", 0)),
                        "url": f"https://www.douyin.com/search/{item.get('name', '')}",
                        "platform": "douyin",
                    })
                return results
        except Exception as e:
            print(f"[Fetcher] 抖音热点获取失败: {e}")

        return []

    # ━━━━ 全部获取 ━━━━━

    def fetch_all(self, limit: int = 20) -> dict[str, list[dict]]:
        """获取三大平台热搜"""
        print("[Fetcher] 抓取微博热搜...")
        weibo = self.fetch_weibo(limit)
        print(f"  微博: {len(weibo)} 条")

        print("[Fetcher] 抓取知乎热榜...")
        zhihu = self.fetch_zhihu(limit)
        print(f"  知乎: {len(zhihu)} 条")

        print("[Fetcher] 抓取抖音热点...")
        douyin = self.fetch_douyin(limit)
        print(f"  抖音: {len(douyin)} 条")

        return {
            "weibo": weibo,
            "zhihu": zhihu,
            "douyin": douyin,
        }

    def close(self):
        self.client.close()
