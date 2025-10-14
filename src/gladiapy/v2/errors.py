from __future__ import annotations
from typing import List, Optional


class GladiaError(Exception):
    """Base exception for Gladia API errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 0,
        request_id: str = "",
        timestamp: str = "",
        path: str = "",
        validation_errors: Optional[List[str]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.timestamp = timestamp
        self.path = path
        self.validation_errors = validation_errors or []
    
    @classmethod
    def from_response(cls, resp, default_message: str = "API request failed") -> "GladiaError":
        try:
            data = resp.json()
        except Exception:
            data = {}
        message = data.get("message", default_message)
        status_code = data.get("statusCode", data.get("status", resp.status_code))
        request_id = data.get("request_id", data.get("requestId", ""))
        timestamp = data.get("timestamp", "")
        path = data.get("path", "")
        validation_errors = data.get("validation_errors", data.get("validationErrors", []))
        return cls(
            message=message,
            status_code=status_code,
            request_id=request_id,
            timestamp=timestamp,
            path=path,
            validation_errors=validation_errors,
        )
    
    def __str__(self) -> str:
        base = f"[{self.status_code}] {self.message}"
        if self.request_id:
            base += f" (request_id={self.request_id})"
        if self.validation_errors:
            base += f"\nValidation errors: {', '.join(self.validation_errors)}"
        return base
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code}, "
            f"request_id={self.request_id!r})"
        )
