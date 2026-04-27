from fastapi import APIRouter, HTTPException, status

from trms_backend.domain.materials import MaterialRepository
from trms_backend.domain.recognitions import (
    RecognitionTaskCreate,
    RecognitionTaskRepository,
    RecognitionTaskStatusTransitionError,
    RecognitionTaskStatusUpdate,
    ensure_recognition_task_can_transition,
)


def build_recognition_router(
    material_repository: MaterialRepository,
    recognition_task_repository: RecognitionTaskRepository,
) -> APIRouter:
    router = APIRouter(tags=["recognitions"])

    @router.post(
        "/api/materials/{material_id}/recognition-tasks",
        status_code=status.HTTP_201_CREATED,
    )
    def create_recognition_task(material_id: str):
        material = material_repository.get(material_id)
        if material is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")

        task = recognition_task_repository.create(RecognitionTaskCreate(material_id=material_id))
        return {"item": task}

    @router.get("/api/materials/{material_id}/recognition-tasks")
    def list_recognition_tasks(material_id: str):
        material = material_repository.get(material_id)
        if material is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="material not found")

        return {"items": recognition_task_repository.list_by_material(material_id)}

    @router.patch("/api/recognition-tasks/{recognition_task_id}/status")
    def update_recognition_task_status(
        recognition_task_id: str,
        payload: RecognitionTaskStatusUpdate,
    ):
        task = recognition_task_repository.get(recognition_task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="recognition task not found",
            )
        try:
            ensure_recognition_task_can_transition(task.status, payload.target_status)
        except RecognitionTaskStatusTransitionError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

        updated = recognition_task_repository.update_status(
            recognition_task_id,
            payload.target_status,
            payload.result,
            payload.failure,
        )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="recognition task not found",
            )
        return {"item": updated}

    return router
