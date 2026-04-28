from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path


TOKEN_STORE_SCHEMA_VERSION = "trms-cli.session.v1"
TOKEN_STORE_DIR_ENV = "TRMS_CLI_CONFIG_DIR"
TOKEN_STORE_DIR_MODE = 0o700
TOKEN_STORE_FILE_MODE = 0o600
TOKEN_STORE_FILENAME = "session.json"


class TokenStoreError(Exception):
    """Raised when the CLI token store cannot be safely updated."""


@dataclass(frozen=True)
class TokenSession:
    base_url: str
    member_id: str
    access_token: str
    refresh_token: str


def resolve_token_store_path() -> Path:
    configured_dir = os.getenv(TOKEN_STORE_DIR_ENV)
    if configured_dir:
        return Path(configured_dir).expanduser() / TOKEN_STORE_FILENAME

    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home).expanduser() / "trms" / TOKEN_STORE_FILENAME

    return Path.home() / ".config" / "trms" / TOKEN_STORE_FILENAME


def save_token_session(
    *,
    base_url: str,
    member_id: str,
    access_token: str,
    refresh_token: str,
) -> Path:
    token_store_path = resolve_token_store_path()
    token_store_path.parent.mkdir(parents=True, exist_ok=True)

    if os.name != "nt":
        os.chmod(token_store_path.parent, TOKEN_STORE_DIR_MODE)

    payload = {
        "schema_version": TOKEN_STORE_SCHEMA_VERSION,
        "base_url": base_url,
        "member_id": member_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }

    fd = os.open(
        token_store_path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        TOKEN_STORE_FILE_MODE,
    )
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False)
        stream.write("\n")

    if os.name != "nt":
        os.chmod(token_store_path, TOKEN_STORE_FILE_MODE)
        _assert_private_permissions(token_store_path)

    return token_store_path


def load_token_session() -> TokenSession:
    token_store_path = resolve_token_store_path()
    if not token_store_path.exists():
        raise TokenStoreError("CLI token session not found; run `trms-cli login` first")

    try:
        with token_store_path.open(encoding="utf-8") as stream:
            payload = json.load(stream)
    except json.JSONDecodeError as error:
        raise TokenStoreError(f"token store file contains invalid JSON: {token_store_path}") from error

    if not isinstance(payload, dict):
        raise TokenStoreError(f"token store payload must be an object: {token_store_path}")

    schema_version = payload.get("schema_version")
    if schema_version != TOKEN_STORE_SCHEMA_VERSION:
        raise TokenStoreError(
            "token store schema version is not supported: "
            f"{schema_version!r}; expected {TOKEN_STORE_SCHEMA_VERSION!r}"
        )

    return TokenSession(
        base_url=_require_non_empty_string(payload, "base_url", token_store_path),
        member_id=_require_member_id(payload, token_store_path),
        access_token=_require_non_empty_string(payload, "access_token", token_store_path),
        refresh_token=_require_non_empty_string(payload, "refresh_token", token_store_path),
    )


def _require_non_empty_string(payload: dict[str, object], field_name: str, token_store_path: Path) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise TokenStoreError(
            f"token store field {field_name!r} must be a non-empty string: {token_store_path}"
        )
    return value.strip()


def _require_member_id(payload: dict[str, object], token_store_path: Path) -> str:
    try:
        return _require_non_empty_string(payload, "member_id", token_store_path)
    except TokenStoreError as error:
        raise TokenStoreError(
            "CLI token session is missing bound member id; run `trms-cli login --member-id ...` again"
        ) from error


def _assert_private_permissions(token_store_path: Path) -> None:
    directory_mode = stat.S_IMODE(token_store_path.parent.stat().st_mode)
    if directory_mode & 0o077:
        raise TokenStoreError(
            f"token store directory permissions must be 0700 or stricter: {token_store_path.parent}"
        )

    file_mode = stat.S_IMODE(token_store_path.stat().st_mode)
    if file_mode & 0o077:
        raise TokenStoreError(
            f"token store file permissions must be 0600 or stricter: {token_store_path}"
        )
