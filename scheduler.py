#!/usr/bin/env python3
"""定时调度器 — 每天06:00抓热点写文章，07:30/12:00/18:30分时发布"""
import sys, time, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import schedule
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from src.pipeline import HotArticlePipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("hot-article-factory")


class ArticleScheduler:
    def __init__(self):
        self.pipeline = HotArticlePipeline(
            DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
        )

    def prepare_articles(self):
        """06:00 抓热点 + 写文章 + 事实核查"""
        logger.info("=" * 50)
        logger.info("开始准备今日文章...")
        try:
            self.pipeline.run_full()
            logger.info("文章准备完成！")
        except Exception as e:
            logger.error(f"准备文章失败: {e}")

    def publish_slot_0(self):
        self._publish(0)

    def publish_slot_1(self):
        self._publish(1)

    def publish_slot_2(self):
        self._publish(2)

    def _publish(self, index: int):
        """发布指定槽位的文章"""
        times = ["07:30", "12:00", "18:30"]
        try:
            results = self.pipeline.step_publish(index)
            for r in results:
                if r.get("success"):
                    logger.info(f"[{times[index]}] 发布成功: {r.get('title','')[:40]}")
                else:
                    logger.error(f"[{times[index]}] 发布失败: {r.get('error','')}")
        except Exception as e:
            logger.error(f"[{times[index]}] 发布异常: {e}")


def run_scheduler():
    sched = ArticleScheduler()

    # 06:00 准备当天文章
    schedule.every().day.at("06:00").do(sched.prepare_articles)

    # 三个黄金时段发布
    schedule.every().day.at("07:30").do(sched.publish_slot_0)
    schedule.every().day.at("12:00").do(sched.publish_slot_1)
    schedule.every().day.at("18:30").do(sched.publish_slot_2)

    logger.info("热搜文章工厂调度器已启动")
    logger.info("  06:00 - 抓热点&AI写文章")
    logger.info("  07:30 - 早高峰发布")
    logger.info("  12:00 - 午休发布")
    logger.info("  18:30 - 晚高峰发布")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("调度器已停止")


if __name__ == "__main__":
    run_scheduler()
