from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, delete

from app.api.deps import get_db
from app.main import app
from app.models import (
    EmojiTask,
    Order,
    PointTransaction,
    Subscription,
    User,
    UserPoints,
)


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def db(engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
        # Clean tables after each test (children first).
        session.exec(delete(PointTransaction))
        session.exec(delete(EmojiTask))
        session.exec(delete(Order))
        session.exec(delete(Subscription))
        session.exec(delete(UserPoints))
        session.exec(delete(User))
        session.commit()


@pytest.fixture(scope="function")
def client(engine) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

