from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from trms_backend.api.material_submission_http import build_batch_response, read_uploaded_files
from trms_backend.application.material_submission import (
    MaterialSubmissionTaskNotFoundError,
    MaterialSubmissionTaskNotOpenError,
)
from trms_backend.application.telegram_material_submission import TelegramMaterialSubmissionService
from trms_backend.domain.materials import MaterialType
from trms_backend.domain.tasks import TaskSubmissionDeadlinePassedError, TaskSubmitterNotMemberError


def build_telegram_material_router(
    telegram_material_submission_service: TelegramMaterialSubmissionService,
) -> APIRouter:
    router = APIRouter(tags=["telegram-materials"])

    @router.post("/api/telegram/materials", status_code=status.HTTP_201_CREATED)
    async def submit_telegram_materials(
        telegram_user_id: Annotated[int, Form(gt=0)],
        material_type: Annotated[MaterialType, Form()],
        files: Annotated[list[UploadFile], File(min_length=1)],
        task_id: Annotated[str | None, Form()] = None,
        telegram_username: Annotated[str | None, Form()] = None,
    ):
        uploaded_files = await read_uploaded_files(files)
        try:
            result = telegram_material_submission_service.submit(
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                task_id=task_id,
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

        return build_batch_response(
            result.material_submission,
            file_count=len(uploaded_files),
            extra_body={"submission_identity": result.submission_identity},
        )

    return router
