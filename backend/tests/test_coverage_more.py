from __future__ import annotations

import asyncio
import json
import time

import httpx
import jwt
import pytest
from fastapi import HTTPException
from sqlmodel import Session, delete, select

from app import crud
from app.api import deps
from app.api.errors import AppError, insufficient_points
from app.core import db as core_db
from app.core import snowflake
from app.core.config import Settings, settings
from app.core.redis import get_redis
from app.enums import VipType
from app.integrations import oss as oss_mod
from app.integrations.aliyun_emoji import AliyunEmojiClient
from app.integrations.oss import (
    _build_host,
    build_object_url,
    upload_from_url,
)
from app.models import UserPoints
from app.services import config_service


def test_login_twice_same_user(client):
    r1 = client.post("/api/v1/auth/login", json={"device_id": "device_same"})
    r2 = client.post("/api/v1/auth/login", json={"device_id": "device_same"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["data"]["user"]["id"] == r2.json()["data"]["user"]["id"]


def test_health_check(client):
    r = client.get("/api/v1/utils/health-check/")
    assert r.status_code == 200
    assert r.json() is True


def test_validation_error_handler(client):
    # device_id min_length=1 -> triggers RequestValidationError
    r = client.post("/api/v1/auth/login", json={"device_id": ""})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == 422000
    assert body["data"]["errors"]


def test_http_exception_handler_dict_branch():
    from app import main as app_main

    exc = HTTPException(status_code=418, detail={"code": 418001, "message": "teapot"})
    resp = asyncio.run(app_main.http_error_handler(None, exc))  # type: ignore[arg-type]
    assert resp.status_code == 418
    assert resp.body  # JSONResponse body bytes


def test_deps_invalid_token_paths(client):
    # Totally invalid JWT
    r = client.get("/api/v1/user/profile", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401

    # Valid JWT but sub is not int
    token = jwt.encode({"sub": "abc", "exp": int(time.time()) + 60}, settings.SECRET_KEY, algorithm="HS256")
    r = client.get("/api/v1/user/profile", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401

    # Valid JWT but missing sub
    token = jwt.encode({"exp": int(time.time()) + 60}, settings.SECRET_KEY, algorithm="HS256")
    r = client.get("/api/v1/user/profile", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401

    # Valid JWT but user doesn't exist
    token = jwt.encode({"sub": "999999999", "exp": int(time.time()) + 60}, settings.SECRET_KEY, algorithm="HS256")
    r = client.get("/api/v1/user/profile", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_get_db_generator_uses_engine_override(engine, monkeypatch):
    # Cover app.api.deps.get_db (default engine is Postgres; override for test).
    monkeypatch.setattr(deps, "engine", engine)
    gen = deps.get_db()
    session = next(gen)
    session.exec(select(1))
    gen.close()


def test_snowflake_edge_cases(monkeypatch):
    with pytest.raises(ValueError):
        snowflake.Snowflake(node_id=-1)

    # Cover ts < last_ts branch and _wait_until in next_id.
    sf = snowflake.Snowflake(node_id=1)
    sf._last_ts = 1000  # type: ignore[attr-defined]
    monkeypatch.setattr(snowflake.Snowflake, "_now_ms", staticmethod(lambda: 999))
    monkeypatch.setattr(snowflake.Snowflake, "_wait_until", classmethod(lambda cls, t: t))
    _ = sf.next_id()

    # Cover sequence rollover branch.
    sf2 = snowflake.Snowflake(node_id=1)
    sf2._last_ts = 2000  # type: ignore[attr-defined]
    sf2._seq = 0xFFF  # type: ignore[attr-defined]
    monkeypatch.setattr(snowflake.Snowflake, "_now_ms", staticmethod(lambda: 2000))
    monkeypatch.setattr(snowflake.Snowflake, "_wait_until", classmethod(lambda cls, t: t))
    _ = sf2.next_id()

    # _wait_until loop is covered in a dedicated test.


def test_snowflake_wait_until_loop(monkeypatch):
    calls = [0, 0, 5]

    def fake_now_ms() -> int:
        return calls.pop(0) if calls else 5

    monkeypatch.setattr(snowflake.Snowflake, "_now_ms", staticmethod(fake_now_ms))
    monkeypatch.setattr(time, "sleep", lambda _: None)
    assert snowflake.Snowflake._wait_until(5) == 5


def test_settings_validation_paths():
    # parse_cors branches
    from app.core.config import parse_cors

    assert parse_cors(["a"]) == ["a"]
    with pytest.raises(ValueError):
        parse_cors(123)

    # Non-local env should reject default secrets.
    with pytest.raises(ValueError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="changethis",
            POSTGRES_PASSWORD="not-changethis",
            PROJECT_NAME="x",
            POSTGRES_SERVER="localhost",
            POSTGRES_USER="postgres",
            POSTGRES_DB="app",
        )


def test_config_service_missing_file_branch(monkeypatch):
    config_service.refresh_config()

    orig_exists = config_service.Path.exists

    def fake_exists(_self):  # type: ignore[no-untyped-def]
        return False

    monkeypatch.setattr(config_service.Path, "exists", fake_exists)
    cfg = config_service.refresh_config()
    assert cfg == {"banners": [], "styles": [], "points_rules": {}}
    monkeypatch.setattr(config_service.Path, "exists", orig_exists)


def test_oss_host_and_missing_config(monkeypatch):
    assert _build_host("b", "oss-cn-hangzhou.aliyuncs.com").startswith("https://b.")
    assert _build_host("b", "https://oss-cn-hangzhou.aliyuncs.com").startswith("https://b.")

    monkeypatch.setattr(settings, "OSS_ENDPOINT", None)
    monkeypatch.setattr(settings, "OSS_BUCKET", None)
    monkeypatch.setattr(settings, "OSS_ACCESS_KEY_ID", None)
    monkeypatch.setattr(settings, "OSS_ACCESS_KEY_SECRET", None)
    with pytest.raises(AppError):
        build_object_url(key="a/b.jpg")


def test_aliyun_emoji_non_mock_config_error():
    client = AliyunEmojiClient()
    client._mock = False  # type: ignore[attr-defined]
    client._api_key = None  # type: ignore[attr-defined]
    with pytest.raises(AppError):
        client.detect(image_url="https://example.com/a.jpg")


def test_misc_helpers_covered(engine):
    # Cover init_db hook.
    with Session(engine) as session:
        core_db.init_db(session)

    # Cover get_redis factory (doesn't connect until used).
    r = get_redis()
    assert hasattr(r, "xadd")

    # Cover insufficient_points helper.
    e = insufficient_points()
    assert e.code == 402001


def test_prestart_and_seed_scripts(engine, monkeypatch):
    from app import backend_pre_start, initial_data, tests_pre_start

    # Point the scripts to the test engine so they can run without Postgres.
    monkeypatch.setattr(backend_pre_start, "engine", engine)
    monkeypatch.setattr(tests_pre_start, "engine", engine)
    monkeypatch.setattr(initial_data, "engine", engine)

    backend_pre_start.init(engine)
    backend_pre_start.main()

    tests_pre_start.init(engine)
    tests_pre_start.main()

    initial_data.init()
    initial_data.main()


def test_config_service_file_load(monkeypatch):
    config_service.refresh_config()

    sample = {
        "banners": [{"id": 1}],
        "styles": [{"category": "x", "templates": []}],
        "points_rules": {"emoji": 123},
        "points_packs": {"points_1000": 1000},
        "vip_products": {"weekly_001": "weekly"},
        "weekly_reward": {"weekly": 2000, "lifetime": 3000},
    }

    def fake_exists(_self):  # type: ignore[no-untyped-def]
        return True

    def fake_read_text(_self, encoding="utf-8"):  # type: ignore[no-untyped-def]
        return json.dumps(sample)

    monkeypatch.setattr(config_service.Path, "exists", fake_exists)
    monkeypatch.setattr(config_service.Path, "read_text", fake_read_text)
    monkeypatch.setattr(config_service, "_config", None)

    cfg = config_service.refresh_config()
    assert cfg["banners"][0]["id"] == 1
    assert cfg["styles"][0]["category"] == "x"
    assert cfg["points_rules"]["emoji"] == 123
    assert cfg["points_packs"]["points_1000"] == 1000
    assert cfg["vip_products"]["weekly_001"] == "weekly"
    assert cfg["weekly_reward"]["weekly"] == 2000


def test_aliyun_emoji_client_http_paths(monkeypatch):
    # Cover non-mock detect/create/get flows without hitting network.
    client = AliyunEmojiClient()
    client._mock = False  # type: ignore[attr-defined]
    client._api_key = "k"  # type: ignore[attr-defined]

    class FakeResp:
        def __init__(self, data):  # type: ignore[no-untyped-def]
            self._data = data

        def raise_for_status(self):  # type: ignore[no-untyped-def]
            return None

        def json(self):  # type: ignore[no-untyped-def]
            return self._data

    queue: list[dict] = [
        {"output": {"bbox_face": [1, 2, 3, 4], "ext_bbox_face": [1, 2, 3, 5]}},
        {"output": {"task_id": "t1", "task_status": "PENDING"}, "request_id": "r1"},
        {
            "output": {
                "task_status": "SUCCEEDED",
                "video_url": "https://example.com/v.mp4",
            }
        },
    ]

    class FakeHttpxClient:
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            _ = args, kwargs

        def __enter__(self):  # type: ignore[no-untyped-def]
            return self

        def __exit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
            return False

        def post(self, url, json=None, headers=None):  # type: ignore[no-untyped-def]
            _ = url, json, headers
            return FakeResp(queue.pop(0))

        def get(self, url, headers=None):  # type: ignore[no-untyped-def]
            _ = url, headers
            return FakeResp(queue.pop(0))

    monkeypatch.setattr(httpx, "Client", FakeHttpxClient)

    det = client.detect(image_url="https://example.com/a.jpg")
    assert det.passed is True

    created = client.create_task(
        image_url="https://example.com/a.jpg",
        driven_id="emoji_001",
        face_bbox=[1, 2, 3, 4],
        ext_bbox=[1, 2, 3, 5],
    )
    assert created.task_id == "t1"

    task = client.get_task(task_id="t1")
    assert task.task_status == "SUCCEEDED"
    assert task.video_url == "https://example.com/v.mp4"


def test_oss_upload_from_url(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "OSS_PUBLIC_BASE_URL", "https://cdn.example.com")
    assert build_object_url(key="a/b.jpg") == "https://cdn.example.com/a/b.jpg"

    monkeypatch.setattr(settings, "OSS_PUBLIC_BASE_URL", None)
    monkeypatch.setattr(settings, "OSS_BUCKET", "b")
    monkeypatch.setattr(settings, "OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com")
    assert build_object_url(key="a/b.jpg").startswith("https://b.oss-cn-hangzhou.aliyuncs.com/")

    class FakeBucket:
        def __init__(self):  # type: ignore[no-untyped-def]
            self.calls = []

        def put_object_from_file(self, key, filename, headers=None):  # type: ignore[no-untyped-def]
            self.calls.append((key, filename, headers))

    fake_bucket = FakeBucket()
    monkeypatch.setattr(oss_mod, "_get_bucket", lambda: fake_bucket)

    class _StreamResp:
        def raise_for_status(self):  # type: ignore[no-untyped-def]
            return None

        def iter_bytes(self):  # type: ignore[no-untyped-def]
            yield b"abc"

    class _StreamCtx:
        def __enter__(self):  # type: ignore[no-untyped-def]
            return _StreamResp()

        def __exit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
            return False

    monkeypatch.setattr(httpx, "stream", lambda *a, **k: _StreamCtx())
    monkeypatch.setattr(settings, "OSS_OBJECT_ACL", "public-read")

    url = upload_from_url(url="https://example.com/v.mp4", key="results/x.mp4")
    assert url.endswith("/results/x.mp4")
    assert fake_bucket.calls


def test_crud_points_row_autocreate(db):
    user = crud.create_user(session=db, device_id="device_no_points")
    # Remove points row to hit create branch.
    db.exec(delete(UserPoints).where(UserPoints.user_id == user.id))
    db.commit()

    points = crud.get_user_points(session=db, user_id=user.id)
    assert points.balance == 0


def test_crud_update_user_vip(db):
    user = crud.create_user(session=db, device_id="device_vip")
    crud.update_user_vip(session=db, user_id=user.id, is_vip=True, vip_type=str(VipType.weekly), vip_expire_time=None)
    db.refresh(user)
    assert user.is_vip is True
