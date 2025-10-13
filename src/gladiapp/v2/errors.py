from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class TranscriptionError(BaseModel):
    """Structured error information from Gladia API."""
    timestamp: str = ""
    path: str = ""
    request_id: str = Field(default="", alias="requestId")
    status_code: int = Field(default=0, alias="status")
    message: str = ""
    validation_errors: List[str] = Field(default_factory=list, alias="validationErrors")

    def reset(self) -> None:
        self.timestamp = ""
        self.path = ""
        self.request_id = ""
        self.status_code = 0
        self.message = ""
        self.validation_errors = []

    @classmethod
    def from_json(cls, data: dict | str) -> "TranscriptionError":
        if isinstance(data, str):
            import json
            data = json.loads(data)
        return cls.model_validate(data)

    def to_string(self) -> str:
        return f"[{self.status_code}] {self.message} (request_id={self.request_id})"
