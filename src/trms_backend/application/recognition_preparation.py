from __future__ import annotations

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError, PdfStreamError

from trms_backend.application.recognition_llm import (
    RecognitionDocumentInput,
    RecognitionLlmClient,
    RecognitionLlmExecutionError,
)
from trms_backend.application.recognition_runtime import (
    RecognitionLlmCapability,
    RecognitionLlmCapabilityStatus,
)
from trms_backend.domain.materials import MaterialFileStorage, MaterialRecord, MaterialRepository
from trms_backend.domain.recognitions import (
    RecognitionFailureDetail,
    RecognitionFailureStage,
    RecognitionFieldResult,
    RecognitionFieldSource,
    RecognitionResultPayload,
    RecognitionTaskRecord,
    RecognitionTaskRepository,
    RecognitionTaskStatus,
)

_IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})


class RecognitionTaskExecutionNotFoundError(LookupError):
    def __init__(self, recognition_task_id: str) -> None:
        self.recognition_task_id = recognition_task_id
        super().__init__(f"recognition task not found: {recognition_task_id}")


class RecognitionTaskExecutionConflictError(ValueError):
    def __init__(self, recognition_task_id: str, status: RecognitionTaskStatus) -> None:
        self.recognition_task_id = recognition_task_id
        self.status = status
        super().__init__(
            "recognition task can only execute from pending status: "
            f"{recognition_task_id} is {status.value}"
        )


class RecognitionMaterialNotFoundError(LookupError):
    def __init__(self, material_id: str) -> None:
        self.material_id = material_id
        super().__init__(f"material not found for recognition task: {material_id}")


class RecognitionPreparationError(ValueError):
    def __init__(self, failure: RecognitionFailureDetail) -> None:
        self.failure = failure
        super().__init__(failure.reason)


class RecognitionPreparationService:
    def __init__(
        self,
        material_repository: MaterialRepository,
        material_file_storage: MaterialFileStorage,
        recognition_task_repository: RecognitionTaskRepository,
        llm_capability: RecognitionLlmCapability,
        recognition_llm_client: RecognitionLlmClient | None = None,
    ) -> None:
        self._material_repository = material_repository
        self._material_file_storage = material_file_storage
        self._recognition_task_repository = recognition_task_repository
        self._llm_capability = llm_capability
        self._recognition_llm_client = recognition_llm_client

    def execute(self, recognition_task_id: str) -> RecognitionTaskRecord:
        task = self._recognition_task_repository.get(recognition_task_id)
        if task is None:
            raise RecognitionTaskExecutionNotFoundError(recognition_task_id)
        if task.status is not RecognitionTaskStatus.PENDING:
            raise RecognitionTaskExecutionConflictError(recognition_task_id, task.status)

        material = self._material_repository.get(task.material_id)
        if material is None:
            raise RecognitionMaterialNotFoundError(task.material_id)

        base_payload = {
            "preparation": {
                "material_id": material.id,
                "original_filename": material.original_filename,
                "content_type": material.content_type,
            }
        }

        try:
            content = self._material_file_storage.read(storage_key=material.storage_key)
        except FileNotFoundError:
            return self._fail_task(
                recognition_task_id=recognition_task_id,
                raw_response=base_payload,
                failure=RecognitionFailureDetail(
                    stage=RecognitionFailureStage.PDF,
                    reason="stored_file_missing",
                ),
            )

        try:
            document_input = build_recognition_document_input(material=material, content=content)
        except RecognitionPreparationError as error:
            return self._fail_task(
                recognition_task_id=recognition_task_id,
                raw_response=base_payload,
                failure=error.failure,
            )

        base_payload["preparation"]["recognition_input"] = document_input.model_dump(mode="json")
        if self._llm_capability.status is RecognitionLlmCapabilityStatus.DISABLED:
            return self._fail_task(
                recognition_task_id=recognition_task_id,
                raw_response=base_payload,
                failure=self._llm_capability.failure,
            )
        if self._recognition_llm_client is None:
            return self._fail_task(
                recognition_task_id=recognition_task_id,
                raw_response=base_payload,
                failure=RecognitionFailureDetail(
                    stage=RecognitionFailureStage.AI,
                    reason="structured_recognition_not_configured",
                ),
            )

        try:
            extraction = self._recognition_llm_client.recognize(
                material=material,
                document_input=document_input,
            )
        except RecognitionLlmExecutionError as error:
            raw_response = dict(base_payload)
            raw_response["llm"] = error.raw_response
            return self._fail_task(
                recognition_task_id=recognition_task_id,
                raw_response=raw_response,
                failure=error.failure,
            )

        raw_response = dict(base_payload)
        raw_response["llm"] = extraction.raw_response
        return self._complete_task(
            recognition_task_id=recognition_task_id,
            raw_response=raw_response,
            recognized_fields=extraction.recognized_fields,
            target_status=(
                RecognitionTaskStatus.NEEDS_CONFIRMATION
                if extraction.has_pending_confirmation()
                else RecognitionTaskStatus.SUCCEEDED
            ),
        )

    def _fail_task(
        self,
        *,
        recognition_task_id: str,
        raw_response: dict[str, object],
        failure: RecognitionFailureDetail,
    ) -> RecognitionTaskRecord:
        updated = self._recognition_task_repository.update_status(
            recognition_task_id,
            RecognitionTaskStatus.FAILED,
            result=RecognitionResultPayload(raw_response=raw_response),
            failure=failure,
            expected_current_status=RecognitionTaskStatus.PENDING,
        )
        if updated is None:
            self._raise_missing_or_conflict(recognition_task_id)
        return updated

    def _complete_task(
        self,
        *,
        recognition_task_id: str,
        raw_response: dict[str, object],
        recognized_fields: dict[str, RecognitionFieldResult],
        target_status: RecognitionTaskStatus,
    ) -> RecognitionTaskRecord:
        updated = self._recognition_task_repository.update_status(
            recognition_task_id,
            target_status,
            result=RecognitionResultPayload(
                raw_response=raw_response,
                recognized_fields=recognized_fields,
            ),
            expected_current_status=RecognitionTaskStatus.PENDING,
        )
        if updated is None:
            self._raise_missing_or_conflict(recognition_task_id)
        return updated

    def _raise_missing_or_conflict(self, recognition_task_id: str) -> None:
        current = self._recognition_task_repository.get(recognition_task_id)
        if current is None:
            raise RecognitionTaskExecutionNotFoundError(recognition_task_id)
        raise RecognitionTaskExecutionConflictError(recognition_task_id, current.status)


def build_recognition_document_input(
    *,
    material: MaterialRecord,
    content: bytes,
) -> RecognitionDocumentInput:
    if _is_pdf_material(material):
        return _build_pdf_document_input(content)
    if _is_image_material(material):
        raise RecognitionPreparationError(
            RecognitionFailureDetail(
                stage=RecognitionFailureStage.OCR,
                reason="ocr_not_configured",
            )
        )
    raise RecognitionPreparationError(
        RecognitionFailureDetail(
            stage=RecognitionFailureStage.PDF,
            reason="unsupported_recognition_content_type",
        )
    )


def _build_pdf_document_input(content: bytes) -> RecognitionDocumentInput:
    try:
        reader = PdfReader(BytesIO(content))
    except (PdfReadError, PdfStreamError, ValueError) as error:
        raise RecognitionPreparationError(
            RecognitionFailureDetail(
                stage=RecognitionFailureStage.PDF,
                reason="pdf_parse_failed",
            )
        ) from error

    if reader.is_encrypted:
        raise RecognitionPreparationError(
            RecognitionFailureDetail(
                stage=RecognitionFailureStage.PDF,
                reason="encrypted_pdf",
            )
        )

    extracted_segments: list[str] = []
    image_count = 0
    try:
        for page in reader.pages:
            image_count += len(page.images)
            extracted_text = page.extract_text() or ""
            normalized_text = _normalize_extracted_text(extracted_text)
            if normalized_text:
                extracted_segments.append(normalized_text)
    except FileNotDecryptedError as error:
        raise RecognitionPreparationError(
            RecognitionFailureDetail(
                stage=RecognitionFailureStage.PDF,
                reason="encrypted_pdf",
            )
        ) from error
    except Exception as error:
        raise RecognitionPreparationError(
            RecognitionFailureDetail(
                stage=RecognitionFailureStage.PDF,
                reason="pdf_text_extraction_failed",
            )
        ) from error

    extracted_text = "\n\n".join(extracted_segments).strip()
    if extracted_text:
        return RecognitionDocumentInput(
            source=RecognitionFieldSource.PDF_TEXT,
            text=extracted_text,
            page_count=len(reader.pages),
            text_character_count=len(extracted_text),
        )
    if image_count > 0:
        raise RecognitionPreparationError(
            RecognitionFailureDetail(
                stage=RecognitionFailureStage.OCR,
                reason="ocr_not_configured",
            )
        )
    raise RecognitionPreparationError(
        RecognitionFailureDetail(
            stage=RecognitionFailureStage.PDF,
            reason="blank_pdf",
        )
    )


def _normalize_extracted_text(value: str) -> str:
    lines = [line.strip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines)


def _is_pdf_material(material: MaterialRecord) -> bool:
    if material.content_type == "application/pdf":
        return True
    return Path(material.original_filename).suffix.lower() == ".pdf"


def _is_image_material(material: MaterialRecord) -> bool:
    if material.content_type in {"image/jpeg", "image/png", "image/webp"}:
        return True
    return Path(material.original_filename).suffix.lower() in _IMAGE_SUFFIXES
