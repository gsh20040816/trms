from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
import json
from datetime import datetime
from typing import Any, Protocol, cast

import httpx
from pydantic import BaseModel, Field, ValidationError, create_model, model_validator

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
PROMPT_VERSION = "trms-recognition-v3"
_CONFIDENCE_TEXT_TO_FLOAT = {
    "high": 0.95,
    "medium": 0.7,
    "low": 0.4,
    "高": 0.95,
    "中": 0.7,
    "低": 0.4,
}
_MATERIAL_TYPE_ALIASES = {
    "发票": "invoice",
    "电子发票": "invoice",
    "普通发票": "invoice",
    "增值税电子普通发票": "invoice",
    "增值税普通发票": "invoice",
    "支付记录": "payment_record",
    "付款记录": "payment_record",
    "比赛通知": "competition_notice",
    "通知": "competition_notice",
    "行程单": "itinerary",
    "订单截图": "order_screenshot",
    "订单": "order_screenshot",
    "其他附件": "other_attachment",
}
_EXPENSE_TYPE_ALIASES = {
    "参赛费": "registration",
    "报名费": "registration",
    "会务费": "registration",
    "火车票": "railway",
    "高铁票": "railway",
    "动车票": "railway",
    "飞机票": "airfare",
    "机票": "airfare",
    "航空费": "airfare",
    "市内交通": "local_transport",
    "打车费": "local_transport",
    "网约车": "local_transport",
    "住宿费": "hotel",
    "酒店费": "hotel",
    "房费": "hotel",
    "其他": "other",
}
_DOCUMENT_FAMILY_ALIASES = {
    "发票": "invoice",
    "电子发票": "invoice",
    "普通发票": "invoice",
    "比赛通知": "competition_notice",
    "通知": "competition_notice",
    "支付记录": "payment_record",
    "付款记录": "payment_record",
    "订单截图": "order_screenshot",
    "订单": "order_screenshot",
    "行程单": "itinerary",
    "其他附件": "other_attachment",
    "辅助材料": "other_attachment",
}
_BOOLEAN_TEXT_TO_VALUE = {
    "true": True,
    "false": False,
    "yes": True,
    "no": False,
    "1": True,
    "0": False,
    "是": True,
    "否": False,
    "可报销": True,
    "不可报销": False,
}


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


class RecognitionBooleanField(BaseModel):
    value: bool
    confidence: float = Field(ge=0, le=1)


class RecognitionFloatField(BaseModel):
    value: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)


class RecognitionExpenseTypeField(BaseModel):
    value: ExpenseType
    confidence: float = Field(ge=0, le=1)


class RecognitionMaterialTypeField(BaseModel):
    value: MaterialType
    confidence: float = Field(ge=0, le=1)


class RecognitionDocumentFamily(StrEnum):
    INVOICE = "invoice"
    COMPETITION_NOTICE = "competition_notice"
    PAYMENT_RECORD = "payment_record"
    ORDER_SCREENSHOT = "order_screenshot"
    ITINERARY = "itinerary"
    OTHER_ATTACHMENT = "other_attachment"


class RecognitionDocumentFamilyField(BaseModel):
    value: RecognitionDocumentFamily
    confidence: float = Field(ge=0, le=1)


class RecognitionClassificationOutput(BaseModel):
    document_family: RecognitionDocumentFamilyField
    material_type: RecognitionMaterialTypeField
    expense_type_candidate: RecognitionExpenseTypeField
    is_reimbursement_voucher: RecognitionBooleanField
    classification_confidence: RecognitionFloatField


class RecognitionInvoiceExtractionOutput(BaseModel):
    invoice_number: RecognitionTextField | None = None
    amount_cents: RecognitionIntegerField | None = None
    buyer_name: RecognitionTextField | None = None
    tax_number: RecognitionTextField | None = None
    transaction_time: RecognitionDatetimeField | None = None
    location: RecognitionTextField | None = None
    expense_type: RecognitionExpenseTypeField | None = None
    trip_route: RecognitionTextField | None = None
    transport_mode: RecognitionTextField | None = None
    cabin_class: RecognitionTextField | None = None


class RecognitionPaymentRecordExtractionOutput(BaseModel):
    amount_cents: RecognitionIntegerField | None = None
    transaction_time: RecognitionDatetimeField | None = None
    location: RecognitionTextField | None = None
    expense_type: RecognitionExpenseTypeField | None = None
    trip_route: RecognitionTextField | None = None
    transport_mode: RecognitionTextField | None = None


class RecognitionCompetitionNoticeExtractionOutput(BaseModel):
    transaction_time: RecognitionDatetimeField | None = None
    location: RecognitionTextField | None = None
    expense_type: RecognitionExpenseTypeField | None = None
    trip_route: RecognitionTextField | None = None


class RecognitionOrderScreenshotExtractionOutput(BaseModel):
    amount_cents: RecognitionIntegerField | None = None
    transaction_time: RecognitionDatetimeField | None = None
    location: RecognitionTextField | None = None
    expense_type: RecognitionExpenseTypeField | None = None
    trip_route: RecognitionTextField | None = None
    transport_mode: RecognitionTextField | None = None


class RecognitionItineraryExtractionOutput(BaseModel):
    transaction_time: RecognitionDatetimeField | None = None
    location: RecognitionTextField | None = None
    expense_type: RecognitionExpenseTypeField | None = None
    trip_route: RecognitionTextField | None = None
    transport_mode: RecognitionTextField | None = None
    cabin_class: RecognitionTextField | None = None


class RecognitionOtherAttachmentExtractionOutput(BaseModel):
    transaction_time: RecognitionDatetimeField | None = None
    location: RecognitionTextField | None = None
    expense_type: RecognitionExpenseTypeField | None = None
    trip_route: RecognitionTextField | None = None
    transport_mode: RecognitionTextField | None = None


@dataclass(frozen=True)
class RecognitionExtractionSchemaDefinition:
    name: str
    description: str
    output_model: type[BaseModel]

    @property
    def allowed_field_names(self) -> tuple[str, ...]:
        return tuple(self.output_model.model_fields.keys())


_INVOICE_EXTRACTION_SCHEMA = RecognitionExtractionSchemaDefinition(
    name="invoice",
    description=(
        "For invoices and direct reimbursement vouchers. Extract invoice identity, "
        "amount, buyer/tax identifiers, transaction time/location, and any route or cabin clues."
    ),
    output_model=RecognitionInvoiceExtractionOutput,
)
_PAYMENT_RECORD_EXTRACTION_SCHEMA = RecognitionExtractionSchemaDefinition(
    name="payment_record",
    description=(
        "For bank or platform payment proofs. Extract paid amount, payment time, "
        "location, expense type hints, and any visible trip metadata."
    ),
    output_model=RecognitionPaymentRecordExtractionOutput,
)
_COMPETITION_NOTICE_EXTRACTION_SCHEMA = RecognitionExtractionSchemaDefinition(
    name="competition_notice",
    description=(
        "For notices or official competition announcements. Extract event time, "
        "location, expense type clues, and route references only when explicit."
    ),
    output_model=RecognitionCompetitionNoticeExtractionOutput,
)
_ORDER_SCREENSHOT_EXTRACTION_SCHEMA = RecognitionExtractionSchemaDefinition(
    name="order_screenshot",
    description=(
        "For platform order screenshots. Extract amount, transaction time, location, "
        "expense type hints, and route or ride details when visible."
    ),
    output_model=RecognitionOrderScreenshotExtractionOutput,
)
_ITINERARY_EXTRACTION_SCHEMA = RecognitionExtractionSchemaDefinition(
    name="itinerary",
    description=(
        "For travel itineraries and ticket details. Extract time, location, expense "
        "type, route, transport mode, and cabin or seat class."
    ),
    output_model=RecognitionItineraryExtractionOutput,
)
_OTHER_ATTACHMENT_EXTRACTION_SCHEMA = RecognitionExtractionSchemaDefinition(
    name="other_attachment",
    description=(
        "For uncategorized supporting attachments. Extract only general time, location, "
        "expense type clues, or route hints when they are explicit."
    ),
    output_model=RecognitionOtherAttachmentExtractionOutput,
)
_EXTRACTION_SCHEMA_BY_MATERIAL_TYPE = {
    MaterialType.INVOICE: _INVOICE_EXTRACTION_SCHEMA,
    MaterialType.PAYMENT_RECORD: _PAYMENT_RECORD_EXTRACTION_SCHEMA,
    MaterialType.COMPETITION_NOTICE: _COMPETITION_NOTICE_EXTRACTION_SCHEMA,
    MaterialType.ORDER_SCREENSHOT: _ORDER_SCREENSHOT_EXTRACTION_SCHEMA,
    MaterialType.ITINERARY: _ITINERARY_EXTRACTION_SCHEMA,
    MaterialType.OTHER_ATTACHMENT: _OTHER_ATTACHMENT_EXTRACTION_SCHEMA,
}


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


class RoutedRecognitionClient:
    def __init__(
        self,
        *,
        text_client: RecognitionLlmClient | None = None,
        vlm_client: RecognitionLlmClient | None = None,
        text_provider_config_resolver: Callable[[], LLMProviderConfig | None] | None = None,
        vlm_provider_config_resolver: Callable[[], LLMProviderConfig | None] | None = None,
    ) -> None:
        self._text_client = text_client
        self._vlm_client = vlm_client
        self._text_provider_config_resolver = text_provider_config_resolver
        self._vlm_provider_config_resolver = vlm_provider_config_resolver

    def recognize(
        self,
        *,
        material: MaterialRecord,
        document_input: RecognitionDocumentInput,
    ) -> RecognitionLlmExtractionResult:
        selected_client: RecognitionLlmClient | None
        missing_reason: str
        if document_input.source is RecognitionInputSource.PDF_TEXT:
            selected_client = self._text_client or self._build_resolved_client(
                self._text_provider_config_resolver
            )
            missing_reason = "text_llm_provider_not_configured"
        else:
            selected_client = self._vlm_client or self._build_resolved_client(
                self._vlm_provider_config_resolver
            )
            missing_reason = "vlm_provider_not_configured"

        if selected_client is None:
            raise RecognitionLlmExecutionError(
                failure=RecognitionFailureDetail(
                    stage=RecognitionFailureStage.AI,
                    reason=missing_reason,
                ),
                raw_response={
                    "material_id": material.id,
                    "recognition_input": document_input.to_safe_log_payload(),
                },
            )

        return selected_client.recognize(material=material, document_input=document_input)

    @staticmethod
    def _build_resolved_client(
        resolver: Callable[[], LLMProviderConfig | None] | None,
    ) -> RecognitionLlmClient | None:
        if resolver is None:
            return None
        provider_config = resolver()
        if provider_config is None:
            return None
        return OpenAiCompatibleRecognitionClient(provider_config)


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
        classification_output, classification_fields, classification_raw_response = (
            self._run_recognition_stage(
                request_payload=_build_classification_chat_completions_payload(
                    provider_base_url=self._provider_config.base_url,
                    model=self._provider_config.model,
                    material=material,
                    document_input=document_input,
                ),
                output_model=RecognitionClassificationOutput,
                allow_empty_fields=False,
            )
        )
        classification_output = cast(RecognitionClassificationOutput, classification_output)
        extraction_schema = _select_extraction_schema(classification_output)
        extraction_output, extraction_fields, extraction_raw_response = self._run_recognition_stage(
            request_payload=_build_extraction_chat_completions_payload(
                provider_base_url=self._provider_config.base_url,
                model=self._provider_config.model,
                material=material,
                document_input=document_input,
                classification_output=classification_output,
                extraction_schema=extraction_schema,
            ),
            output_model=extraction_schema.output_model,
            allow_empty_fields=True,
        )
        _ = extraction_output

        recognized_fields = {
            **classification_fields,
            **extraction_fields,
        }

        return RecognitionLlmExtractionResult(
            raw_response={
                "classification": classification_raw_response,
                "selected_schema": {
                    "name": extraction_schema.name,
                    "description": extraction_schema.description,
                    "allowed_fields": list(extraction_schema.allowed_field_names),
                },
                "extraction": extraction_raw_response,
            },
            recognized_fields=recognized_fields,
        )

    def _run_recognition_stage(
        self,
        *,
        request_payload: dict[str, Any],
        output_model: type[BaseModel],
        allow_empty_fields: bool,
    ) -> tuple[BaseModel, dict[str, RecognitionFieldResult], dict[str, Any]]:
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

        normalized_parsed_content = _normalize_llm_response_payload(
            parsed_content,
            known_output_fields=set(output_model.model_fields.keys()),
        )
        if (
            not allow_empty_fields
            and isinstance(normalized_parsed_content, dict)
            and normalized_parsed_content.get("output") == {}
        ):
            raise RecognitionLlmExecutionError(
                failure=RecognitionFailureDetail(
                    stage=RecognitionFailureStage.AI,
                    reason="llm_output_missing_fields",
                ),
                raw_response={
                    "request": _safe_request_summary(request_payload),
                    "response": response_payload,
                    "parsed_content": {"output": _empty_output_payload(output_model)},
                    "attempts": attempt_count,
                },
            )
        response_model = _build_stage_response_model(output_model)
        try:
            validated = response_model.model_validate(normalized_parsed_content)
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

        output = validated.output
        recognized_fields = _recognized_fields_from_output(output)
        if not recognized_fields and not allow_empty_fields:
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
        return (
            output,
            recognized_fields,
            {
                "request": _safe_request_summary(request_payload),
                "response": response_payload,
                "parsed_content": validated.model_dump(mode="json"),
                "attempts": attempt_count,
            },
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


def _build_classification_chat_completions_payload(
    *,
    provider_base_url: str,
    model: str,
    material: MaterialRecord,
    document_input: RecognitionDocumentInput,
) -> dict[str, Any]:
    user_prompt = {
        "prompt_version": PROMPT_VERSION,
        "stage": "classification",
        "material_id": material.id,
        "uploaded_material_type": material.material_type.value,
        "original_filename": material.original_filename,
        "content_type": material.content_type,
        "recognition_input": document_input.to_prompt_payload(),
        "instructions": [
            "Return JSON only.",
            "Stage 1 only: classify the document before extracting detailed metadata.",
            "Always populate document_family, material_type, expense_type_candidate, is_reimbursement_voucher, and classification_confidence.",
            "Use only TRMS enums for document_family, material_type, and expense_type_candidate.",
            "Set is_reimbursement_voucher to true only when the document itself can directly serve as a reimbursement voucher.",
            "classification_confidence.value must be a float between 0 and 1 describing the overall confidence of the classification result.",
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
                    "You classify Chinese university reimbursement materials before metadata extraction. "
                    f"Prompt version: {PROMPT_VERSION}. "
                    "Return JSON only. "
                    "The top-level object must contain an 'output' field. "
                    "Inside 'output', always provide these fields as objects with 'value' and 'confidence': "
                    "document_family, material_type, expense_type_candidate, is_reimbursement_voucher, classification_confidence. "
                    "document_family must be one of: invoice, competition_notice, payment_record, order_screenshot, itinerary, other_attachment. "
                    "material_type must be one of the TRMS material_type enums. "
                    "expense_type_candidate must be one of the TRMS expense_type enums and should use 'other' when no stronger category is supported. "
                    "classification_confidence.value must equal the overall classification confidence in [0, 1]. "
                    "Cover common mainland China reimbursement materials such as VAT electronic invoices, paper invoice scans, "
                    "payment records, competition notices, travel itineraries, train or flight documents, rideshare receipts, "
                    "hotel invoices, and platform order screenshots. "
                    "Do not extract detailed invoice metadata in this stage. "
                    "Do not guess unsupported categories. "
                    "For scanned PDFs or photos, rely only on the visible content in the supplied file, not on filename guesses."
                ),
            },
            {
                "role": "user",
                "content": document_input.to_message_content(metadata_json=user_prompt_json),
            },
        ],
    }


def _build_extraction_chat_completions_payload(
    *,
    provider_base_url: str,
    model: str,
    material: MaterialRecord,
    document_input: RecognitionDocumentInput,
    classification_output: RecognitionClassificationOutput,
    extraction_schema: RecognitionExtractionSchemaDefinition,
) -> dict[str, Any]:
    allowed_fields = list(extraction_schema.allowed_field_names)
    user_prompt = {
        "prompt_version": PROMPT_VERSION,
        "stage": "metadata_extraction",
        "material_id": material.id,
        "material_type": material.material_type.value,
        "original_filename": material.original_filename,
        "content_type": material.content_type,
        "recognition_input": document_input.to_prompt_payload(),
        "classification_result": classification_output.model_dump(mode="json"),
        "selected_schema": {
            "name": extraction_schema.name,
            "description": extraction_schema.description,
            "allowed_fields": allowed_fields,
        },
        "instructions": [
            "Return JSON only.",
            "Stage 2 only: extract metadata allowed by the selected schema.",
            "Do not repeat classification-only fields in this stage.",
            "Do not fabricate fields that are not supported by the provided document.",
            "Use amount_cents as integer cents.",
            "Use ISO 8601 with timezone for transaction_time when available.",
            "Use TRMS enums for expense_type.",
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
                    f"Inside 'output', only use these field names for the selected schema: {', '.join(allowed_fields)}. "
                    "Each populated field must be an object with 'value' and 'confidence'. "
                    f"Selected schema: {extraction_schema.name}. "
                    f"Schema intent: {extraction_schema.description} "
                    "Do not guess missing fields. If a field is blurred, absent, ambiguous, or contradicted, omit it. "
                    "For buyer_name and tax_number, only extract them when the invoice header or tax identifier is explicitly visible. "
                    "For amount_cents, convert RMB yuan to integer cents and ignore currency symbols or separators. "
                    "For transaction_time, use the clearest transaction or issue timestamp on the document; if only a date is present, leave the field absent. "
                    "For expense_type, choose only a TRMS enum value that is directly supported by the document evidence. "
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
    output: BaseModel,
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
    return {"type": "json_object"}


def _normalize_llm_response_payload(
    payload: Any,
    *,
    known_output_fields: set[str],
) -> Any:
    if not isinstance(payload, dict):
        return payload
    if "output" in payload:
        output = payload.get("output")
        if isinstance(output, dict):
            return {
                **payload,
                "output": _normalize_output_fields(output),
            }
        return payload

    if payload and set(payload.keys()).issubset(known_output_fields):
        return {"output": _normalize_output_fields(payload)}
    return payload


def _normalize_output_fields(output: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field_name, field_value in output.items():
        if not isinstance(field_value, dict):
            normalized[field_name] = field_value
            continue

        next_field_value = dict(field_value)
        normalized_confidence = _normalize_confidence_value(next_field_value.get("confidence"))
        if normalized_confidence is not None:
            next_field_value["confidence"] = normalized_confidence

        if field_name == "material_type":
            normalized_material_type = _normalize_material_type_value(next_field_value.get("value"))
            if normalized_material_type is None:
                continue
            next_field_value["value"] = normalized_material_type

        if field_name == "document_family":
            normalized_document_family = _normalize_document_family_value(
                next_field_value.get("value")
            )
            if normalized_document_family is None:
                continue
            next_field_value["value"] = normalized_document_family

        if field_name == "expense_type":
            normalized_expense_type = _normalize_expense_type_value(next_field_value.get("value"))
            if normalized_expense_type is None:
                continue
            next_field_value["value"] = normalized_expense_type

        if field_name == "expense_type_candidate":
            normalized_expense_type = _normalize_expense_type_value(next_field_value.get("value"))
            next_field_value["value"] = normalized_expense_type or ExpenseType.OTHER.value

        if field_name == "classification_confidence":
            normalized_value = _normalize_confidence_value(next_field_value.get("value"))
            if normalized_value is None:
                continue
            next_field_value["value"] = normalized_value

        if field_name == "is_reimbursement_voucher":
            normalized_boolean = _normalize_boolean_value(next_field_value.get("value"))
            if normalized_boolean is None:
                continue
            next_field_value["value"] = normalized_boolean

        normalized[field_name] = next_field_value
    return normalized


def _normalize_confidence_value(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _CONFIDENCE_TEXT_TO_FLOAT:
            return _CONFIDENCE_TEXT_TO_FLOAT[normalized]
        try:
            return float(normalized)
        except ValueError:
            return None
    return None


def _normalize_material_type_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in MaterialType._value2member_map_:
        return normalized
    return _MATERIAL_TYPE_ALIASES.get(value.strip())


def _normalize_expense_type_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in ExpenseType._value2member_map_:
        return normalized
    return _EXPENSE_TYPE_ALIASES.get(value.strip())


def _normalize_document_family_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in RecognitionDocumentFamily._value2member_map_:
        return normalized
    return _DOCUMENT_FAMILY_ALIASES.get(value.strip())


def _normalize_boolean_value(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return _BOOLEAN_TEXT_TO_VALUE.get(value.strip().lower())
    return None


def _select_extraction_schema(
    classification_output: RecognitionClassificationOutput,
) -> RecognitionExtractionSchemaDefinition:
    material_type = classification_output.material_type.value
    return _EXTRACTION_SCHEMA_BY_MATERIAL_TYPE.get(
        material_type,
        _OTHER_ATTACHMENT_EXTRACTION_SCHEMA,
    )


@lru_cache(maxsize=None)
def _build_stage_response_model(output_model: type[BaseModel]) -> type[BaseModel]:
    return create_model(
        f"{output_model.__name__}Response",
        output=(output_model, ...),
    )


def _empty_output_payload(output_model: type[BaseModel]) -> dict[str, None]:
    return {
        field_name: None
        for field_name in output_model.model_fields.keys()
    }
