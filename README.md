# 热搜文章工厂 (Hot Article Factory)

> 每日自动抓取微博/抖音热搜 → AI 选题 → AI 写文 → AI 事实核查 → 定时发布到今日头条

## 工作流

```
06:00  抓取热搜 (微博 + 抖音)
06:05  AI 筛选 3 个最值得热议的话题
06:10  AI 撰写 3 篇评论文章 (800-1500字)
06:15  AI 事实核查 (数据/事件/引用/逻辑)
07:30  早高峰发布第1篇
12:00  午休发布第2篇
18:30  晚高峰发布第3篇
```

## 快速开始

```bash
pip install -r requirements.txt
playwright install chromium

# 登录今日头条创作者中心
python main.py login

# 运行完整流程 (抓热点 → AI写文 → 事实核查)
python main.py run

# 启动定时调度
python main.py schedule
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `python main.py run` | 完整流程 |
| `python main.py fetch` | 仅抓取热点 |
| `python main.py select` | AI 筛选话题 |
| `python main.py write` | AI 写文章 |
| `python main.py check` | AI 事实核查 |
| `python main.py publish` | 发布到头条 |
| `python main.py schedule` | 定时调度 |
| `python main.py status` | 查看状态 |

## 成本

DeepSeek v4 Pro: 每天约 $0.005，月成本约 $0.15

## License

MIT
