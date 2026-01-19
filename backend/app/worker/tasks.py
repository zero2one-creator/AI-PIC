"""
定时任务逻辑
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.core.redis_client import get_redis_client
from app.crud import add_points
from app.models import PointTransaction, Subscription

logger = logging.getLogger(__name__)

REWARD_LOCK_KEY = "points:weekly_reward:lock"
REWARD_LOCK_TTL_SECONDS = 60 * 30


def _get_reward_week(now: datetime) -> str:
    iso_year, iso_week, _ = now.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def award_weekly_points() -> None:
    """
    每周一 00:00 UTC 为周订阅用户发放积分
    """
    now = datetime.now(timezone.utc)
    reward_week = _get_reward_week(now)

    redis_client = get_redis_client()
    lock_value = str(uuid4())
    acquired = redis_client.acquire_lock(
        REWARD_LOCK_KEY,
        lock_value,
        expire_seconds=REWARD_LOCK_TTL_SECONDS,
    )
    if not acquired:
        logger.info("Weekly reward task already running, skip this run.")
        return

    try:
        with Session(engine) as session:
            subscription_user_ids = session.exec(
                select(Subscription.user_id)
                .where(Subscription.status == "active")
                .where(Subscription.plan_type == "weekly")
                .distinct()
            ).all()

            if not subscription_user_ids:
                logger.info("No active weekly subscriptions found.")
                return

            rewarded_user_ids = set(
                session.exec(
                    select(PointTransaction.user_id)
                    .where(PointTransaction.type == "reward")
                    .where(PointTransaction.reward_week == reward_week)
                ).all()
            )

            pending_user_ids = [
                user_id
                for user_id in subscription_user_ids
                if user_id not in rewarded_user_ids
            ]

            if not pending_user_ids:
                logger.info("Weekly reward already issued for all users.")
                return

            for user_id in pending_user_ids:
                try:
                    add_points(
                        session=session,
                        user_id=user_id,
                        amount=settings.POINTS_WEEKLY_REWARD,
                        point_type="reward",
                        reward_week=reward_week,
                    )
                except Exception as exc:
                    logger.error(
                        "Failed to grant weekly reward to user %s: %s",
                        user_id,
                        exc,
                    )

            logger.info(
                "Weekly reward issued: week=%s users=%d",
                reward_week,
                len(pending_user_ids),
            )
    finally:
        redis_client.release_lock(REWARD_LOCK_KEY, lock_value)
