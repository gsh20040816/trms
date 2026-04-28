from datetime import datetime, timezone

import pytest

from trms_backend.api.request_identity import (
    RequestIdentity,
    RequestIdentityActorMismatchError,
    RequestIdentityMemberMismatchError,
    RequestIdentitySource,
    resolve_actor_id_for_request,
    resolve_member_id_for_request,
    resolve_submitter_id_for_request,
)
from trms_backend.domain.auth import AuthenticatedUser, UserRole


def build_authenticated_identity(
    *,
    actor_id: str = "2250001",
    member_id: str | None = "2250001",
) -> RequestIdentity:
    now = datetime.now(timezone.utc)
    user = AuthenticatedUser(
        id="user-1",
        username="member1",
        role=UserRole.MEMBER,
        actor_id=actor_id,
        display_name="王队员",
        member_code=member_id,
        created_at=now,
        updated_at=now,
    )
    return RequestIdentity(
        is_authenticated=True,
        source=RequestIdentitySource.BEARER,
        role=user.role,
        actor_id=user.actor_id,
        member_id=user.member_code,
        user=user,
    )


def test_resolve_actor_id_defaults_to_authenticated_identity():
    identity = build_authenticated_identity(actor_id="member-1")

    assert resolve_actor_id_for_request(identity, None) == "member-1"
    assert resolve_actor_id_for_request(identity, " member-1 ") == "member-1"


def test_resolve_actor_id_rejects_mismatched_authenticated_identity():
    identity = build_authenticated_identity(actor_id="member-1")

    with pytest.raises(RequestIdentityActorMismatchError):
        resolve_actor_id_for_request(identity, "member-2")


def test_resolve_member_id_defaults_to_authenticated_member_identity():
    identity = build_authenticated_identity(member_id="2250001")

    assert resolve_member_id_for_request(identity, None) == "2250001"
    assert resolve_submitter_id_for_request(identity, " 2250001 ") == "2250001"


def test_resolve_member_id_rejects_mismatched_authenticated_member_identity():
    identity = build_authenticated_identity(member_id="2250001")

    with pytest.raises(RequestIdentityMemberMismatchError):
        resolve_member_id_for_request(identity, "2250999")

    with pytest.raises(RequestIdentityMemberMismatchError):
        resolve_submitter_id_for_request(identity, "2250999")


def test_anonymous_request_identity_keeps_explicit_legacy_ids():
    identity = RequestIdentity(
        is_authenticated=False,
        source=RequestIdentitySource.ANONYMOUS,
    )

    assert resolve_actor_id_for_request(identity, "admin-1") == "admin-1"
    assert resolve_member_id_for_request(identity, "2250002") == "2250002"
    assert resolve_submitter_id_for_request(identity, "2250003") == "2250003"
