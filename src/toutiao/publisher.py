"""
今日头条发布器 — Playwright 持久化浏览器上下文
"""
import time, json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


class ToutiaoPublisher:
    def __init__(self, data_dir: Path = None, headless: bool = False):
        self.data_dir = data_dir or Path("data")
        self.user_data_dir = self.data_dir / "toutiao_browser"
        self.headless = headless

    def login(self):
        """扫码登录，持久化浏览器上下文"""
        print("[Toutiao] 打开浏览器，请在窗口中扫码登录...")
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=False,
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            page.goto("https://mp.toutiao.com/")
            print("[Toutiao] 等待登录（检测到仪表盘即完成）...")
            try:
                page.wait_for_url("**/profile_v4/**", timeout=300000)
                print("[Toutiao] 登录成功!")
            except PWTimeout:
                if "login" not in page.url.lower():
                    print("[Toutiao] 已登录")
                else:
                    print("[Toutiao] 超时，请重试")
                    ctx.close()
                    return False
            ctx.close()
            return True

    def is_logged_in(self) -> bool:
        return (self.user_data_dir / "Default").exists()

    def publish_article(self, title: str, content: str, tags: list[str] = None) -> dict:
        """发布一篇图文"""
        if not self.is_logged_in():
            return {"success": False, "error": "未登录"}

        print(f"[Toutiao] 发布: {title[:40]}...")

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=self.headless,
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()

            try:
                # 1. 进入仪表盘
                page.goto("https://mp.toutiao.com/", timeout=30000)
                page.wait_for_timeout(3000)

                if "login" in page.url:
                    return {"success": False, "error": "需要重新登录"}

                # 2. Hover "发布" 展开下拉菜单
                publish_div = page.locator("div:has-text('发布')").first
                publish_div.hover()
                page.wait_for_timeout(2000)

                # 3. 点击下拉中的 "文章"
                article_link = page.get_by_text("文章", exact=True).first
                if article_link.is_visible():
                    article_link.click()
                    page.wait_for_timeout(5000)
                else:
                    page.goto("https://mp.toutiao.com/profile_v4/graphic/publish", timeout=30000)
                    page.wait_for_timeout(5000)

                print(f"[Toutiao] 编辑页: {page.url[:80]}")

                # 检查是否成功进入编辑页
                if "publish" not in page.url.lower() and "graphic" not in page.url.lower():
                    page.goto("https://mp.toutiao.com/profile_v4/graphic/publish", timeout=30000)
                    page.wait_for_timeout(5000)

                # 3.5 移除 AI 助手遮罩（暴力 JS）
                page.evaluate("""
                    document.querySelectorAll('.byte-drawer-mask, .byte-drawer-wrapper')
                        .forEach(el => el.remove());
                """)
                page.wait_for_timeout(2000)
                print("[Toutiao] 已移除遮挡层")

                # 4. 用 JS 直接填标题和正文
                js_content = content.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
                js_title = title.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

                page.evaluate(f"""
                    // 填标题
                    const titleInput = document.querySelector('input[placeholder*="标题"]') ||
                                      document.querySelector('[class*="title"] input') ||
                                      document.querySelector('input[maxlength]');
                    if (titleInput) {{
                        titleInput.value = '';
                        titleInput.focus();
                        document.execCommand('insertText', false, `{js_title}`);
                        titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        titleInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}

                    // 填正文
                    const editor = document.querySelector('[contenteditable="true"]') ||
                                   document.querySelector('.ProseMirror') ||
                                   document.querySelector('.publish-editor');
                    if (editor) {{
                        editor.focus();
                        const ps = `{js_content}`.split('\\n').filter(p => p.trim());
                        const html = ps.map(p => '<p>' + p.trim() + '</p>').join('');
                        editor.innerHTML = html;
                        editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                """)
                page.wait_for_timeout(3000)
                print("[Toutiao] 内容已填入")

                # 5. 点击发布按钮（用 JS 查找并点击）
                clicked = page.evaluate("() => { const bs = document.querySelectorAll('button'); for (const b of bs) { if (b.textContent.includes('发布') || b.textContent.includes('发表')) { b.click(); return true; } } return false; }")
                if clicked:
                    page.wait_for_timeout(5000)
                    print("[Toutiao] 已点击发布!")

                page.screenshot(path=str(self.data_dir / "publish_result.png"))
                print(f"[Toutiao] 结果页: {page.url[:80]}")
                return {"success": True, "url": page.url, "title": title}

            except Exception as e:
                try:
                    page.screenshot(path=str(self.data_dir / "publish_error.png"))
                except:
                    pass
                print(f"[Toutiao] 错误: {e}")
                import traceback
                traceback.print_exc()
                return {"success": False, "error": str(e)}
            finally:
                ctx.close()

    def publish_all(self, articles: list[dict]) -> list[dict]:
        results = []
        for i, article in enumerate(articles):
            result = self.publish_article(
                title=article.get("title", ""),
                content=article.get("content", ""),
                tags=article.get("tags", []),
            )
            results.append(result)
            if i < len(articles) - 1 and result.get("success"):
                wait = 300
                print(f"[Toutiao] 等待 {wait}s ...")
                time.sleep(wait)
        return results
