from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel


class RecognitionTaskStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NEEDS_CONFIRMATION = "needs_confirmation"


class RecognitionTaskCreate(BaseModel):
    material_id: str
    is_final_fact: Literal[False] = False


class RecognitionTaskRecord(BaseModel):
    id: str
    material_id: str
    status: RecognitionTaskStatus
    is_final_fact: Literal[False] = False
    created_at: datetime
    updated_at: datetime


class RecognitionTaskStatusUpdate(BaseModel):
    target_status: RecognitionTaskStatus


class RecognitionTaskStatusTransitionError(ValueError):
    def __init__(
        self,
        current_status: RecognitionTaskStatus,
        target_status: RecognitionTaskStatus,
    ) -> None:
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            "recognition task cannot transition from "
            f"{current_status.value} to {target_status.value}"
        )


class RecognitionTaskRepository(Protocol):
    def create(self, data: RecognitionTaskCreate) -> RecognitionTaskRecord:
        raise NotImplementedError

    def get(self, recognition_task_id: str) -> RecognitionTaskRecord | None:
        raise NotImplementedError

    def list_by_material(self, material_id: str) -> list[RecognitionTaskRecord]:
        raise NotImplementedError

    def update_status(
        self,
        recognition_task_id: str,
        target_status: RecognitionTaskStatus,
    ) -> RecognitionTaskRecord | None:
        raise NotImplementedError


_ALLOWED_RECOGNITION_TASK_TRANSITIONS: dict[
    RecognitionTaskStatus,
    set[RecognitionTaskStatus],
] = {
    RecognitionTaskStatus.PENDING: {
        RecognitionTaskStatus.SUCCEEDED,
        RecognitionTaskStatus.FAILED,
        RecognitionTaskStatus.NEEDS_CONFIRMATION,
    },
    RecognitionTaskStatus.NEEDS_CONFIRMATION: {
        RecognitionTaskStatus.SUCCEEDED,
        RecognitionTaskStatus.FAILED,
    },
    RecognitionTaskStatus.SUCCEEDED: set(),
    RecognitionTaskStatus.FAILED: set(),
}


def ensure_recognition_task_can_transition(
    current_status: RecognitionTaskStatus,
    target_status: RecognitionTaskStatus,
) -> None:
    if target_status not in _ALLOWED_RECOGNITION_TASK_TRANSITIONS[current_status]:
        raise RecognitionTaskStatusTransitionError(current_status, target_status)
