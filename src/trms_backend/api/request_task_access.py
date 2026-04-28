from __future__ import annotations

from enum import StrEnum

from fastapi import HTTPException, status

from trms_backend.api.request_identity import RequestIdentity
from trms_backend.domain.auth import UserRole
from trms_backend.domain.tasks import ReimbursementTask


class TaskAccessScope(StrEnum):
    ANONYMOUS = "anonymous"
    ADMINISTRATOR = "administrator"
    MEMBER = "member"


def resolve_task_access_scope(
    identity: RequestIdentity,
    task: ReimbursementTask,
    *,
    forbidden_detail: str,
) -> TaskAccessScope:
    if not identity.is_authenticated or identity.actor_id is None:
        return TaskAccessScope.ANONYMOUS

    actor_id = identity.actor_id
    if (
        actor_id == task.administrator_id
        and identity.role in {UserRole.ADMIN, UserRole.SYSTEM_ADMIN}
    ):
        return TaskAccessScope.ADMINISTRATOR
    if identity.role is UserRole.MEMBER and actor_id in task.member_ids:
        return TaskAccessScope.MEMBER

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=forbidden_detail,
    )
