import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402

DEVICE_HEADERS = {"X-API-Key": TestConfig.DEVICE_API_KEY}


@pytest.fixture
def app():
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    client.post("/api/register", json={
        "fullname": "Test User", "email": "test@example.com", "password": "secret123", "phone": "9999999999",
    })
    token = client.post("/api/login", json={"email": "test@example.com", "password": "secret123"}).json["token"]
    return {"Authorization": f"Bearer {token}"}


def send_reading(client, **overrides):
    payload = {
        "shipment_id": "SHP1", "product_type": "pharma", "location": "Hyderabad",
        "temperature": 5, "humidity": 50, "delay_hours": 0.5,
    }
    payload.update(overrides)
    return client.post("/api/sensor", json=payload, headers=DEVICE_HEADERS)
