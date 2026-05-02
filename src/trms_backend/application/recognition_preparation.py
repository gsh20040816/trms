from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image

from trms_backend.application.metrics import MetricsCollector, NoOpMetricsCollector
from trms_backend.application.recognition_llm import (
    RecognitionDocumentInput,
    RecognitionInputSource,
    RecognitionLlmClient,
    RecognitionLlmExecutionError,
)
from trms_backend.application.recognition_audit import (
    SYSTEM_RECOGNITION_ACTOR_ID,
    record_recognition_result_audit,
)
from trms_backend.application.recognition_runtime import (
    RecognitionLlmCapability,
)
from trms_backend.domain.audit_logs import AuditLogRepository
from trms_backend.domain.materials import (
    MaterialFileStorage,
    MaterialRecord,
    MaterialRepository,
    MaterialType,
)
from trms_backend.domain.recognitions import (
    RecognitionFailureDetail,
    RecognitionFailureStage,
    RecognitionFieldResult,
    RecognitionFieldStatus,
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
        audit_log_repository: AuditLogRepository,
        llm_capability: RecognitionLlmCapability,
        recognition_llm_client: RecognitionLlmClient | None = None,
        metrics_collector: MetricsCollector | None = None,
    ) -> None:
        self._material_repository = material_repository
        self._material_file_storage = material_file_storage
        self._recognition_task_repository = recognition_task_repository
        self._audit_log_repository = audit_log_repository
        self._llm_capability = llm_capability
        self._recognition_llm_client = recognition_llm_client
        self._metrics_collector = metrics_collector or NoOpMetricsCollector()

    def execute(
        self,
        recognition_task_id: str,
        *,
        actor_id: str = SYSTEM_RECOGNITION_ACTOR_ID,
        request_id: str | None = None,
    ) -> RecognitionTaskRecord:
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
                material=material,
                actor_id=actor_id,
                request_id=request_id,
            )

        try:
            document_input = build_recognition_document_input(material=material, content=content)
        except RecognitionPreparationError as error:
            return self._fail_task(
                recognition_task_id=recognition_task_id,
                raw_response=base_payload,
                failure=error.failure,
                material=material,
                actor_id=actor_id,
                request_id=request_id,
            )

        base_payload["preparation"]["recognition_input"] = document_input.to_safe_log_payload()
        if self._recognition_llm_client is None:
            return self._fail_task(
                recognition_task_id=recognition_task_id,
                raw_response=base_payload,
                failure=(
                    self._llm_capability.failure
                    if self._llm_capability.failure is not None
                    else RecognitionFailureDetail(
                        stage=RecognitionFailureStage.AI,
                        reason="structured_recognition_not_configured",
                    )
                ),
                material=material,
                actor_id=actor_id,
                request_id=request_id,
            )

        try:
            extraction = self._recognition_llm_client.recognize(
                material=material,
                document_input=document_input,
            )
        except RecognitionLlmExecutionError as error:
            if (
                _is_pdf_material(material)
                and document_input.source is RecognitionInputSource.PDF_TEXT
            ):
                try:
                    fallback_document_input = _build_rendered_pdf_document_input(
                        material,
                        content,
                        require_visible_content=False,
                    )
                except RecognitionPreparationError:
                    fallback_document_input = None
                if fallback_document_input is not None:
                    base_payload["preparation"]["fallback_recognition_input"] = (
                        fallback_document_input.to_safe_log_payload()
                    )
                    try:
                        extraction = self._recognition_llm_client.recognize(
                            material=material,
                            document_input=fallback_document_input,
                        )
                    except RecognitionLlmExecutionError as fallback_error:
                        raw_response = dict(base_payload)
                        raw_response["llm"] = {
                            "text_attempt": error.raw_response,
                            "image_fallback_attempt": fallback_error.raw_response,
                        }
                        return self._fail_task(
                            recognition_task_id=recognition_task_id,
                            raw_response=raw_response,
                            failure=fallback_error.failure,
                            material=material,
                            actor_id=actor_id,
                            request_id=request_id,
                        )
                    raw_response = dict(base_payload)
                    raw_response["llm"] = {
                        "text_attempt": error.raw_response,
                        "image_fallback_attempt": extraction.raw_response,
                    }
                    return self._complete_task(
                        recognition_task_id=recognition_task_id,
                        raw_response=raw_response,
                        recognized_fields=extraction.recognized_fields,
                        target_status=(
                            RecognitionTaskStatus.NEEDS_CONFIRMATION
                            if extraction.has_pending_confirmation()
                            else RecognitionTaskStatus.SUCCEEDED
                        ),
                        material=material,
                        actor_id=actor_id,
                        request_id=request_id,
                    )
            raw_response = dict(base_payload)
            raw_response["llm"] = error.raw_response
            return self._fail_task(
                recognition_task_id=recognition_task_id,
                raw_response=raw_response,
                failure=error.failure,
                material=material,
                actor_id=actor_id,
                request_id=request_id,
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
            material=material,
            actor_id=actor_id,
            request_id=request_id,
        )

    def _fail_task(
        self,
        *,
        recognition_task_id: str,
        raw_response: dict[str, object],
        failure: RecognitionFailureDetail,
        material: MaterialRecord,
        actor_id: str,
        request_id: str | None,
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
        record_recognition_result_audit(
            self._audit_log_repository,
            actor_id=actor_id,
            recognition_task=updated,
            task_id=material.task_id,
            request_id=request_id,
        )
        self._metrics_collector.record_recognition_task_status(
            status=updated.status,
            failure_stage=updated.failure.stage if updated.failure is not None else None,
        )
        return updated

    def _complete_task(
        self,
        *,
        recognition_task_id: str,
        raw_response: dict[str, object],
        recognized_fields: dict[str, RecognitionFieldResult],
        target_status: RecognitionTaskStatus,
        material: MaterialRecord,
        actor_id: str,
        request_id: str | None,
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
        material = self._maybe_auto_update_material_type(
            material=material,
            recognized_fields=recognized_fields,
        )
        record_recognition_result_audit(
            self._audit_log_repository,
            actor_id=actor_id,
            recognition_task=updated,
            task_id=material.task_id,
            request_id=request_id,
        )
        self._metrics_collector.record_recognition_task_status(status=updated.status)
        return updated

    def _maybe_auto_update_material_type(
        self,
        *,
        material: MaterialRecord,
        recognized_fields: dict[str, RecognitionFieldResult],
    ) -> MaterialRecord:
        recognized_material_type = recognized_fields.get("material_type")
        if (
            recognized_material_type is None
            or recognized_material_type.status is not RecognitionFieldStatus.RECOGNIZED
            or not isinstance(recognized_material_type.value, str)
        ):
            return material

        try:
            next_material_type = MaterialType(recognized_material_type.value)
        except ValueError:
            return material
        if next_material_type is MaterialType.OTHER_ATTACHMENT:
            return material
        if next_material_type is material.material_type:
            return material
        if not _can_auto_update_material_type(
            current_material_type=material.material_type,
            next_material_type=next_material_type,
        ):
            return material

        return (
            self._material_repository.update_material_type(
                material_id=material.id,
                material_type=next_material_type,
            )
            or material
        )


def _can_auto_update_material_type(
    *,
    current_material_type: MaterialType,
    next_material_type: MaterialType,
) -> bool:
    if current_material_type is MaterialType.INVOICE or next_material_type is MaterialType.INVOICE:
        return current_material_type is MaterialType.OTHER_ATTACHMENT
    return True

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
        return _build_pdf_document_input(material, content)
    if _is_image_material(material):
        return _build_image_document_input(material, content)
    raise RecognitionPreparationError(
        RecognitionFailureDetail(
            stage=RecognitionFailureStage.PDF,
            reason="unsupported_recognition_content_type",
        )
    )


def _build_pdf_document_input(
    material: MaterialRecord,
    content: bytes,
) -> RecognitionDocumentInput:
    document = _open_pdf_document(content)
    try:
        extracted_segments: list[str] = []
        for page in document:
            extracted_text = page.get_text("text", sort=True) or ""
            normalized_text = _normalize_extracted_text(extracted_text)
            if normalized_text:
                extracted_segments.append(normalized_text)
        extracted_text = "\n\n".join(extracted_segments).strip()
        if extracted_text:
            return RecognitionDocumentInput(
                source=RecognitionInputSource.PDF_TEXT,
                text=extracted_text,
                page_count=document.page_count,
                text_character_count=len(extracted_text),
            )
    except Exception as error:
        raise RecognitionPreparationError(
            RecognitionFailureDetail(
                stage=RecognitionFailureStage.PDF,
                reason="pdf_text_extraction_failed",
            )
        ) from error
    finally:
        document.close()

    return _build_rendered_pdf_document_input(
        material,
        content,
        require_visible_content=True,
    )


def _normalize_extracted_text(value: str) -> str:
    lines = [line.strip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines)


def _build_image_document_input(
    material: MaterialRecord,
    content: bytes,
) -> RecognitionDocumentInput:
    media_type = _resolve_image_media_type(material)
    return RecognitionDocumentInput(
        source=RecognitionInputSource.IMAGE_FILE,
        file_name=material.original_filename,
        media_type=media_type,
        data_url=_build_base64_data_url(content, media_type=media_type),
        byte_count=len(content),
    )


def _build_base64_data_url(content: bytes, *, media_type: str) -> str:
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def _build_rendered_pdf_document_input(
    material: MaterialRecord,
    content: bytes,
    *,
    require_visible_content: bool,
) -> RecognitionDocumentInput:
    document = _open_pdf_document(content)
    try:
        if require_visible_content and not any(_page_has_visible_content(page) for page in document):
            raise RecognitionPreparationError(
                RecognitionFailureDetail(
                    stage=RecognitionFailureStage.PDF,
                    reason="blank_pdf",
                )
            )
        rendered_png = _render_pdf_document_to_png(document)
    finally:
        document.close()
    rendered_file_name = f"{Path(material.original_filename).stem}.png"
    return RecognitionDocumentInput(
        source=RecognitionInputSource.IMAGE_FILE,
        file_name=rendered_file_name,
        media_type="image/png",
        data_url=_build_base64_data_url(rendered_png, media_type="image/png"),
        byte_count=len(rendered_png),
    )


def _open_pdf_document(content: bytes) -> fitz.Document:
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as error:
        raise RecognitionPreparationError(
            RecognitionFailureDetail(
                stage=RecognitionFailureStage.PDF,
                reason="pdf_parse_failed",
            )
        ) from error
    if document.needs_pass:
        document.close()
        raise RecognitionPreparationError(
            RecognitionFailureDetail(
                stage=RecognitionFailureStage.PDF,
                reason="encrypted_pdf",
            )
        )
    return document


def _page_has_visible_content(page: fitz.Page) -> bool:
    try:
        if page.get_images(full=True):
            return True
        if page.get_drawings():
            return True
    except Exception:
        return False
    return False


def _render_pdf_document_to_png(document: fitz.Document) -> bytes:
    page_images: list[Image.Image] = []
    try:
        for page in document:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            page_image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
            page_images.append(page_image)
        if not page_images:
            raise RecognitionPreparationError(
                RecognitionFailureDetail(
                    stage=RecognitionFailureStage.PDF,
                    reason="blank_pdf",
                )
            )
        merged_image = _merge_page_images(page_images)
        buffer = BytesIO()
        merged_image.save(buffer, format="PNG")
        merged_image.close()
        return buffer.getvalue()
    except RecognitionPreparationError:
        raise
    except Exception as error:
        raise RecognitionPreparationError(
            RecognitionFailureDetail(
                stage=RecognitionFailureStage.PDF,
                reason="pdf_render_failed",
            )
        ) from error
    finally:
        for image in page_images:
            image.close()


def _merge_page_images(page_images: list[Image.Image]) -> Image.Image:
    width = max(image.width for image in page_images)
    height = sum(image.height for image in page_images)
    merged = Image.new("RGB", (width, height), (255, 255, 255))
    offset_y = 0
    for image in page_images:
        merged.paste(image, (0, offset_y))
        offset_y += image.height
    return merged


def _resolve_image_media_type(material: MaterialRecord) -> str:
    if material.content_type in {"image/jpeg", "image/png", "image/webp"}:
        return material.content_type
    suffix = Path(material.original_filename).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")


def _is_pdf_material(material: MaterialRecord) -> bool:
    if material.content_type == "application/pdf":
        return True
    return Path(material.original_filename).suffix.lower() == ".pdf"


def _is_image_material(material: MaterialRecord) -> bool:
    if material.content_type in {"image/jpeg", "image/png", "image/webp"}:
        return True
    return Path(material.original_filename).suffix.lower() in _IMAGE_SUFFIXES
