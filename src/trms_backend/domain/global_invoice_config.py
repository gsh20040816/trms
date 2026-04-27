from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class GlobalInvoiceConfig(BaseModel):
    invoice_title: str = Field(min_length=1)
    tax_number: str = Field(min_length=1)


class GlobalInvoiceConfigRepository(Protocol):
    def get(self) -> GlobalInvoiceConfig | None:
        raise NotImplementedError

    def set(self, config: GlobalInvoiceConfig) -> GlobalInvoiceConfig:
        raise NotImplementedError
