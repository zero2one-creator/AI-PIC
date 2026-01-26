from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app import crud
from app.core.db import engine
from app.enums import PointTransactionType, SubscriptionStatus, VipType
from app.models import Subscription
from app.services.config_service import get_config, refresh_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weekly_points_reward")


def _current_reward_week(now: datetime) -> str:
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def main() -> None:
    refresh_config()
    now = datetime.now(timezone.utc)
    reward_week = _current_reward_week(now)
    cfg = get_config()

    weekly_amount = int(cfg.get("weekly_reward", {}).get("weekly", 2000))
    lifetime_amount = int(cfg.get("weekly_reward", {}).get("lifetime", 3000))

    with Session(engine) as session:
        stmt = select(Subscription).where(
            Subscription.status == SubscriptionStatus.active,
        )
        subs = session.exec(stmt).all()

        awarded = 0
        skipped = 0
        for sub in subs:
            if sub.plan_type == VipType.weekly:
                amount = weekly_amount
            else:
                amount = lifetime_amount

            try:
                crud.change_points(
                    session=session,
                    user_id=sub.user_id,
                    delta=amount,
                    tx_type=PointTransactionType.reward,
                    reward_week=reward_week,
                )
                awarded += 1
            except IntegrityError:
                session.rollback()
                skipped += 1
            except Exception as e:
                session.rollback()
                logger.exception("failed rewarding user %s: %s", sub.user_id, e)

        logger.info("weekly reward done: week=%s awarded=%s skipped=%s", reward_week, awarded, skipped)


if __name__ == "__main__":  # pragma: no cover
    main()
