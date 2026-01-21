from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.core.security import generate_snowflake_id, get_password_hash, verify_password
from app.models import (
    EmojiTask,
    EmojiTaskCreate,
    EmojiTaskUpdate,
    Item,
    ItemCreate,
    Order,
    OrderCreate,
    OrderUpdate,
    PointTransaction,
    PointTransactionCreate,
    Subscription,
    SubscriptionCreate,
    SubscriptionUpdate,
    User,
    UserCreate,
    UserPoints,
    UserUpdate,
)


# ============================================================================
# User CRUD
# ============================================================================


def create_user(*, session: Session, user_create: UserCreate) -> User:
    """创建用户(邮箱注册)"""
    db_obj = User.model_validate(
        user_create,
        update={
            "id": generate_snowflake_id(),
            "hashed_password": get_password_hash(user_create.password),
        },
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def create_user_by_device(*, session: Session, device_id: str) -> User:
    """通过设备ID创建用户"""
    user = User(
        id=generate_snowflake_id(),
        device_id=device_id,
        is_active=True,
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # 初始化积分账户
    user_points = UserPoints(
        id=generate_snowflake_id(),
        user_id=user.id,
        balance=0,
        updated_at=datetime.utcnow(),
    )
    session.add(user_points)
    session.commit()

    return user


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    """更新用户信息"""
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    db_user.updated_at = datetime.utcnow()
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    """通过邮箱查询用户"""
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def get_user_by_device_id(*, session: Session, device_id: str) -> User | None:
    """通过设备ID查询用户"""
    statement = select(User).where(User.device_id == device_id)
    session_user = session.exec(statement).first()
    return session_user


def get_user_by_id(*, session: Session, user_id: int) -> User | None:
    """通过ID查询用户"""
    return session.get(User, user_id)


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    """邮箱密码认证"""
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not db_user.hashed_password:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def authenticate_by_device(*, session: Session, device_id: str) -> User:
    """设备ID认证(自动注册)"""
    db_user = get_user_by_device_id(session=session, device_id=device_id)
    if not db_user:
        # 自动创建用户
        db_user = create_user_by_device(session=session, device_id=device_id)
    return db_user


# ============================================================================
# Item CRUD (保留原有功能)
# ============================================================================


def create_item(*, session: Session, item_in: ItemCreate, owner_id: int) -> Item:
    """创建项目"""
    db_item = Item.model_validate(
        item_in,
        update={
            "id": generate_snowflake_id(),
            "owner_id": owner_id,
        },
    )
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


# ============================================================================
# Points CRUD
# ============================================================================


def get_user_points(*, session: Session, user_id: int) -> UserPoints | None:
    """获取用户积分账户"""
    statement = select(UserPoints).where(UserPoints.user_id == user_id)
    return session.exec(statement).first()


def init_user_points(*, session: Session, user_id: int) -> UserPoints:
    """初始化用户积分账户"""
    user_points = UserPoints(
        id=generate_snowflake_id(),
        user_id=user_id,
        balance=0,
        updated_at=datetime.utcnow(),
    )
    session.add(user_points)
    session.commit()
    session.refresh(user_points)
    return user_points


def consume_points(
    *,
    session: Session,
    user_id: int,
    amount: int,
    task_type: str | None = None,
) -> tuple[bool, str]:
    """
    扣减积分

    Returns:
        (是否成功, 错误信息)
    """
    # 获取积分账户
    user_points = get_user_points(session=session, user_id=user_id)
    if not user_points:
        user_points = init_user_points(session=session, user_id=user_id)

    # 检查余额
    if user_points.balance < amount:
        return False, "积分余额不足"

    # 扣减积分
    user_points.balance -= amount
    user_points.updated_at = datetime.utcnow()
    session.add(user_points)

    # 记录流水
    transaction = PointTransaction(
        id=generate_snowflake_id(),
        user_id=user_id,
        type="consume",
        amount=-amount,
        balance_after=user_points.balance,
        task_type=task_type,
        created_at=datetime.utcnow(),
    )
    session.add(transaction)

    session.commit()
    return True, ""


def add_points(
    *,
    session: Session,
    user_id: int,
    amount: int,
    point_type: str,
    order_id: str | None = None,
    reward_week: str | None = None,
) -> UserPoints:
    """
    增加积分

    Args:
        user_id: 用户ID
        amount: 积分数量
        point_type: 类型 (purchase/reward)
        order_id: 订单号
        reward_week: 奖励周(如 2024-W03)
    """
    # 获取积分账户
    user_points = get_user_points(session=session, user_id=user_id)
    if not user_points:
        user_points = init_user_points(session=session, user_id=user_id)

    # 增加积分
    user_points.balance += amount
    user_points.updated_at = datetime.utcnow()
    session.add(user_points)

    # 记录流水
    transaction = PointTransaction(
        id=generate_snowflake_id(),
        user_id=user_id,
        type=point_type,
        amount=amount,
        balance_after=user_points.balance,
        order_id=order_id,
        reward_week=reward_week,
        created_at=datetime.utcnow(),
    )
    session.add(transaction)

    session.commit()
    session.refresh(user_points)
    return user_points


def get_point_transactions(
    *,
    session: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[PointTransaction]:
    """获取积分流水"""
    statement = (
        select(PointTransaction)
        .where(PointTransaction.user_id == user_id)
        .order_by(PointTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(session.exec(statement).all())


# ============================================================================
# Subscription CRUD
# ============================================================================


def create_subscription(
    *, session: Session, subscription_in: SubscriptionCreate
) -> Subscription:
    """创建订阅"""
    db_obj = Subscription.model_validate(
        subscription_in,
        update={
            "id": generate_snowflake_id(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_subscription(
    *, session: Session, db_subscription: Subscription, subscription_in: SubscriptionUpdate
) -> Subscription:
    """更新订阅"""
    subscription_data = subscription_in.model_dump(exclude_unset=True)
    db_subscription.sqlmodel_update(subscription_data)
    db_subscription.updated_at = datetime.utcnow()
    session.add(db_subscription)
    session.commit()
    session.refresh(db_subscription)
    return db_subscription


def get_user_active_subscription(
    *, session: Session, user_id: int
) -> Subscription | None:
    """获取用户活跃订阅"""
    statement = (
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .where(Subscription.status == "active")
        .order_by(Subscription.created_at.desc())
    )
    return session.exec(statement).first()


# ============================================================================
# Order CRUD
# ============================================================================


def create_order(*, session: Session, order_in: OrderCreate) -> Order:
    """创建订单"""
    db_obj = Order.model_validate(
        order_in,
        update={
            "id": generate_snowflake_id(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_order(*, session: Session, db_order: Order, order_in: OrderUpdate) -> Order:
    """更新订单"""
    order_data = order_in.model_dump(exclude_unset=True)
    db_order.sqlmodel_update(order_data)
    db_order.updated_at = datetime.utcnow()
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    return db_order


def get_order_by_no(*, session: Session, order_no: str) -> Order | None:
    """通过订单号查询订单"""
    statement = select(Order).where(Order.order_no == order_no)
    return session.exec(statement).first()


# ============================================================================
# EmojiTask CRUD
# ============================================================================


def create_emoji_task(*, session: Session, task_in: EmojiTaskCreate) -> EmojiTask:
    """创建表情包任务"""
    db_obj = EmojiTask.model_validate(
        task_in,
        update={
            "id": generate_snowflake_id(),
            "created_at": datetime.utcnow(),
        },
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_emoji_task(
    *, session: Session, db_task: EmojiTask, task_in: EmojiTaskUpdate
) -> EmojiTask:
    """更新表情包任务"""
    task_data = task_in.model_dump(exclude_unset=True)
    db_task.sqlmodel_update(task_data)
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


def get_emoji_task_by_id(*, session: Session, task_id: int) -> EmojiTask | None:
    """通过ID查询任务"""
    return session.get(EmojiTask, task_id)


def get_user_emoji_tasks(
    *,
    session: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[EmojiTask]:
    """获取用户的表情包任务列表"""
    statement = (
        select(EmojiTask)
        .where(EmojiTask.user_id == user_id)
        .order_by(EmojiTask.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(session.exec(statement).all())
