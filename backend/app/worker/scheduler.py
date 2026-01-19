"""
定时任务调度器
"""

import logging
from datetime import timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.worker.tasks import award_weekly_points

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    scheduler = BlockingScheduler(timezone=timezone.utc)
    scheduler.add_job(
        award_weekly_points,
        CronTrigger(day_of_week="mon", hour=0, minute=0),
        id="weekly_reward",
        replace_existing=True,
    )
    logger.info("Scheduler started. Weekly reward job is scheduled at 00:00 UTC on Mondays.")
    scheduler.start()


if __name__ == "__main__":
    main()
