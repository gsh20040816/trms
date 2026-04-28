from __future__ import annotations

from datetime import datetime
from enum import StrEnum
import base64
import hashlib
import hmac
import secrets
from typing import Protocol

from pydantic import BaseModel, Field, model_validator


PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 260_000
PASSWORD_SALT_BYTES = 16
ACCESS_TOKEN_BYTES = 32


class UserRole(StrEnum):
    MEMBER = "member"
    ADMIN = "admin"
    SYSTEM_ADMIN = "system_admin"


class UserRegisterInput(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    role: UserRole
    display_name: str | None = Field(default=None, max_length=128)
    actor_id: str | None = Field(default=None, max_length=128)
    member_code: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def normalize_fields(self) -> "UserRegisterInput":
        self.username = _normalize_required(self.username)
        self.display_name = _normalize_optional(self.display_name)
        self.actor_id = _normalize_optional(self.actor_id)
        self.member_code = _normalize_optional(self.member_code)
        return self


class UserLoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def normalize_fields(self) -> "UserLoginInput":
        self.username = _normalize_required(self.username)
        return self


class UserCreate(BaseModel):
    username: str
    password_hash: str
    role: UserRole
    actor_id: str
    display_name: str
    member_code: str | None


class AuthenticatedUser(BaseModel):
    id: str
    username: str
    role: UserRole
    actor_id: str
    display_name: str
    member_code: str | None
    created_at: datetime
    updated_at: datetime


class StoredAuthUser(AuthenticatedUser):
    password_hash: str


class AuthSession(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser


class UsernameAlreadyExistsError(ValueError):
    def __init__(self, username: str) -> None:
        super().__init__(f"username already exists: {username}")


class InvalidCredentialsError(ValueError):
    def __init__(self) -> None:
        super().__init__("invalid username or password")


class AuthRepository(Protocol):
    def create_user(self, data: UserCreate) -> AuthenticatedUser:
        raise NotImplementedError

    def get_user_by_username(self, username: str) -> StoredAuthUser | None:
        raise NotImplementedError

    def get_user_by_token_hash(self, token_hash: str) -> AuthenticatedUser | None:
        raise NotImplementedError

    def create_session(self, *, user_id: str, token_hash: str) -> None:
        raise NotImplementedError

    def revoke_session(self, *, token_hash: str) -> bool:
        raise NotImplementedError


def register_user(repository: AuthRepository, payload: UserRegisterInput) -> AuthSession:
    username = payload.username.lower()
    display_name = payload.display_name or payload.username
    actor_id = payload.actor_id or payload.username
    member_code = payload.member_code if payload.role is UserRole.MEMBER else None
    user = repository.create_user(
        UserCreate(
            username=username,
            password_hash=hash_password(payload.password),
            role=payload.role,
            actor_id=actor_id,
            display_name=display_name,
            member_code=member_code,
        )
    )
    return _create_auth_session(repository, user)


def login_user(repository: AuthRepository, payload: UserLoginInput) -> AuthSession:
    user = repository.get_user_by_username(payload.username.lower())
    if user is None or not verify_password(payload.password, user.password_hash):
        raise InvalidCredentialsError()
    return _create_auth_session(repository, user)


def get_user_by_access_token(repository: AuthRepository, access_token: str) -> AuthenticatedUser | None:
    normalized_token = access_token.strip()
    if not normalized_token:
        return None
    return repository.get_user_by_token_hash(hash_token(normalized_token))


def revoke_access_token(repository: AuthRepository, access_token: str) -> bool:
    normalized_token = access_token.strip()
    if not normalized_token:
        return False
    return repository.revoke_session(token_hash=hash_token(normalized_token))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return "$".join(
        [
            PASSWORD_HASH_ALGORITHM,
            str(PASSWORD_HASH_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, raw_iterations, raw_salt, raw_digest = password_hash.split("$", maxsplit=3)
        iterations = int(raw_iterations)
        salt = base64.urlsafe_b64decode(raw_salt.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(raw_digest.encode("ascii"))
    except (ValueError, TypeError):
        return False

    if algorithm != PASSWORD_HASH_ALGORITHM:
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def hash_token(access_token: str) -> str:
    return hashlib.sha256(access_token.encode("utf-8")).hexdigest()


def _create_auth_session(repository: AuthRepository, user: AuthenticatedUser) -> AuthSession:
    access_token = secrets.token_urlsafe(ACCESS_TOKEN_BYTES)
    repository.create_session(user_id=user.id, token_hash=hash_token(access_token))
    return AuthSession(access_token=access_token, user=user)


def _normalize_required(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("must not be blank")
    return normalized


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized if normalized else None
