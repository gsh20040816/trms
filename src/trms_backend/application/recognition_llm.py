from __future__ import annotations

from enum import StrEnum
import json
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, ValidationError, model_validator

from trms_backend.domain.invoices import ExpenseType
from trms_backend.domain.materials import MaterialRecord, MaterialType
from trms_backend.domain.recognitions import (
    RecognitionFailureDetail,
    RecognitionFailureStage,
    RecognitionFieldResult,
    RecognitionFieldSource,
    RecognitionFieldStatus,
)
from trms_backend.runtime_config import LLMProviderConfig

LOW_CONFIDENCE_THRESHOLD = 0.8
PROMPT_VERSION = "trms-recognition-v2"


class RecognitionInputSource(StrEnum):
    PDF_TEXT = "pdf_text"
    PDF_FILE = "pdf_file"
    IMAGE_FILE = "image_file"


class RecognitionDocumentInput(BaseModel):
    source: RecognitionInputSource
    text: str | None = None
    page_count: int | None = Field(default=None, ge=1)
    text_character_count: int | None = Field(default=None, ge=1)
    file_name: str | None = None
    media_type: str | None = None
    data_url: str | None = None
    byte_count: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_source_payload(self) -> RecognitionDocumentInput:
        if self.source is RecognitionInputSource.PDF_TEXT:
            if self.text is None or self.page_count is None or self.text_character_count is None:
                raise ValueError("pdf_text recognition input requires extracted text metadata")
            if self.file_name is not None or self.media_type is not None or self.data_url is not None:
                raise ValueError("pdf_text recognition input must not embed file payload")
            if len(self.text) != self.text_character_count:
                raise ValueError("text_character_count must match extracted text length")
            return self

        if self.file_name is None or self.media_type is None or self.data_url is None:
            raise ValueError("file-backed recognition input requires file payload metadata")
        if not self.data_url.startswith(f"data:{self.media_type};base64,"):
            raise ValueError("file-backed recognition input must carry matching base64 data url")
        if self.source is RecognitionInputSource.PDF_FILE and self.page_count is None:
            raise ValueError("pdf_file recognition input requires page_count")
        if self.source is RecognitionInputSource.IMAGE_FILE and self.page_count is not None:
            raise ValueError("image_file recognition input must not persist page_count")
        if self.text is not None or self.text_character_count is not None:
            raise ValueError("file-backed recognition input must not persist extracted text")
        return self

    def to_prompt_payload(self) -> dict[str, Any]:
        if self.source is RecognitionInputSource.PDF_TEXT:
            return {
                "source": self.source.value,
                "text": self.text,
                "page_count": self.page_count,
                "text_character_count": self.text_character_count,
            }
        payload: dict[str, Any] = {
            "source": self.source.value,
            "file_name": self.file_name,
            "media_type": self.media_type,
            "byte_count": self.byte_count,
        }
        if self.page_count is not None:
            payload["page_count"] = self.page_count
        return payload

    def to_safe_log_payload(self) -> dict[str, Any]:
        return self.to_prompt_payload()

    def to_message_content(self, *, metadata_json: str) -> str | list[dict[str, Any]]:
        if self.source is RecognitionInputSource.PDF_TEXT:
            return metadata_json

        content: list[dict[str, Any]] = [{"type": "text", "text": metadata_json}]
        if self.source is RecognitionInputSource.PDF_FILE:
            content.append(
                {
                    "type": "file",
                    "file": {
                        "filename": self.file_name,
                        "file_data": self.data_url,
                    },
                }
            )
            return content

        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": self.data_url,
                    "detail": "high",
                },
            }
        )
        return content


class RecognitionTextField(BaseModel):
    value: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class RecognitionIntegerField(BaseModel):
    value: int
    confidence: float = Field(ge=0, le=1)


class RecognitionDatetimeField(BaseModel):
    value: datetime
    confidence: float = Field(ge=0, le=1)


class RecognitionExpenseTypeField(BaseModel):
    value: ExpenseType
    confidence: float = Field(ge=0, le=1)


class RecognitionMaterialTypeField(BaseModel):
    value: MaterialType
    confidence: float = Field(ge=0, le=1)


class RecognitionStructuredOutput(BaseModel):
    invoice_number: RecognitionTextField | None = None
    amount_cents: RecognitionIntegerField | None = None
    buyer_name: RecognitionTextField | None = None
    tax_number: RecognitionTextField | None = None
    transaction_time: RecognitionDatetimeField | None = None
    location: RecognitionTextField | None = None
    expense_type: RecognitionExpenseTypeField | None = None
    material_type: RecognitionMaterialTypeField | None = None
    trip_route: RecognitionTextField | None = None
    transport_mode: RecognitionTextField | None = None
    cabin_class: RecognitionTextField | None = None


class RecognitionLlmResponse(BaseModel):
    output: RecognitionStructuredOutput


class RecognitionLlmExtractionResult(BaseModel):
    raw_response: dict[str, Any]
    recognized_fields: dict[str, RecognitionFieldResult]

    def has_pending_confirmation(self) -> bool:
        return any(
            field.status is RecognitionFieldStatus.NEEDS_CONFIRMATION
            for field in self.recognized_fields.values()
        )


class RecognitionLlmExecutionError(ValueError):
    def __init__(
        self,
        *,
        failure: RecognitionFailureDetail,
        raw_response: dict[str, Any] | None = None,
    ) -> None:
        self.failure = failure
        self.raw_response = raw_response or {}
        super().__init__(failure.reason)


class RecognitionLlmClient(Protocol):
    def recognize(
        self,
        *,
        material: MaterialRecord,
        document_input: RecognitionDocumentInput,
    ) -> RecognitionLlmExtractionResult:
        raise NotImplementedError


class OpenAiCompatibleRecognitionClient:
    def __init__(
        self,
        provider_config: LLMProviderConfig,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._provider_config = provider_config
        self._http_client = http_client

    def recognize(
        self,
        *,
        material: MaterialRecord,
        document_input: RecognitionDocumentInput,
    ) -> RecognitionLlmExtractionResult:
        request_payload = _build_chat_completions_payload(
            provider_base_url=self._provider_config.base_url,
            model=self._provider_config.model,
            material=material,
            document_input=document_input,
        )

        attempt_count = 0
        for attempt in range(self._provider_config.max_retries + 1):
            attempt_count = attempt + 1
            try:
                response_payload = self._post_chat_completions(request_payload)
                break
            except httpx.TimeoutException as error:
                if attempt >= self._provider_config.max_retries:
                    raise RecognitionLlmExecutionError(
                        failure=RecognitionFailureDetail(
                            stage=RecognitionFailureStage.AI,
                            reason="llm_timeout",
                        ),
                        raw_response={
                            "request": _safe_request_summary(request_payload),
                            "attempts": attempt_count,
                        },
                    ) from error
            except httpx.HTTPError as error:
                if attempt >= self._provider_config.max_retries:
                    raise RecognitionLlmExecutionError(
                        failure=RecognitionFailureDetail(
                            stage=RecognitionFailureStage.AI,
                            reason="llm_request_failed",
                        ),
                        raw_response={
                            "request": _safe_request_summary(request_payload),
                            "attempts": attempt_count,
                            "error": str(error),
                        },
                    ) from error
        else:
            raise AssertionError("unreachable retry loop exit")

        raw_content = _extract_message_content(response_payload)
        try:
            parsed_content = json.loads(raw_content)
        except json.JSONDecodeError as error:
            raise RecognitionLlmExecutionError(
                failure=RecognitionFailureDetail(
                    stage=RecognitionFailureStage.AI,
                    reason="llm_output_not_json",
                ),
                raw_response={
                    "request": _safe_request_summary(request_payload),
                    "response": response_payload,
                    "raw_content": raw_content,
                    "attempts": attempt_count,
                },
            ) from error

        normalized_parsed_content = _normalize_llm_response_payload(parsed_content)
        try:
            validated = RecognitionLlmResponse.model_validate(normalized_parsed_content)
        except ValidationError as error:
            raise RecognitionLlmExecutionError(
                failure=RecognitionFailureDetail(
                    stage=RecognitionFailureStage.AI,
                    reason="llm_output_invalid",
                ),
                raw_response={
                    "request": _safe_request_summary(request_payload),
                    "response": response_payload,
                    "parsed_content": normalized_parsed_content,
                    "validation_errors": error.errors(include_url=False),
                    "attempts": attempt_count,
                },
            ) from error

        recognized_fields = _recognized_fields_from_output(validated.output)
        if not recognized_fields:
            raise RecognitionLlmExecutionError(
                failure=RecognitionFailureDetail(
                    stage=RecognitionFailureStage.AI,
                    reason="llm_output_missing_fields",
                ),
                raw_response={
                    "request": _safe_request_summary(request_payload),
                    "response": response_payload,
                    "parsed_content": validated.model_dump(mode="json"),
                    "attempts": attempt_count,
                },
            )

        return RecognitionLlmExtractionResult(
            raw_response={
                "request": _safe_request_summary(request_payload),
                "response": response_payload,
                "parsed_content": validated.model_dump(mode="json"),
                "attempts": attempt_count,
            },
            recognized_fields=recognized_fields,
        )

    def _post_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._http_client is not None:
            response = self._http_client.post(
                "/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

        with httpx.Client(
            base_url=self._provider_config.base_url.rstrip("/"),
            timeout=self._provider_config.timeout_seconds,
        ) as client:
            response = client.post(
                "/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": (
                f"Bearer {self._provider_config.api_key.get_secret_value()}"
            ),
            "Content-Type": "application/json",
        }


def _build_chat_completions_payload(
    *,
    provider_base_url: str,
    model: str,
    material: MaterialRecord,
    document_input: RecognitionDocumentInput,
) -> dict[str, Any]:
    user_prompt = {
        "prompt_version": PROMPT_VERSION,
        "material_id": material.id,
        "material_type": material.material_type.value,
        "original_filename": material.original_filename,
        "content_type": material.content_type,
        "recognition_input": document_input.to_prompt_payload(),
        "instructions": [
            "Return JSON only.",
            "Do not fabricate fields that are not supported by the provided document.",
            "Use amount_cents as integer cents.",
            "Use ISO 8601 with timezone for transaction_time when available.",
            "Use TRMS enums for expense_type and material_type.",
            "For Chinese invoices, only extract buyer_name and tax_number when they are explicitly visible on the document.",
            "If the document only shows a date but not a complete time, keep transaction_time absent instead of inventing a time.",
            "For RMB amounts, normalize yuan to integer cents and ignore currency symbols such as 元, ￥ and commas.",
        ],
    }
    user_prompt_json = json.dumps(user_prompt, ensure_ascii=False)
    return {
        "model": model,
        "response_format": _build_response_format(provider_base_url),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You extract structured reimbursement metadata from Chinese university reimbursement materials. "
                    f"Prompt version: {PROMPT_VERSION}. "
                    "Return JSON only. "
                    "The top-level object must contain an 'output' field. "
                    "Inside 'output', only use these known field names when the document explicitly supports them: "
                    "invoice_number, amount_cents, buyer_name, tax_number, transaction_time, "
                    "location, expense_type, material_type, trip_route, transport_mode, cabin_class. "
                    "Each populated field must be an object with 'value' and 'confidence'. "
                    "Cover common mainland China reimbursement materials such as VAT electronic invoices, paper invoice scans, "
                    "train or flight itineraries, rideshare receipts, hotel invoices, competition notices and payment records. "
                    "Do not guess missing fields. If a field is blurred, absent, ambiguous, or contradicted, omit it. "
                    "For buyer_name and tax_number, only extract them when the invoice header or tax identifier is explicitly visible. "
                    "For amount_cents, convert RMB yuan to integer cents and ignore currency symbols or separators. "
                    "For transaction_time, use the clearest transaction or issue timestamp on the document; if only a date is present, leave the field absent. "
                    "For expense_type and material_type, choose only TRMS enum values that are directly supported by the document evidence. "
                    "For scanned PDFs or photos, rely only on the visible content in the supplied file, not on filename guesses."
                ),
            },
            {
                "role": "user",
                "content": document_input.to_message_content(metadata_json=user_prompt_json),
            },
        ],
    }


def _extract_message_content(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RecognitionLlmExecutionError(
            failure=RecognitionFailureDetail(
                stage=RecognitionFailureStage.AI,
                reason="llm_output_invalid",
            ),
            raw_response={"response": response_payload},
        )

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise RecognitionLlmExecutionError(
            failure=RecognitionFailureDetail(
                stage=RecognitionFailureStage.AI,
                reason="llm_output_invalid",
            ),
            raw_response={"response": response_payload},
        )

    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                text_parts.append(item["text"])
        if text_parts:
            return "".join(text_parts)

    raise RecognitionLlmExecutionError(
        failure=RecognitionFailureDetail(
            stage=RecognitionFailureStage.AI,
            reason="llm_output_invalid",
        ),
        raw_response={"response": response_payload},
    )


def _recognized_fields_from_output(
    output: RecognitionStructuredOutput,
) -> dict[str, RecognitionFieldResult]:
    recognized_fields: dict[str, RecognitionFieldResult] = {}
    for field_name, field_payload in output.model_dump(mode="json", exclude_none=True).items():
        if not isinstance(field_payload, dict):
            continue
        value = field_payload.get("value")
        confidence = field_payload.get("confidence")
        if confidence is None:
            continue
        status = (
            RecognitionFieldStatus.NEEDS_CONFIRMATION
            if float(confidence) < LOW_CONFIDENCE_THRESHOLD
            else RecognitionFieldStatus.RECOGNIZED
        )
        recognized_fields[field_name] = RecognitionFieldResult(
            value=value,
            source=RecognitionFieldSource.AI,
            confidence=float(confidence),
            status=status,
        )
    return recognized_fields


def _safe_request_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": payload.get("model"),
        "response_format": payload.get("response_format"),
        "message_count": len(payload.get("messages", [])),
        "user_prompt": _extract_safe_user_prompt(payload),
    }


def _extract_safe_user_prompt(payload: dict[str, Any]) -> dict[str, Any] | None:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return None

    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                return {"raw_text": content}
            return parsed if isinstance(parsed, dict) else {"raw_value": parsed}
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict) or item.get("type") != "text":
                    continue
                text = item.get("text")
                if not isinstance(text, str):
                    continue
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    return {"raw_text": text}
                return parsed if isinstance(parsed, dict) else {"raw_value": parsed}
    return None


def _build_response_format(provider_base_url: str) -> dict[str, Any]:
    if _uses_deepseek_json_object(provider_base_url):
        return {"type": "json_object"}

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "trms_structured_recognition",
            "strict": True,
            "schema": RecognitionLlmResponse.model_json_schema(),
        },
    }


def _uses_deepseek_json_object(provider_base_url: str) -> bool:
    hostname = urlparse(provider_base_url).hostname or ""
    normalized_hostname = hostname.strip().lower()
    return normalized_hostname == "api.deepseek.com" or normalized_hostname.endswith(".deepseek.com")


def _normalize_llm_response_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    if "output" in payload:
        return payload

    known_output_fields = set(RecognitionStructuredOutput.model_fields.keys())
    if payload and set(payload.keys()).issubset(known_output_fields):
        return {"output": payload}
    return payload
