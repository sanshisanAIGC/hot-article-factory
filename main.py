#!/usr/bin/env python3
"""热搜文章工厂 - CLI 入口"""
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, validate_config
from src.pipeline import HotArticlePipeline
from src.toutiao.publisher import ToutiaoPublisher


def create_pipeline():
    return HotArticlePipeline(DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL)


def cmd_login(args):
    """登录今日头条"""
    pub = ToutiaoPublisher()
    pub.login()


def cmd_run(args):
    """完整流程：抓热点 + 选话题 + 写文章（不含发布）"""
    pipe = create_pipeline()
    pipe.run_full()


def cmd_fetch(args):
    """仅抓取热点"""
    pipe = create_pipeline()
    result = pipe.step_fetch()
    for t in result["topics"][:10]:
        print(f"  [{t.get('platforms',['?'])}] {t['title']}")


def cmd_select(args):
    """AI 筛选话题"""
    pipe = create_pipeline()
    selected = pipe.step_select()
    for i, t in enumerate(selected):
        print(f"\n{i+1}. {t['title']}")
        print(f"   评分: {t.get('score','?')} | 角度: {t.get('angle','')}")


def cmd_write(args):
    """AI 写文章"""
    pipe = create_pipeline()
    articles = pipe.step_write()
    for i, a in enumerate(articles):
        print(f"\n{i+1}. 《{a['title']}》 ({a.get('word_count',0)}字)")
        print(f"   {a['content'][:150]}...")


def cmd_check(args):
    """AI 事实核查"""
    pipe = create_pipeline()
    pipe.step_check()


def cmd_publish(args):
    """发布文章到头条"""
    pipe = create_pipeline()
    index = args.index if args.index is not None else None
    results = pipe.step_publish(index)
    for r in results:
        status = "OK" if r.get("success") else "FAIL"
        print(f"  [{status}] {r.get('title','?')[:40]} {r.get('url','')}")


def cmd_schedule(args):
    """启动定时调度"""
    from scheduler import run_scheduler
    run_scheduler()


def cmd_status(args):
    """查看状态"""
    pipe = create_pipeline()
    stats = pipe.get_stats()
    print(f"总发布: {stats['total_published']} 篇")
    print(f"今日发布: {stats['today_published']} 篇")

    articles = pipe.get_daily_articles()
    if articles:
        print(f"\n今日文章 ({len(articles)} 篇):")
        times = ["07:30", "12:00", "18:30"]
        for i, a in enumerate(articles):
            status = "已发" if i < stats['today_published'] else "待发"
            print(f"  [{status}] {times[i]} → 《{a.get('title','?')[:30]}》")


def main():
    parser = argparse.ArgumentParser(description="热搜文章工厂")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("login", help="登录今日头条创作者中心")
    sub.add_parser("run", help="完整流程：抓热点+选话题+写文章")
    sub.add_parser("fetch", help="仅抓取热点")
    sub.add_parser("select", help="AI筛选话题")
    sub.add_parser("write", help="AI写文章")
    sub.add_parser("check", help="AI事实核查")
    p = sub.add_parser("publish", help="发布文章")
    p.add_argument("--index", type=int, help="发布第几篇(0/1/2)，不指定则全发")
    sub.add_parser("schedule", help="启动定时调度")
    sub.add_parser("status", help="查看状态")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command != "login":
        missing = validate_config()
        if missing:
            print(f"缺少配置: {missing}")
            sys.exit(1)

    {"login": cmd_login, "run": cmd_run, "fetch": cmd_fetch,
     "select": cmd_select, "write": cmd_write, "check": cmd_check,
     "publish": cmd_publish, "schedule": cmd_schedule,
     "status": cmd_status}[args.command](args)


if __name__ == "__main__":
    main()
