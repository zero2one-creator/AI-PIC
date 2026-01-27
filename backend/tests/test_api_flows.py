from __future__ import annotations

from io import BytesIO
import time

from app import crud
from app.core.config import settings
from app.enums import PointTransactionType


class _FakeRedis:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, str]]] = []

    def xadd(self, name: str, fields: dict[str, str]) -> str:  # type: ignore[override]
        self.messages.append((name, fields))
        return "1-0"


def _login(client, device_id: str = "device_test_1") -> tuple[str, int]:
    r = client.post("/api/v1/auth/login", json={"device_id": device_id})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    token = body["data"]["access_token"]
    user_id = body["data"]["user"]["id"]
    return token, user_id


def test_auth_login_and_profile(client):
    token, user_id = _login(client)

    r = client.get("/api/v1/user/profile", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["id"] == user_id
    assert body["data"]["device_id"] == "device_test_1"
    assert body["data"]["points_balance"] == 0


def test_points_balance_and_transactions(client, db, monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr("app.api.routes.emoji.get_redis", lambda: fake)

    token, user_id = _login(client, device_id="device_points_1")
    headers = {"Authorization": f"Bearer {token}"}

    # Seed balance with a purchase (simulates points pack / reward).
    crud.change_points(
        session=db,
        user_id=user_id,
        delta=500,
        tx_type=PointTransactionType.purchase,
        task_type=None,
    )

    r = client.get("/api/v1/points/balance", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["balance"] == 500

    r = client.post(
        "/api/v1/emoji/create",
        headers=headers,
        json={
            "image_url": "https://example.com/a.jpg",
            "driven_id": "emoji_001",
            "face_bbox": [0, 0, 100, 100],
            "ext_bbox": [0, 0, 120, 120],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["points_cost"] == 200
    assert fake.messages and fake.messages[0][0] == "emoji_tasks"

    r = client.get("/api/v1/points/balance", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["balance"] == 300

    r = client.get("/api/v1/points/transactions?page=1&page_size=20", headers=headers)
    assert r.status_code == 200
    tx = r.json()["data"]
    assert tx["count"] >= 2
    # Latest tx should be the consume for the emoji create.
    assert tx["data"][0]["type"] == "consume"


def test_emoji_task_status_and_history(client, db, monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr("app.api.routes.emoji.get_redis", lambda: fake)

    token, user_id = _login(client, device_id="device_history_1")
    headers = {"Authorization": f"Bearer {token}"}

    crud.change_points(
        session=db,
        user_id=user_id,
        delta=500,
        tx_type=PointTransactionType.purchase,
    )

    r = client.post(
        "/api/v1/emoji/create",
        headers=headers,
        json={
            "image_url": "https://example.com/a.jpg",
            "driven_id": "emoji_001",
            "face_bbox": [0, 0, 100, 100],
            "ext_bbox": [0, 0, 120, 120],
        },
    )
    task_id = r.json()["data"]["id"]

    r = client.get(f"/api/v1/emoji/task/{task_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["id"] == task_id

    r = client.get("/api/v1/emoji/history?page=1&page_size=20", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["count"] >= 1

    r = client.get("/api/v1/emoji/task/999999999", headers=headers)
    assert r.status_code == 404


def test_emoji_create_insufficient_points(client, monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr("app.api.routes.emoji.get_redis", lambda: fake)

    token, _ = _login(client, device_id="device_low_points")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/api/v1/emoji/create",
        headers=headers,
        json={"image_url": "https://example.com/a.jpg", "driven_id": "emoji_001"},
    )
    assert r.status_code == 400
    body = r.json()
    assert body["code"] == 402001


def test_config_endpoint(client):
    r = client.get("/api/v1/config")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["points_rules"]["emoji"] == 200


def test_emoji_upload_and_detect(client, monkeypatch):
    token, _ = _login(client, device_id="device_upload_1")
    headers = {"Authorization": f"Bearer {token}"}

    monkeypatch.setattr(
        "app.api.routes.emoji.upload_file", lambda **_: "https://cdn.example.com/uploads/mock.jpg"
    )
    files = {"file": ("test.jpg", BytesIO(b"fake image bytes"), "image/jpeg")}
    r = client.post("/api/v1/emoji/detect", headers=headers, files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    detect = body["data"]
    assert detect["image_url"].startswith("https://")
    assert detect["passed"] is True
    assert detect["face_bbox"] is not None


def test_subscription_webhook_updates_vip(client):
    token, user_id = _login(client, device_id="device_sub_1")
    headers = {"Authorization": f"Bearer {token}"}

    now_ms = int(time.time() * 1000)
    payload = {
        "event": {
            "id": "evt_sub_1",
            "type": "INITIAL_PURCHASE",
            "app_user_id": str(user_id),
            "product_id": "weekly_001",
            "purchased_at_ms": now_ms,
            "expiration_at_ms": now_ms + 7 * 24 * 3600 * 1000,
        }
    }
    r = client.post(
        "/api/v1/subscription/webhook",
        json=payload,
        headers={"Authorization": f"Bearer {settings.REVENUECAT_WEBHOOK_SECRET}"},
    )
    assert r.status_code == 200
    assert r.json()["code"] == 0

    r = client.get("/api/v1/subscription/status", headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["is_vip"] is True
    assert data["vip_type"] == "weekly"


def test_subscription_webhook_auth_and_invalid_payload(client):
    token, user_id = _login(client, device_id="device_sub_err")
    _ = token

    now_ms = int(time.time() * 1000)
    payload = {
        "event": {
            "id": "evt_sub_err_1",
            "type": "INITIAL_PURCHASE",
            "app_user_id": str(user_id),
            "product_id": "weekly_001",
            "purchased_at_ms": now_ms,
            "expiration_at_ms": now_ms + 7 * 24 * 3600 * 1000,
        }
    }

    r = client.post("/api/v1/subscription/webhook", json=payload)
    assert r.status_code == 401

    r = client.post(
        "/api/v1/subscription/webhook",
        json={"nope": 1},
        headers={"Authorization": f"Bearer {settings.REVENUECAT_WEBHOOK_SECRET}"},
    )
    assert r.status_code == 400


def test_subscription_webhook_expiration_clears_vip(client):
    token, user_id = _login(client, device_id="device_sub_expire")
    headers = {"Authorization": f"Bearer {token}"}

    now_ms = int(time.time() * 1000)
    auth = {"Authorization": f"Bearer {settings.REVENUECAT_WEBHOOK_SECRET}"}

    r = client.post(
        "/api/v1/subscription/webhook",
        json={
            "event": {
                "id": "evt_sub_expire_1",
                "type": "INITIAL_PURCHASE",
                "app_user_id": str(user_id),
                "product_id": "weekly_001",
                "purchased_at_ms": now_ms,
                "expiration_at_ms": now_ms + 7 * 24 * 3600 * 1000,
            }
        },
        headers=auth,
    )
    assert r.status_code == 200

    r = client.post(
        "/api/v1/subscription/webhook",
        json={
            "event": {
                "id": "evt_sub_expire_2",
                "type": "EXPIRATION",
                "app_user_id": str(user_id),
                "product_id": "weekly_001",
                "expiration_at_ms": now_ms,
            }
        },
        headers=auth,
    )
    assert r.status_code == 200

    r = client.get("/api/v1/subscription/status", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["is_vip"] is False


def test_revenuecat_points_pack_grants_points_and_idempotent(client):
    token, user_id = _login(client, device_id="device_pack_1")
    headers = {"Authorization": f"Bearer {token}"}

    auth = {"Authorization": f"Bearer {settings.REVENUECAT_WEBHOOK_SECRET}"}
    now_ms = int(time.time() * 1000)
    payload = {
        "event": {
            "id": "evt_pack_1",
            "type": "NON_RENEWING_PURCHASE",
            "app_user_id": str(user_id),
            "product_id": "points_1000",
            "transaction_id": "tx_pack_1",
            "purchased_at_ms": now_ms,
            "price": 2.99,
            "currency": "USD",
        }
    }
    r = client.post("/api/v1/subscription/webhook", json=payload, headers=auth)
    assert r.status_code == 200
    assert r.json()["code"] == 0

    r = client.get("/api/v1/points/balance", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["balance"] == 1000

    # Duplicate event id should be ignored.
    r = client.post("/api/v1/subscription/webhook", json=payload, headers=auth)
    assert r.status_code == 200
    assert r.json()["data"]["duplicate"] is True

    r = client.get("/api/v1/points/balance", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["balance"] == 1000

    # New event id but same transaction id should also not double-grant.
    payload2 = {
        "event": {**payload["event"], "id": "evt_pack_2"}
    }
    r = client.post("/api/v1/subscription/webhook", json=payload2, headers=auth)
    assert r.status_code == 200

    r = client.get("/api/v1/points/balance", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["balance"] == 1000


def test_order_create_get_list(client):
    token, _ = _login(client, device_id="device_order_1")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/api/v1/order/create",
        headers=headers,
        json={"product_type": "points_pack", "product_id": "points_1000", "quantity": 1, "amount": "2.99", "currency": "USD"},
    )
    assert r.status_code == 200
    order_no = r.json()["data"]["order_no"]

    r = client.get(f"/api/v1/order/{order_no}", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["order_no"] == order_no

    r = client.get("/api/v1/order/list?page=1&page_size=20", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["count"] >= 1


def test_auth_required(client):
    r = client.get("/api/v1/user/profile")
    assert r.status_code in (401, 403)
