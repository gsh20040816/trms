from __future__ import annotations

from io import BytesIO

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, Update

from trms_backend.application.telegram_bot import (
    TelegramBotWorkflowService,
    TelegramIncomingFile,
)


class AiogramTelegramWebhookProcessor:
    def __init__(
        self,
        *,
        bot_token: str,
        workflow_service: TelegramBotWorkflowService,
    ) -> None:
        self._workflow_service = workflow_service
        self._bot = Bot(token=bot_token)
        self._dispatcher = Dispatcher()
        self._router = Router()
        self._install_handlers()
        self._dispatcher.include_router(self._router)

    async def process_update(self, payload: dict, *, request_id: str) -> None:
        update = Update.model_validate(payload, context={"bot": self._bot})
        await self._dispatcher.feed_update(
            self._bot,
            update,
            request_id=request_id,
        )

    async def run_polling(self, *, drop_pending_updates: bool = False) -> None:
        try:
            await self._bot.delete_webhook(drop_pending_updates=drop_pending_updates)
            await self._dispatcher.start_polling(
                self._bot,
                request_id="telegram-polling",
            )
        finally:
            await self.close()

    async def close(self) -> None:
        await self._bot.session.close()

    def _install_handlers(self) -> None:
        @self._router.message(Command("bind", ignore_mention=True))
        async def handle_bind(message: Message):
            if message.from_user is None:
                return
            response_text = self._workflow_service.start_binding(
                telegram_user_id=message.from_user.id,
                telegram_chat_id=message.chat.id,
                telegram_username=message.from_user.username,
            )
            await message.answer(response_text)

        @self._router.message(Command("tasks", ignore_mention=True))
        async def handle_tasks(message: Message):
            if message.from_user is None:
                return
            await message.answer(
                self._workflow_service.list_tasks(
                    telegram_user_id=message.from_user.id,
                )
            )

        @self._router.message(Command("task", ignore_mention=True))
        async def handle_task(message: Message, command: CommandObject):
            if message.from_user is None:
                return
            await message.answer(
                self._workflow_service.select_task(
                    telegram_user_id=message.from_user.id,
                    submission_key=(command.args or ""),
                )
            )

        @self._router.message()
        async def handle_file_message(message: Message, request_id: str):
            if message.from_user is None:
                return
            incoming_file = await _extract_incoming_file(self._bot, message)
            if incoming_file is None:
                await message.answer(
                    "可用命令：/bind、/tasks、/task <任务提交标识>。"
                    "直接发送 PDF、图片或其他文件时，会先按当前任务的其他材料上传，再由识别结果修正类型。"
                )
                return
            await message.answer(
                self._workflow_service.upload_material(
                    telegram_user_id=message.from_user.id,
                    incoming_file=incoming_file,
                    request_id=request_id,
                )
            )


async def _extract_incoming_file(bot: Bot, message: Message) -> TelegramIncomingFile | None:
    if message.document is not None:
        telegram_file = await bot.get_file(message.document.file_id)
        if telegram_file.file_path is None:
            return None
        payload = await bot.download_file(telegram_file.file_path)
        content = _read_buffer_bytes(payload)
        return TelegramIncomingFile(
            original_filename=message.document.file_name or f"{message.document.file_unique_id}.bin",
            content_type=message.document.mime_type,
            content=content,
        )

    if message.photo:
        largest_photo = max(
            message.photo,
            key=lambda item: (item.file_size or 0, item.width * item.height),
        )
        telegram_file = await bot.get_file(largest_photo.file_id)
        if telegram_file.file_path is None:
            return None
        payload = await bot.download_file(telegram_file.file_path)
        content = _read_buffer_bytes(payload)
        filename = f"telegram-photo-{largest_photo.file_unique_id}.jpg"
        return TelegramIncomingFile(
            original_filename=filename,
            content_type="image/jpeg",
            content=content,
        )

    return None


def _read_buffer_bytes(payload: BytesIO | None) -> bytes:
    if payload is None:
        return b""
    payload.seek(0)
    return payload.read()
