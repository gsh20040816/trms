from typing import Any

from fastapi import HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from trms_backend.application.material_submission import (
    MaterialSubmissionBatchResult,
    SubmittedMaterialFile,
)
from trms_backend.domain.materials import (
    MaterialUploadEmptyFileError,
    MaterialUploadMissingFilenameError,
    MaterialUploadTooLargeError,
    MaterialUploadUnsupportedContentTypeError,
    MaterialUploadValidationError,
)


def raise_material_upload_http_error(error: MaterialUploadValidationError) -> None:
    if isinstance(error, MaterialUploadMissingFilenameError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    if isinstance(error, MaterialUploadEmptyFileError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    if isinstance(error, MaterialUploadUnsupportedContentTypeError):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(error),
        ) from error
    if isinstance(error, MaterialUploadTooLargeError):
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(error),
        ) from error
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(error),
    ) from error


async def read_uploaded_files(files: list[UploadFile]) -> list[SubmittedMaterialFile]:
    uploads: list[SubmittedMaterialFile] = []
    for file in files:
        uploads.append(
            SubmittedMaterialFile(
                original_filename=file.filename,
                content_type=file.content_type,
                content=await file.read(),
            )
        )
    return uploads


def build_batch_response(
    result: MaterialSubmissionBatchResult,
    *,
    file_count: int,
    extra_body: dict[str, Any] | None = None,
):
    if file_count == 1 and not result.records and len(result.failures) == 1:
        raise_material_upload_http_error(result.failures[0].error)

    response_body: dict[str, Any] = {
        "status": "success",
        "items": result.records,
    }
    if extra_body:
        response_body.update(extra_body)

    failures = [
        {
            "original_filename": failure.original_filename,
            "error_code": failure.error_code,
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
