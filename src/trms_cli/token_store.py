from __future__ import annotations

import json
import os
import stat
from pathlib import Path


TOKEN_STORE_SCHEMA_VERSION = "trms-cli.session.v1"
TOKEN_STORE_DIR_ENV = "TRMS_CLI_CONFIG_DIR"
TOKEN_STORE_DIR_MODE = 0o700
TOKEN_STORE_FILE_MODE = 0o600
TOKEN_STORE_FILENAME = "session.json"


class TokenStoreError(Exception):
    """Raised when the CLI token store cannot be safely updated."""


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
