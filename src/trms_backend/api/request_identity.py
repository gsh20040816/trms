from __future__ import annotations

from enum import StrEnum
from typing import Callable

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from trms_backend.domain.auth import (
    AuthRepository,
    AuthenticatedUser,
    UserRole,
    get_user_by_access_token,
)


class RequestIdentitySource(StrEnum):
    ANONYMOUS = "anonymous"
    BEARER = "bearer"


class RequestIdentity(BaseModel):
    is_authenticated: bool
    source: RequestIdentitySource
    role: UserRole | None = None
    available_roles: list[UserRole] = Field(default_factory=list)
    actor_id: str | None = None
    member_id: str | None = None
    user: AuthenticatedUser | None = None


class RequestIdentityActorMismatchError(ValueError):
    def __init__(self, expected_actor_id: str, received_actor_id: str) -> None:
        super().__init__(
            "actor_id does not match the authenticated request identity: "
            f"expected '{expected_actor_id}', got '{received_actor_id}'"
        )


class RequestIdentityMemberMismatchError(ValueError):
    def __init__(self, field_name: str, expected_member_id: str, received_member_id: str) -> None:
        super().__init__(
            f"{field_name} does not match the authenticated request identity: "
            f"expected '{expected_member_id}', got '{received_member_id}'"
        )


def build_optional_request_identity_dependency(
    repository: AuthRepository,
) -> Callable[..., RequestIdentity]:
    def resolve_request_identity(
        authorization: str | None = Header(default=None),
    ) -> RequestIdentity:
        return resolve_request_identity_from_authorization(repository, authorization)

    return resolve_request_identity


def build_authenticated_request_identity_dependency(
    repository: AuthRepository,
) -> Callable[..., RequestIdentity]:
    optional_request_identity = build_optional_request_identity_dependency(repository)

    def require_request_identity(
        identity: RequestIdentity = Depends(optional_request_identity),
    ) -> RequestIdentity:
        if not identity.is_authenticated:
            raise build_invalid_bearer_token_exception()
        return identity

    return require_request_identity


def resolve_request_identity_from_authorization(
    repository: AuthRepository,
    authorization: str | None,
) -> RequestIdentity:
    if authorization is None:
        return RequestIdentity(
            is_authenticated=False,
            source=RequestIdentitySource.ANONYMOUS,
        )

    access_token = extract_bearer_token(authorization)
    if access_token is None:
        raise build_invalid_bearer_token_exception()

    user = get_user_by_access_token(repository, access_token)
    if user is None:
        raise build_invalid_bearer_token_exception()

    return RequestIdentity(
        is_authenticated=True,
        source=RequestIdentitySource.BEARER,
        role=user.role,
        available_roles=user.roles,
        actor_id=user.actor_id,
        member_id=user.member_code,
        user=user,
    )


def resolve_actor_id_for_request(identity: RequestIdentity, actor_id: str | None) -> str | None:
    normalized_actor_id = _normalize_optional_id(actor_id)
    if identity.actor_id is None:
        return normalized_actor_id
    if normalized_actor_id is None:
        return identity.actor_id
    if normalized_actor_id != identity.actor_id:
        raise RequestIdentityActorMismatchError(identity.actor_id, normalized_actor_id)
    return normalized_actor_id


def resolve_member_id_for_request(identity: RequestIdentity, member_id: str | None) -> str | None:
    return _resolve_subject_member_id_for_request(
        identity,
        member_id,
        field_name="member_id",
    )


def resolve_submitter_id_for_request(
    identity: RequestIdentity,
    submitter_id: str | None,
) -> str | None:
    return _resolve_subject_member_id_for_request(
        identity,
        submitter_id,
        field_name="submitter_id",
    )


def extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer":
        return None
    normalized_token = token.strip()
    return normalized_token if normalized_token else None


def build_invalid_bearer_token_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid or missing bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _resolve_subject_member_id_for_request(
    identity: RequestIdentity,
    value: str | None,
    *,
    field_name: str,
) -> str | None:
    normalized_value = _normalize_optional_id(value)
    if identity.member_id is None:
        return normalized_value
    if normalized_value is None:
        return identity.member_id
    if normalized_value != identity.member_id:
        raise RequestIdentityMemberMismatchError(field_name, identity.member_id, normalized_value)
    return normalized_value


def _normalize_optional_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized_value = value.strip()
    return normalized_value or None
