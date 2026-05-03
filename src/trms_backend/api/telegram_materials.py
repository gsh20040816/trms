import hmac
from typing import Annotated

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile, status

from trms_backend.api.error_responses import ensure_request_id
from trms_backend.api.material_submission_http import build_batch_response, read_uploaded_files
from trms_backend.application.material_submission import (
    MaterialSubmissionTaskNotFoundError,
    MaterialSubmissionTaskNotOpenError,
)
from trms_backend.application.telegram_material_submission import TelegramMaterialSubmissionService
from trms_backend.domain.materials import MaterialType
from trms_backend.domain.tasks import TaskSubmissionDeadlinePassedError, TaskSubmitterNotMemberError


def _resolve_uploaded_material_type(material_type: MaterialType | None) -> MaterialType:
    return material_type or MaterialType.OTHER_ATTACHMENT


def build_telegram_material_router(
    telegram_material_submission_service: TelegramMaterialSubmissionService,
    *,
    trusted_inbound_token: str | None,
) -> APIRouter:
    router = APIRouter(tags=["telegram-materials"])

    @router.post("/api/telegram/materials", status_code=status.HTTP_201_CREATED)
    async def submit_telegram_materials(
        request: Request,
        telegram_user_id: Annotated[int, Form(gt=0)],
        files: Annotated[list[UploadFile], File(min_length=1)],
        material_type: Annotated[MaterialType | None, Form()] = None,
        task_id: Annotated[str | None, Form()] = None,
        telegram_username: Annotated[str | None, Form()] = None,
        telegram_inbound_token: Annotated[
            str | None,
            Header(alias="X-TRMS-Telegram-Inbound-Token"),
        ] = None,
    ):
        uploaded_files = await read_uploaded_files(files)
        trust_form_telegram_user_id = _is_trusted_telegram_request(
            configured_token=trusted_inbound_token,
            request_token=telegram_inbound_token,
        )
        try:
            result = telegram_material_submission_service.submit(
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                task_id=task_id,
                material_type=_resolve_uploaded_material_type(material_type),
                files=uploaded_files,
                trust_form_telegram_user_id=trust_form_telegram_user_id,
                request_id=ensure_request_id(request),
            )
        except MaterialSubmissionTaskNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        except MaterialSubmissionTaskNotOpenError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="task is not open for material submission",
            )
        except TaskSubmitterNotMemberError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except TaskSubmissionDeadlinePassedError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        return build_batch_response(
            result.material_submission,
            file_count=len(uploaded_files),
            extra_body={"submission_identity": result.submission_identity},
        )

    return router


def _is_trusted_telegram_request(
    *,
    configured_token: str | None,
    request_token: str | None,
) -> bool:
    normalized_configured_token = (configured_token or "").strip()
    if not normalized_configured_token:
        return False

    normalized_request_token = (request_token or "").strip()
    if not normalized_request_token:
        return False

    if not hmac.compare_digest(normalized_request_token, normalized_configured_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid telegram inbound token",
        )

    return True
