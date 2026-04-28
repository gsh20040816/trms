from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from trms_backend.api.material_submission_http import read_uploaded_files
from trms_backend.application.email_material_submission import (
    EmailMaterialSubmissionFormatError,
    EmailMaterialSubmissionService,
)
from trms_backend.application.material_submission import MaterialSubmissionTaskNotOpenError
from trms_backend.domain.tasks import TaskSubmissionDeadlinePassedError, TaskSubmitterNotMemberError


def build_email_material_router(
    email_material_submission_service: EmailMaterialSubmissionService,
) -> APIRouter:
    router = APIRouter(tags=["email-materials"])

    @router.post("/api/email/materials", status_code=status.HTTP_201_CREATED)
    async def submit_email_materials(
        sender_email: Annotated[str, Form(min_length=1)],
        subject: Annotated[str, Form(min_length=1)],
        body: Annotated[str, Form()],
        files: Annotated[list[UploadFile] | None, File()] = None,
        resolved_member_id: Annotated[str | None, Form()] = None,
    ):
        if not files:
            return _build_email_format_error_response(
                error_code="missing_attachments",
                detail="formatted email must include at least one attachment",
            )

        uploaded_files = await read_uploaded_files(files)
        try:
            result = email_material_submission_service.submit(
                sender_email=sender_email,
                subject=subject,
                body=body,
                resolved_member_id=resolved_member_id,
                files=uploaded_files,
            )
        except EmailMaterialSubmissionFormatError as error:
            return _build_email_format_error_response(
                error_code=error.error_code,
                detail=str(error),
            )
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

        return _build_email_batch_response(
            result.material_submission,
            extra_body={"parsed_email": result.parsed_email},
        )

    return router


def _build_email_format_error_response(*, error_code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"status": "failed", "error_code": error_code, "detail": detail},
    )


def _build_email_batch_response(result, *, extra_body: dict[str, Any] | None = None):
    response_body: dict[str, Any] = {"status": "success", "items": result.records}
    if extra_body:
        response_body.update(extra_body)

    failures = [
        {
            "original_filename": failure.original_filename,
            "error_code": _map_email_failure_code(failure.error_code),
            "detail": failure.detail,
        }
        for failure in result.failures
    ]
    if not failures:
        return response_body

    response_body["failures"] = failures
    if result.records:
        response_body["status"] = "partial_success"
        return JSONResponse(
            status_code=status.HTTP_207_MULTI_STATUS,
            content=jsonable_encoder(response_body),
        )

    response_body["status"] = "failed"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(response_body),
    )


def _map_email_failure_code(error_code: str) -> str:
    if error_code == "missing_filename":
        return "attachment_missing_filename"
    return error_code
