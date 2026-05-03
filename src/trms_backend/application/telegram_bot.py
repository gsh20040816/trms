from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode

from trms_backend.application.material_submission import (
    MaterialSubmissionTaskNotFoundError,
    MaterialSubmissionTaskNotOpenError,
    SubmittedMaterialFile,
)
from trms_backend.application.task_material_upload import TaskMaterialUploadService
from trms_backend.application.telegram_binding_oauth import TelegramBindingOauthService
from trms_backend.domain.materials import MaterialType, SubmissionChannel
from trms_backend.domain.tasks import TaskRepository, TaskSubmissionDeadlinePassedError, TaskSubmitterNotMemberError
from trms_backend.domain.telegram_bindings import TelegramAccountBindingRepository
from trms_backend.domain.telegram_bot import TelegramTaskContextRepository


@dataclass(frozen=True)
class TelegramIncomingFile:
    original_filename: str
    content_type: str | None
    content: bytes


class TelegramBotWorkflowService:
    def __init__(
        self,
        *,
        public_web_base_url: str,
        binding_oauth_service: TelegramBindingOauthService,
        binding_repository: TelegramAccountBindingRepository,
        task_repository: TaskRepository,
        task_context_repository: TelegramTaskContextRepository,
        task_material_upload_service: TaskMaterialUploadService,
    ) -> None:
        self._public_web_base_url = public_web_base_url.rstrip("/")
        self._binding_oauth_service = binding_oauth_service
        self._binding_repository = binding_repository
        self._task_repository = task_repository
        self._task_context_repository = task_context_repository
        self._task_material_upload_service = task_material_upload_service

    def start_binding(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: str | None,
    ) -> str:
        authorization = self._binding_oauth_service.create_authorization(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            telegram_username=telegram_username,
        )
        query = urlencode({"token": authorization.token})
        bind_url = f"{self._public_web_base_url}/telegram/bind?{query}"
        return (
            "请在浏览器中完成账号绑定：\n"
            f"{bind_url}\n\n"
            "登录后确认绑定，绑定成功后再使用 /tasks 查看任务。"
        )

    def list_tasks(self, *, telegram_user_id: int) -> str:
        binding = self._binding_repository.get_by_telegram_user_id(telegram_user_id)
        if binding is None:
            return "当前 Telegram 账号尚未绑定 TRMS 成员身份，请先发送 /bind。"

        tasks = self._task_repository.list_for_member(binding.member_id)
        if not tasks:
            return "当前账号还没有作为成员参与的任务。"

        current_context = self._task_context_repository.get_by_telegram_user_id(telegram_user_id)
        current_task_id = current_context.task_id if current_context is not None else None
        lines = ["你参与的任务："]
        for task in tasks:
            submission_key = task.submission_key or task.email_submission_key or task.id
            marker = " [当前]" if task.id == current_task_id else ""
            lines.append(
                f"- {submission_key}{marker} | {task.competition_name} | 状态 {task.status.value}"
            )
        lines.append("")
        lines.append("使用 /task <任务提交标识> 切换当前任务。")
        return "\n".join(lines)

    def select_task(self, *, telegram_user_id: int, submission_key: str) -> str:
        binding = self._binding_repository.get_by_telegram_user_id(telegram_user_id)
        if binding is None:
            return "当前 Telegram 账号尚未绑定 TRMS 成员身份，请先发送 /bind。"

        normalized_key = submission_key.strip()
        if not normalized_key:
            return "用法：/task <任务提交标识>"
        task = self._task_repository.get_by_email_submission_key(normalized_key)
        if task is None:
            return f"未找到任务提交标识 {normalized_key} 对应的任务。"
        if binding.member_id not in task.member_ids:
            return "你不是该任务成员，不能切换到这个任务。"

        self._task_context_repository.upsert(
            telegram_user_id=telegram_user_id,
            task_id=task.id,
        )
        return (
            f"已切换当前任务：{task.competition_name}\n"
            f"任务提交标识：{task.submission_key or task.email_submission_key or task.id}\n"
            f"当前状态：{task.status.value}"
        )

    def upload_material(
        self,
        *,
        telegram_user_id: int,
        incoming_file: TelegramIncomingFile,
        request_id: str,
    ) -> str:
        binding = self._binding_repository.get_by_telegram_user_id(telegram_user_id)
        if binding is None:
            return "当前 Telegram 账号尚未绑定 TRMS 成员身份，请先发送 /bind。"

        context = self._task_context_repository.get_by_telegram_user_id(telegram_user_id)
        if context is None:
            return "当前还没有选中的任务，请先发送 /tasks 查看任务，再用 /task <任务提交标识> 切换。"

        task = self._task_repository.get(context.task_id)
        if task is None:
            self._task_context_repository.delete(telegram_user_id)
            return "当前任务已不存在，已清空选择。请重新发送 /tasks 查看可用任务。"

        try:
            result = self._task_material_upload_service.submit_to_task(
                task_id=task.id,
                submitter_id=binding.member_id,
                actor_id=binding.member_id,
                channel=SubmissionChannel.TELEGRAM,
                material_type=MaterialType.OTHER_ATTACHMENT,
                files=[
                    SubmittedMaterialFile(
                        original_filename=incoming_file.original_filename,
                        content_type=incoming_file.content_type,
                        content=incoming_file.content,
                    )
                ],
                request_id=request_id,
            )
        except MaterialSubmissionTaskNotFoundError:
            self._task_context_repository.delete(telegram_user_id)
            return "当前任务已不存在，已清空选择。请重新发送 /tasks 查看可用任务。"
        except MaterialSubmissionTaskNotOpenError:
            return (
                f"当前任务 {task.competition_name} 现在不接受材料上传。"
                "请先用 /tasks 查看开放任务，再用 /task <任务提交标识> 切换。"
            )
        except TaskSubmitterNotMemberError:
            self._task_context_repository.delete(telegram_user_id)
            return "你已不在当前任务成员名单中，已清空选择。请联系管理员确认成员范围。"
        except TaskSubmissionDeadlinePassedError:
            return (
                f"当前任务 {task.competition_name} 的成员提交截止时间已过，暂不能继续上传材料。"
            )

        if result.batch_result.failures:
            failure = result.batch_result.failures[0]
            return (
                f"上传失败：{incoming_file.original_filename}\n"
                f"原因：{failure.detail}"
            )

        uploaded = result.items[0]
        return (
            f"上传成功：{uploaded.material.original_filename}\n"
            f"任务：{task.competition_name}\n"
            f"任务提交标识：{task.submission_key or task.email_submission_key or task.id}\n"
            f"识别状态：{uploaded.recognition_status}\n"
            f"识别调度：{result.recognition_dispatch.get('status', 'queued')}"
        )
