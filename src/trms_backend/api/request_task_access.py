from __future__ import annotations

from enum import StrEnum

from fastapi import HTTPException, status

from trms_backend.api.request_identity import RequestIdentity
from trms_backend.domain.auth import UserRole
from trms_backend.domain.tasks import ReimbursementTask, is_task_administrator


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
    if identity.role in {UserRole.ADMIN, UserRole.SYSTEM_ADMIN} and is_task_administrator(
        task,
        actor_id=actor_id,
    ):
        return TaskAccessScope.ADMINISTRATOR
    if identity.role is UserRole.MEMBER and actor_id in task.member_ids:
        return TaskAccessScope.MEMBER

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=forbidden_detail,
    )
