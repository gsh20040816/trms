from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field, field_validator


def normalize_email_host(value: str, *, field_name: str = "email_host") -> str:
    normalized = value.strip().lower()
    if normalized.startswith("@"):
        normalized = normalized[1:]
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if (
        " " in normalized
        or "\t" in normalized
        or "\n" in normalized
        or "\r" in normalized
        or "@" in normalized
    ):
        raise ValueError(f"{field_name} must be a valid host")
    if "." not in normalized:
        raise ValueError(f"{field_name} must be a valid host")
    return normalized


class RegistrationPolicy(BaseModel):
    allowed_email_hosts: list[str] = Field(default_factory=list)

    @field_validator("allowed_email_hosts", mode="before")
    @classmethod
    def normalize_allowed_email_hosts(cls, value: list[str] | None) -> list[str]:
        normalized_hosts: list[str] = []
        for raw_host in value or []:
            host = normalize_email_host(str(raw_host), field_name="allowed_email_hosts")
            if host not in normalized_hosts:
                normalized_hosts.append(host)
        return normalized_hosts

    def is_email_allowed(self, email: str) -> bool:
        host = email.rsplit("@", maxsplit=1)[-1].lower()
        return host in self.allowed_email_hosts


class RegistrationPolicyRepository(Protocol):
    def get(self) -> RegistrationPolicy | None:
        raise NotImplementedError

    def set(self, policy: RegistrationPolicy) -> RegistrationPolicy:
        raise NotImplementedError
