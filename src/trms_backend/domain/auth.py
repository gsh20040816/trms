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


class UserRegistrationSource(StrEnum):
    SELF_SERVICE = "self_service"
    BOOTSTRAP_TOKEN = "bootstrap_token"


class UserRegisterInput(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    role: UserRole
    roles: list[UserRole] | None = None
    display_name: str | None = Field(default=None, max_length=128)
    actor_id: str | None = Field(default=None, max_length=128)
    member_code: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def normalize_fields(self) -> "UserRegisterInput":
        self.username = _normalize_required(self.username)
        self.roles = _normalize_roles(self.roles, self.role)
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
    roles: list[UserRole]
    actor_id: str
    display_name: str
    member_code: str | None
    registration_source: UserRegistrationSource
    created_by_user_id: str | None = None


class AuthenticatedUser(BaseModel):
    id: str
    username: str
    role: UserRole
    roles: list[UserRole]
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


class RoleSwitchInput(BaseModel):
    role: UserRole


class UsernameAlreadyExistsError(ValueError):
    def __init__(self, username: str) -> None:
        super().__init__(f"username already exists: {username}")


class InvalidCredentialsError(ValueError):
    def __init__(self) -> None:
        super().__init__("invalid username or password")


class PrivilegedSelfRegistrationDisabledError(ValueError):
    def __init__(self, role: UserRole) -> None:
        super().__init__(f"self-service registration for role '{role.value}' is disabled")


class PrivilegedBootstrapDisabledError(ValueError):
    def __init__(self) -> None:
        super().__init__("privileged account bootstrap is not configured")


class InvalidBootstrapTokenError(ValueError):
    def __init__(self) -> None:
        super().__init__("invalid bootstrap token")


class InvalidBootstrapRoleError(ValueError):
    def __init__(self, role: UserRole) -> None:
        super().__init__(
            f"bootstrap endpoint only supports 'system_admin', got '{role.value}'"
        )


class PrivilegedBootstrapAlreadyCompletedError(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "privileged account bootstrap is already completed; use an audited invite or approval flow"
        )


class RoleNotAssignedError(ValueError):
    def __init__(self, role: UserRole) -> None:
        super().__init__(f"role '{role.value}' is not assigned to this account")


class AuthRepository(Protocol):
    def get_user_by_id(self, user_id: str) -> AuthenticatedUser | None:
        raise NotImplementedError

    def create_user(self, data: UserCreate) -> AuthenticatedUser:
        raise NotImplementedError

    def get_user_by_username(self, username: str) -> StoredAuthUser | None:
        raise NotImplementedError

    def get_user_by_token_hash(self, token_hash: str) -> AuthenticatedUser | None:
        raise NotImplementedError

    def list_users_by_member_identifiers(self, identifiers: list[str]) -> list[AuthenticatedUser]:
        raise NotImplementedError

    def search_users(
        self,
        *,
        keyword: str,
        roles: tuple[UserRole, ...],
        limit: int,
    ) -> list[AuthenticatedUser]:
        raise NotImplementedError

    def create_session(self, *, user_id: str, token_hash: str, active_role: UserRole) -> None:
        raise NotImplementedError

    def revoke_session(self, *, token_hash: str) -> bool:
        raise NotImplementedError

    def switch_session_active_role(
        self,
        *,
        token_hash: str,
        active_role: UserRole,
    ) -> AuthenticatedUser | None:
        raise NotImplementedError

    def grant_role_to_user(
        self,
        *,
        user_id: str,
        role: UserRole,
    ) -> tuple[AuthenticatedUser, bool] | None:
        raise NotImplementedError

    def count_users_with_roles(self, roles: tuple[UserRole, ...]) -> int:
        raise NotImplementedError


def register_user(
    repository: AuthRepository,
    payload: UserRegisterInput,
    *,
    allow_privileged_self_registration: bool = True,
) -> AuthSession:
    requested_roles = _normalize_roles(payload.roles, payload.role)
    if not allow_privileged_self_registration:
        privileged_role = next((role for role in requested_roles if _is_privileged_role(role)), None)
        if privileged_role is not None:
            raise PrivilegedSelfRegistrationDisabledError(privileged_role)
    user = repository.create_user(
        _build_user_create(
            payload,
            registration_source=UserRegistrationSource.SELF_SERVICE,
        )
    )
    return _create_auth_session(repository, user)


def bootstrap_privileged_user(
    repository: AuthRepository,
    payload: UserRegisterInput,
    *,
    bootstrap_token: str | None,
    configured_bootstrap_token: str | None,
) -> AuthSession:
    if payload.role is not UserRole.SYSTEM_ADMIN:
        raise InvalidBootstrapRoleError(payload.role)

    normalized_configured_token = (configured_bootstrap_token or "").strip()
    if not normalized_configured_token:
        raise PrivilegedBootstrapDisabledError()

    normalized_bootstrap_token = (bootstrap_token or "").strip()
    if not normalized_bootstrap_token or not hmac.compare_digest(
        normalized_bootstrap_token,
        normalized_configured_token,
    ):
        raise InvalidBootstrapTokenError()

    if repository.count_users_with_roles((UserRole.ADMIN, UserRole.SYSTEM_ADMIN)) > 0:
        raise PrivilegedBootstrapAlreadyCompletedError()

    user = repository.create_user(
        _build_user_create(
            payload,
            registration_source=UserRegistrationSource.BOOTSTRAP_TOKEN,
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


def switch_active_role(
    repository: AuthRepository,
    access_token: str,
    target_role: UserRole,
) -> AuthSession:
    normalized_token = access_token.strip()
    if not normalized_token:
        raise InvalidCredentialsError()

    user = repository.get_user_by_token_hash(hash_token(normalized_token))
    if user is None:
        raise InvalidCredentialsError()
    if target_role not in user.roles:
        raise RoleNotAssignedError(target_role)

    switched_user = repository.switch_session_active_role(
        token_hash=hash_token(normalized_token),
        active_role=target_role,
    )
    if switched_user is None:
        raise InvalidCredentialsError()
    return AuthSession(access_token=normalized_token, user=switched_user)


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
    repository.create_session(
        user_id=user.id,
        token_hash=hash_token(access_token),
        active_role=user.role,
    )
    return AuthSession(access_token=access_token, user=user)


def _build_user_create(
    payload: UserRegisterInput,
    *,
    registration_source: UserRegistrationSource,
) -> UserCreate:
    username = payload.username.lower()
    display_name = payload.display_name or payload.username
    actor_id = payload.actor_id or payload.username
    roles = _normalize_roles(payload.roles, payload.role)
    member_code = payload.member_code if UserRole.MEMBER in roles else None
    return UserCreate(
        username=username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        roles=roles,
        actor_id=actor_id,
        display_name=display_name,
        member_code=member_code,
        registration_source=registration_source,
    )


def _is_privileged_role(role: UserRole) -> bool:
    return role in {UserRole.ADMIN, UserRole.SYSTEM_ADMIN}


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


def _normalize_roles(
    roles: list[UserRole] | None,
    fallback_role: UserRole,
) -> list[UserRole]:
    normalized_roles: list[UserRole] = []
    for role in roles or []:
        if role not in normalized_roles:
            normalized_roles.append(role)
    if fallback_role not in normalized_roles:
        normalized_roles.insert(0, fallback_role)
    return normalized_roles
