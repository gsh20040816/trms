from fastapi.testclient import TestClient

from trms_backend.api.cli_compatibility import CLI_CLIENT_HEADER, CLI_VERSION_HEADER
from trms_backend.main import create_app


def test_cli_request_with_supported_version_can_access_health(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/test.db"))

    response = client.get(
        "/health",
        headers={
            CLI_CLIENT_HEADER: "cli",
            CLI_VERSION_HEADER: "1",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cli_request_with_stale_version_gets_upgrade_required(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/test.db"))

    response = client.get(
        "/health",
        headers={
            CLI_CLIENT_HEADER: "cli",
            CLI_VERSION_HEADER: "0",
        },
    )

    assert response.status_code == 426
    assert response.headers["X-TRMS-Minimum-CLI-Version"] == "1"
    assert response.json() == {
        "code": "cli_version_too_old",
        "detail": "CLI version is too old; upgrade trms-cli to protocol version 1 or newer",
        "minimum_supported_cli_version": "1",
        "received_cli_version": "0",
        "client_capabilities": "",
    }
