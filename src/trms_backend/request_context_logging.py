from __future__ import annotations

import logging
from contextvars import ContextVar, Token


_request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
_record_factory_installed = False


def bind_request_id(request_id: str | None) -> Token[str | None]:
    return _request_id_context.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id_context.reset(token)


def get_request_id() -> str | None:
    return _request_id_context.get()


def install_request_id_log_record_factory() -> None:
    global _record_factory_installed

    if _record_factory_installed:
        return

    previous_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = previous_factory(*args, **kwargs)
        request_id = get_request_id()
        if request_id is not None and (
            not hasattr(record, "request_id") or record.request_id is None
        ):
            record.request_id = request_id
        return record

    logging.setLogRecordFactory(record_factory)
    _record_factory_installed = True
