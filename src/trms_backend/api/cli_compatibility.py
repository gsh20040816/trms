from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

from trms_backend.api.error_responses import build_error_payload


CLI_CLIENT_HEADER = "X-TRMS-Client"
CLI_CLIENT_KIND = "cli"
CLI_VERSION_HEADER = "X-TRMS-CLI-Version"
CLI_CAPABILITIES_HEADER = "X-TRMS-CLI-Capabilities"
MINIMUM_SUPPORTED_CLI_VERSION = 1


def reject_incompatible_cli_request(
    request: Request,
    *,
    request_id: str,
) -> JSONResponse | None:
    if request.headers.get(CLI_CLIENT_HEADER) != CLI_CLIENT_KIND:
        return None

    raw_version = request.headers.get(CLI_VERSION_HEADER)
    try:
        client_version = int(raw_version) if raw_version is not None else None
    except ValueError:
        client_version = None

    if client_version is not None and client_version >= MINIMUM_SUPPORTED_CLI_VERSION:
        return None

    return JSONResponse(
        status_code=status.HTTP_426_UPGRADE_REQUIRED,
        headers={
            "X-TRMS-Minimum-CLI-Version": str(MINIMUM_SUPPORTED_CLI_VERSION),
            "X-Request-ID": request_id,
        },
        content=build_error_payload(
            status_code=status.HTTP_426_UPGRADE_REQUIRED,
            code="cli_version_too_old",
            message="cli protocol version is no longer supported",
            request_id=request_id,
            detail=(
                "CLI version is too old; "
                f"upgrade trms-cli to protocol version {MINIMUM_SUPPORTED_CLI_VERSION} or newer"
            ),
            extra={
                "minimum_supported_cli_version": str(MINIMUM_SUPPORTED_CLI_VERSION),
                "received_cli_version": raw_version,
                "client_capabilities": request.headers.get(CLI_CAPABILITIES_HEADER, ""),
            },
        ),
    )
