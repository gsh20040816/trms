from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, field_validator, model_validator


class RecognitionTaskStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NEEDS_CONFIRMATION = "needs_confirmation"


class RecognitionTaskCreate(BaseModel):
    material_id: str
    is_final_fact: Literal[False] = False


class RecognitionFieldSource(StrEnum):
    OCR = "ocr"
    PDF_TEXT = "pdf_text"
    AI = "ai"
    MANUAL = "manual"


class RecognitionFieldStatus(StrEnum):
    RECOGNIZED = "recognized"
    NEEDS_CONFIRMATION = "needs_confirmation"


class RecognitionFailureStage(StrEnum):
    OCR = "ocr"
    PDF = "pdf"
    AI = "ai"


class RecognitionFieldResult(BaseModel):
    value: Any
    source: RecognitionFieldSource
    confidence: float = Field(ge=0, le=1)
    status: RecognitionFieldStatus = RecognitionFieldStatus.RECOGNIZED
    updated_at: datetime | None = None


class RecognitionFailureDetail(BaseModel):
    stage: RecognitionFailureStage
    reason: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("failure reason must not be empty")
        return normalized


class RecognitionResultPayload(BaseModel):
    raw_response: Any = None
    recognized_fields: dict[str, RecognitionFieldResult] = Field(default_factory=dict)

    @field_validator("recognized_fields")
    @classmethod
    def validate_field_names(
        cls,
        value: dict[str, RecognitionFieldResult],
    ) -> dict[str, RecognitionFieldResult]:
        normalized: dict[str, RecognitionFieldResult] = {}
        for field_name, field_result in value.items():
            normalized_name = field_name.strip()
            if not normalized_name:
                raise ValueError("recognition field names must not be empty")
            normalized[normalized_name] = field_result
        return normalized

    def pending_confirmation_field_names(self) -> list[str]:
        return [
            field_name
            for field_name, field_result in self.recognized_fields.items()
            if field_result.status is RecognitionFieldStatus.NEEDS_CONFIRMATION
        ]


class RecognitionTaskRecord(BaseModel):
    id: str
    material_id: str
    status: RecognitionTaskStatus
    is_final_fact: Literal[False] = False
    failure: RecognitionFailureDetail | None = None
    raw_response: Any = None
    recognized_fields: dict[str, RecognitionFieldResult] = Field(default_factory=dict)
    manual_corrections: list["RecognitionFieldCorrectionRecord"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class RecognitionRevalidationStatus(StrEnum):
    TRIGGERED = "triggered"
    NOT_REQUIRED = "not_required"


class RecognitionFieldCorrectionRecord(BaseModel):
    id: str
    field_name: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    before: RecognitionFieldResult | None = None
    after: RecognitionFieldResult
    revalidation_status: RecognitionRevalidationStatus = RecognitionRevalidationStatus.NOT_REQUIRED
    corrected_at: datetime


class RecognitionTaskStatusUpdate(BaseModel):
    target_status: RecognitionTaskStatus
    result: RecognitionResultPayload | None = None
    failure: RecognitionFailureDetail | None = None

    @model_validator(mode="after")
    def validate_payload_for_target_status(self) -> RecognitionTaskStatusUpdate:
        if self.target_status is RecognitionTaskStatus.FAILED:
            if self.failure is None:
                raise ValueError("failed recognition task requires failure detail")
        elif self.failure is not None:
            raise ValueError("only failed recognition task can persist failure detail")

        if self.result is None:
            return self
        if self.target_status is RecognitionTaskStatus.PENDING:
            raise ValueError("pending recognition task cannot persist recognition result")
        pending_fields = self.result.pending_confirmation_field_names()
        if pending_fields and self.target_status is not RecognitionTaskStatus.NEEDS_CONFIRMATION:
            joined_field_names = ", ".join(pending_fields)
            raise ValueError(
                "low-confidence recognition fields require needs_confirmation status: "
                f"{joined_field_names}"
            )
        return self


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

    def list_pending(self, *, limit: int) -> list[RecognitionTaskRecord]:
        raise NotImplementedError

    def get_latest_effective_by_material(self, material_id: str) -> RecognitionTaskRecord | None:
        raise NotImplementedError

    def list_by_material(self, material_id: str) -> list[RecognitionTaskRecord]:
        raise NotImplementedError

    def update_status(
        self,
        recognition_task_id: str,
        target_status: RecognitionTaskStatus,
        result: RecognitionResultPayload | None = None,
        failure: RecognitionFailureDetail | None = None,
        expected_current_status: RecognitionTaskStatus | None = None,
    ) -> RecognitionTaskRecord | None:
        raise NotImplementedError

    def apply_manual_corrections(
        self,
        *,
        material_id: str,
        actor_id: str,
        corrected_fields: dict[str, Any],
        revalidation_field_names: set[str] | None = None,
    ) -> RecognitionTaskRecord:
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
