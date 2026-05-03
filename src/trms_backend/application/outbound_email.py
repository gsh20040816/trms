from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
import smtplib
from typing import Protocol

from trms_backend.runtime_config import OutboundEmailConfig


@dataclass(frozen=True)
class OutboundEmailMessage:
    to_email: str
    subject: str
    text_body: str


class OutboundEmailSender(Protocol):
    def send(self, message: OutboundEmailMessage) -> None:
        raise NotImplementedError


class SmtpOutboundEmailSender:
    def __init__(self, config: OutboundEmailConfig) -> None:
        self._config = config

    def send(self, message: OutboundEmailMessage) -> None:
        email_message = EmailMessage()
        email_message["From"] = self._config.from_address
        email_message["To"] = message.to_email
        email_message["Subject"] = message.subject
        email_message.set_content(message.text_body)

        if self._config.use_ssl:
            with smtplib.SMTP_SSL(
                host=self._config.host,
                port=self._config.port,
                timeout=self._config.timeout_seconds,
            ) as smtp:
                self._login_if_needed(smtp)
                smtp.send_message(email_message)
            return

        with smtplib.SMTP(
            host=self._config.host,
            port=self._config.port,
            timeout=self._config.timeout_seconds,
        ) as smtp:
            smtp.ehlo()
            if self._config.starttls:
                smtp.starttls()
                smtp.ehlo()
            self._login_if_needed(smtp)
            smtp.send_message(email_message)

    def _login_if_needed(self, smtp: smtplib.SMTP) -> None:
        if self._config.username is None or self._config.password is None:
            return
        smtp.login(
            self._config.username,
            self._config.password.get_secret_value(),
        )
