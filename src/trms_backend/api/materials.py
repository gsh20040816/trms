from typing import Annotated

from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from trms_backend.domain.materials import (
    MaterialCreate,
    MaterialFileStorage,
    MaterialUploadEmptyFileError,
    MaterialUploadMissingFilenameError,
    MaterialUploadTooLargeError,
    MaterialUploadUnsupportedContentTypeError,
    MaterialUploadValidationError,
    MaterialRepository,
    MaterialType,
    SubmissionChannel,
    validate_material_upload,
)
from trms_backend.domain.tasks import (
    TaskRepository,
    TaskStatus,
    TaskSubmissionDeadlinePassedError,
    TaskSubmitterNotMemberError,
    ensure_task_accepts_member_submission,
)


def _raise_material_upload_http_error(error: MaterialUploadValidationError) -> None:
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


def _material_upload_error_code(error: MaterialUploadValidationError) -> str:
    if isinstance(error, MaterialUploadMissingFilenameError):
        return "missing_filename"
    if isinstance(error, MaterialUploadEmptyFileError):
        return "empty_file"
    if isinstance(error, MaterialUploadUnsupportedContentTypeError):
        return "unsupported_content_type"
    if isinstance(error, MaterialUploadTooLargeError):
        return "file_too_large"
    return "validation_error"


def build_material_router(
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    material_file_storage: MaterialFileStorage,
) -> APIRouter:
    router = APIRouter(prefix="/api/tasks/{task_id}/materials", tags=["materials"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    async def submit_materials(
        task_id: str,
        submitter_id: Annotated[str, Form(min_length=1)],
        channel: Annotated[SubmissionChannel, Form()],
        material_type: Annotated[MaterialType, Form()],
        files: Annotated[list[UploadFile], File(min_length=1)],
    ):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        if task.status != TaskStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="task is not open for material submission",
            )
        try:
            ensure_task_accepts_member_submission(task, submitter_id=submitter_id)
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

        batch_mode = len(files) > 1
        validated_uploads: list[tuple[str, str | None, bytes]] = []
        failures: list[dict[str, str | None]] = []
        for file in files:
            content = await file.read()
            try:
                validate_material_upload(
                    original_filename=file.filename,
                    content_type=file.content_type,
                    content=content,
                )
            except MaterialUploadValidationError as error:
                if not batch_mode:
                    _raise_material_upload_http_error(error)
                failures.append(
                    {
                        "original_filename": file.filename,
                        "error_code": _material_upload_error_code(error),
                        "detail": str(error),
                    }
                )
                continue
            validated_uploads.append((file.filename or "", file.content_type, content))

        records = []
        for original_filename, content_type, content in validated_uploads:
            stored_file = material_file_storage.save(
                task_id=task_id,
                original_filename=original_filename,
                content_type=content_type,
                content=content,
            )
            records.append(
                material_repository.create(
                    MaterialCreate(
                        task_id=task_id,
                        submitter_id=submitter_id,
                        channel=channel,
                        material_type=material_type,
                        storage_key=stored_file.storage_key,
                        original_filename=stored_file.original_filename,
                        content_type=stored_file.content_type,
                        size_bytes=stored_file.size_bytes,
                        sha256=stored_file.sha256,
                    )
                )
            )
        response_body: dict[str, object] = {
            "status": "success",
            "items": records,
        }
        if not failures:
            return response_body

        response_body["failures"] = failures
        if records:
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

    @router.get("")
    def list_materials(task_id: str):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return {"items": material_repository.list_by_task(task_id)}

    return router
