from typing import Annotated

from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from trms_backend.application.material_submission import (
    MaterialSubmissionBatchResult,
    MaterialSubmissionService,
    MaterialSubmissionTaskNotFoundError,
    MaterialSubmissionTaskNotOpenError,
    SubmittedMaterialFile,
)
from trms_backend.domain.materials import (
    MaterialStatus,
    MaterialUploadEmptyFileError,
    MaterialUploadMissingFilenameError,
    MaterialUploadTooLargeError,
    MaterialUploadUnsupportedContentTypeError,
    MaterialUploadValidationError,
    MaterialRepository,
    MaterialType,
    SubmissionChannel,
)
from trms_backend.domain.tasks import (
    TaskRepository,
    TaskSubmissionDeadlinePassedError,
    TaskSubmitterNotMemberError,
    ensure_task_has_member,
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


def build_material_router(
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    material_submission_service: MaterialSubmissionService,
) -> APIRouter:
    router = APIRouter(tags=["materials"])

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
    ):
        if file_count == 1 and not result.records and len(result.failures) == 1:
            _raise_material_upload_http_error(result.failures[0].error)

        failures = [
            {
                "original_filename": failure.original_filename,
                "error_code": failure.error_code,
                "detail": failure.detail,
            }
            for failure in result.failures
        ]
        response_body: dict[str, object] = {
            "status": "success",
            "items": result.records,
        }
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

    @router.post("/api/tasks/{task_id}/materials", status_code=status.HTTP_201_CREATED)
    async def submit_materials(
        task_id: str,
        submitter_id: Annotated[str, Form(min_length=1)],
        channel: Annotated[SubmissionChannel, Form()],
        material_type: Annotated[MaterialType, Form()],
        files: Annotated[list[UploadFile], File(min_length=1)],
    ):
        uploaded_files = await read_uploaded_files(files)
        try:
            result = material_submission_service.submit_to_task(
                task_id=task_id,
                submitter_id=submitter_id,
                channel=channel,
                material_type=material_type,
                files=uploaded_files,
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

        return build_batch_response(result, file_count=len(uploaded_files))

    @router.post("/api/materials/pending-assignment", status_code=status.HTTP_201_CREATED)
    async def submit_pending_assignment_materials(
        channel: Annotated[SubmissionChannel, Form()],
        material_type: Annotated[MaterialType, Form()],
        files: Annotated[list[UploadFile], File(min_length=1)],
        task_id_hint: Annotated[str | None, Form()] = None,
        submitter_id_hint: Annotated[str | None, Form()] = None,
    ):
        uploaded_files = await read_uploaded_files(files)
        result = material_submission_service.submit_pending_assignment(
            channel=channel,
            material_type=material_type,
            files=uploaded_files,
            task_id_hint=task_id_hint,
            submitter_id_hint=submitter_id_hint,
        )
        return build_batch_response(result, file_count=len(uploaded_files))

    @router.post("/api/materials/{material_id}/claim")
    def claim_pending_assignment_material(
        material_id: str,
        administrator_id: Annotated[str, Form(min_length=1)],
        task_id: Annotated[str, Form(min_length=1)],
        submitter_id: Annotated[str, Form(min_length=1)],
    ):
        material = material_repository.get(material_id)
        if material is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")
        if material.status is not MaterialStatus.PENDING_ASSIGNMENT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="material is not pending assignment",
            )

        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        if task.administrator_id != administrator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="administrator is not allowed to claim materials for this task",
            )

        try:
            ensure_task_has_member(task, submitter_id=submitter_id)
        except TaskSubmitterNotMemberError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        claimed_material = material_repository.claim_pending_assignment(
            material_id=material_id,
            task_id=task_id,
            submitter_id=submitter_id,
            claimed_by=administrator_id,
        )
        if claimed_material is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="material is not pending assignment",
            )
        return {"item": claimed_material}

    @router.get("/api/tasks/{task_id}/materials")
    def list_materials(task_id: str):
        task = task_repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return {"items": material_repository.list_by_task(task_id)}

    return router
