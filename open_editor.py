"""打开头条编辑器，填入文章 + 搜索配图，保持浏览器开启"""
import json, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

articles = json.load(open('data/articles_daily.json', 'r', encoding='utf-8'))
a = articles[0]
TITLE = a['title']
CONTENT = a['content']

print(f'标题: {TITLE[:60]}')
print(f'字数: {len(CONTENT)}')

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir='data/toutiao_browser',
        headless=False,
        viewport={'width': 1280, 'height': 800},
    )
    page = ctx.new_page()

    # 1. 进编辑页
    page.goto('https://mp.toutiao.com/', timeout=30000)
    page.wait_for_timeout(3000)
    if 'login' in page.url:
        print('请扫码登录...')
        page.wait_for_url('**/profile_v4/**', timeout=300000)

    page.locator("div:has-text('发布')").first.hover()
    page.wait_for_timeout(2000)
    page.get_by_text('文章', exact=True).first.click()
    page.wait_for_timeout(5000)

    # 2. 干掉遮罩
    page.evaluate("""
        document.querySelectorAll('.byte-drawer-mask, .byte-drawer-wrapper')
            .forEach(function(el) { el.remove(); });
    """)
    page.wait_for_timeout(1000)

    # 3. 填标题 - 用 fill() 然后手动触发事件
    title_input = page.locator('input').filter(has=page.locator('[placeholder*="标题"]')).first
    # fallback: find any input with placeholder containing 标题
    if not title_input.is_visible():
        all_inputs = page.locator('input').all()
        for inp in all_inputs:
            ph = inp.get_attribute('placeholder') or ''
            if '标题' in ph:
                title_input = inp
                break

    title_input.click()
    title_input.fill('')  # 清空
    title_input.type(TITLE, delay=30)
    page.wait_for_timeout(1000)
    print('标题 OK')

    # 4. 填正文 - 用 editor.type() 自然输入
    editor = page.locator('[contenteditable="true"]').first
    editor.click()
    page.wait_for_timeout(500)

    lines = [l.strip() for l in CONTENT.split('\n') if l.strip()]
    for i, line in enumerate(lines):
        editor.type(line, delay=10)
        page.keyboard.press('Enter')
        if i % 4 == 3:  # 每4段留空行
            page.keyboard.press('Enter')

    page.wait_for_timeout(2000)
    print(f'正文 OK: {len(lines)}段')
    print('正文已填入，浏览器应该可以看到滚动条')

    # 5. 滚动到页面顶部确认标题可见
    page.evaluate('window.scrollTo(0, 0)')
    page.wait_for_timeout(500)

    # 6. 插入配图 - 搜索示意图
    print('\n尝试插入配图...')
    # 先找到插入图片按钮并点击
    img_btns = page.locator('[class*="toolbar"] button, [class*="editor"] button').all()
    for btn in img_btns:
        try:
            title_attr = btn.get_attribute('title') or ''
            text = btn.inner_text() or ''
            if '图片' in title_attr or '图片' in text or '插图' in title_attr:
                btn.click()
                page.wait_for_timeout(2000)
                print(f'点击了图片按钮: {title_attr or text[:20]}')
                break
        except:
            pass

    # 在图片搜索框中搜索关键词
    search_keywords = ['地震预警', '科技防灾', '地震']
    for kw in search_keywords:
        try:
            search_input = page.locator('input[placeholder*="搜索"]').last
            if search_input.is_visible(timeout=2000):
                search_input.fill(kw)
                page.keyboard.press('Enter')
                page.wait_for_timeout(3000)
                print(f'搜索配图: {kw}')

                # 点击第一张图片插入
                first_img = page.locator('[class*="image-item"], [class*="img-item"], img[class*="thumb"]').first
                if first_img.is_visible(timeout=2000):
                    first_img.click()
                    page.wait_for_timeout(1000)
                    # 确认插入
                    confirm_btn = page.locator('button:has-text("插入"), button:has-text("确定"), button:has-text("使用")').first
                    if confirm_btn.is_visible(timeout=2000):
                        confirm_btn.click()
                        page.wait_for_timeout(2000)
                        print(f'  已插入配图: {kw}')
                        break
        except Exception as e:
            print(f'  配图搜索失败({kw}): {e}')

    print('\n=== 浏览器已就绪 ===')
    print('文章标题和正文已填入，可以手动：')
    print('  1. 滚动查看全文')
    print('  2. 手动添加配图')
    print('  3. 检查标题是否显示')
    print('  4. 点击发布')
    print('\n保持浏览器开启中...完成后关闭窗口即可')

    time.sleep(999999)
