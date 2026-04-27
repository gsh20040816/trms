from fastapi.testclient import TestClient

from trms_backend.main import create_app


def test_health_check_returns_ok(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/test.db"))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
