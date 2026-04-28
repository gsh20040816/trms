from __future__ import annotations

from httpx import Response


def assert_api_error(
    response: Response,
    *,
    status_code: int,
    code: str,
    detail=None,
):
    assert response.status_code == status_code
    payload = response.json()
    assert payload["code"] == code
    assert isinstance(payload["message"], str)
    assert payload["message"]
    assert payload["request_id"].startswith("req_")
    assert response.headers["X-Request-ID"] == payload["request_id"]
    if detail is not None:
        assert payload["detail"] == detail
    return payload
