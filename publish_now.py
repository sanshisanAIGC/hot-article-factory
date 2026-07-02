"""一键发布脚本"""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

articles = json.load(open('data/articles_daily.json', 'r', encoding='utf-8'))
a = articles[0]
title = a['title']
content = a['content']

# 段落美化：双空行分隔
paras = [p.strip() for p in content.split('\n') if p.strip()]
formatted = '\n\n'.join(paras)

print(f'发布: {title[:40]}... ({len(formatted)}字)')

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir='data/toutiao_browser',
        headless=False,
        viewport={'width': 1280, 'height': 800},
    )
    page = ctx.new_page()

    # 1. 进仪表盘
    page.goto('https://mp.toutiao.com/', timeout=30000)
    page.wait_for_timeout(3000)

    # 2. Hover 发布 → 点文章
    page.locator("div:has-text('发布')").first.hover()
    page.wait_for_timeout(2000)
    page.get_by_text('文章', exact=True).first.click()
    page.wait_for_timeout(5000)

    # 3. 干掉 AI 助手
    page.evaluate("""
        document.querySelectorAll('.byte-drawer-mask, .byte-drawer-wrapper, .ai-assistant-drawer')
            .forEach(el => { el.style.display = 'none'; el.style.pointerEvents = 'none'; });
    """)
    page.wait_for_timeout(1000)

    # 4. 填标题
    page.evaluate("""
        const ti = document.querySelector('input[placeholder*="标题"]');
        if (ti) {
            ti.value = '';
            ti.focus();
        }
    """)
    page.keyboard.type(title, delay=50)
    page.wait_for_timeout(1000)

    # 5. 填正文（逐段输入，模拟真人）
    editor = page.locator('[contenteditable="true"]').first
    editor.click()
    page.wait_for_timeout(500)

    for para in paras:
        if para.strip():
            page.keyboard.type(para.strip())
            page.keyboard.press('Enter')
            page.keyboard.press('Enter')
            page.wait_for_timeout(200)
            print(f'  [段落] {para[:50]}...')

    page.wait_for_timeout(2000)
    print('内容填入完成')

    # 6. 再次干掉可能弹出的 AI 助手
    page.evaluate("""
        document.querySelectorAll('.byte-drawer-mask, .byte-drawer-wrapper')
            .forEach(el => { el.style.display = 'none'; el.style.pointerEvents = 'none'; });
    """)
    page.wait_for_timeout(1000)

    # 7. 点发布
    page.evaluate("""
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            if (btn.textContent.includes('发布') || btn.textContent.includes('发表')) {
                btn.click();
                break;
            }
        }
    """)
    page.wait_for_timeout(5000)

    page.screenshot(path='data/final_result.png')
    print(f'当前页面: {page.url}')
    print(f'标题: {page.title()}')
    print('浏览器保持打开，请检查结果')

    ctx.close()
