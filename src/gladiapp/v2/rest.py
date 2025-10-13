from __future__ import annotations
import os
import json
from typing import Optional
import requests
from .constants import headers as H, common as C
from .errors import TranscriptionError
from .rest_models import (
    UploadResponse,
    TranscriptionRequest,
    TranscriptionJobResponse,
    TranscriptionResult,
    ListResultsPage,
    ListResultsQuery,
)

def _api_base_url() -> str:
    return f"https://{C.HOST}"


class GladiaRestClient:
    """Client for Gladia REST API batch transcription jobs."""
    
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("API key is required")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": C.USER_AGENT,
            H.X_GLADIA_KEY: self.api_key,
        })

    def upload(self, file_path: str, transcription_error: Optional[TranscriptionError] = None) -> UploadResponse:
        """Upload audio file to Gladia storage.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            UploadResponse with audio_url for transcription
        """
        url = _api_base_url() + C.UPLOAD_ENDPOINT
        with open(file_path, "rb") as f:
            files = {"audio": (os.path.basename(file_path), f, "application/octet-stream")}
            resp = self.session.post(url, files=files, timeout=120)
        if resp.status_code >= 400:
            if transcription_error is not None:
                try:
                    data = resp.json()
                except Exception:
                    data = {"status": resp.status_code, "message": resp.text}
                te = TranscriptionError.from_json(data)
                transcription_error.timestamp = getattr(te, "timestamp", "")
                transcription_error.path = getattr(te, "path", "")
                transcription_error.request_id = te.request_id
                transcription_error.status_code = te.status_code
                transcription_error.message = te.message
                transcription_error.validation_errors = te.validation_errors
            resp.raise_for_status()
        return UploadResponse.model_validate(resp.json())

    def pre_recorded(self, request: TranscriptionRequest, transcription_error: Optional[TranscriptionError] = None) -> TranscriptionJobResponse:
        """Start batch transcription job.
        
        Args:
            request: TranscriptionRequest with audio_url and options
            
        Returns:
            TranscriptionJobResponse with job id for polling
        """
        url = _api_base_url() + C.PRERECORDED_ENDPOINT
        resp = self.session.post(url, json=request.model_dump(by_alias=True, exclude_none=True))
        if resp.status_code >= 400:
            if transcription_error is not None:
                try:
                    data = resp.json()
                except Exception:
                    data = {"status": resp.status_code, "message": resp.text}
                te = TranscriptionError.from_json(data)
                transcription_error.timestamp = getattr(te, "timestamp", "")
                transcription_error.path = getattr(te, "path", "")
                transcription_error.request_id = te.request_id
                transcription_error.status_code = te.status_code
                transcription_error.message = te.message
                transcription_error.validation_errors = te.validation_errors
            resp.raise_for_status()
        return TranscriptionJobResponse.model_validate(resp.json())

    def get_result(self, id: str, transcription_error: Optional[TranscriptionError] = None) -> TranscriptionResult:
        """Get transcription job status and results.
        
        Args:
            id: Job ID from pre_recorded() call
            
        Returns:
            TranscriptionResult with status and transcription data
        """
        url = _api_base_url() + f"{C.PRERECORDED_ENDPOINT}/{id}"
        resp = self.session.get(url)
        if resp.status_code >= 400:
            if transcription_error is not None:
                try:
                    data = resp.json()
                except Exception:
                    data = {"status": resp.status_code, "message": resp.text}
                te = TranscriptionError.from_json(data)
                transcription_error.timestamp = getattr(te, "timestamp", "")
                transcription_error.path = getattr(te, "path", "")
                transcription_error.request_id = te.request_id
                transcription_error.status_code = te.status_code
                transcription_error.message = te.message
                transcription_error.validation_errors = te.validation_errors
            resp.raise_for_status()
        return TranscriptionResult.model_validate(resp.json())

    def get_results(self, query: ListResultsQuery, transcription_error: Optional[TranscriptionError] = None) -> ListResultsPage:
        """List transcription jobs with pagination.
        
        Args:
            query: ListResultsQuery with offset/limit and filters
            
        Returns:
            ListResultsPage with jobs array and pagination info
        """
        url = _api_base_url() + C.PRERECORDED_ENDPOINT
        params = {k: v for k, v in query.model_dump(exclude_none=True).items() if v is not None and v != []}
        if "status" in params:
            params["status"] = ",".join(params["status"])  # API expects CSV
        resp = self.session.get(url, params=params)
        if resp.status_code >= 400:
            if transcription_error is not None:
                try:
                    data = resp.json()
                except Exception:
                    data = {"status": resp.status_code, "message": resp.text}
                te = TranscriptionError.from_json(data)
                transcription_error.timestamp = getattr(te, "timestamp", "")
                transcription_error.path = getattr(te, "path", "")
                transcription_error.request_id = te.request_id
                transcription_error.status_code = te.status_code
                transcription_error.message = te.message
                transcription_error.validation_errors = te.validation_errors
            resp.raise_for_status()
        return ListResultsPage.model_validate(resp.json())

    def delete_result(self, id: str, transcription_error: Optional[TranscriptionError] = None) -> None:
        """Delete transcription job and results.
        
        Args:
            id: Job ID to delete
        """
        url = _api_base_url() + f"{C.PRERECORDED_ENDPOINT}/{id}"
        resp = self.session.delete(url)
        if resp.status_code >= 400:
            if transcription_error is not None:
                try:
                    data = resp.json()
                except Exception:
                    data = {"status": resp.status_code, "message": resp.text}
                te = TranscriptionError.from_json(data)
                transcription_error.timestamp = getattr(te, "timestamp", "")
                transcription_error.path = getattr(te, "path", "")
                transcription_error.request_id = te.request_id
                transcription_error.status_code = te.status_code
                transcription_error.message = te.message
                transcription_error.validation_errors = te.validation_errors
        resp.raise_for_status()
        return None
