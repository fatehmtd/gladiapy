from __future__ import annotations
import os
import json
from typing import Optional
import requests
from .constants import headers as H, common as C
from .errors import GladiaError
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

    def upload(self, file_path: str) -> UploadResponse:
        """Upload audio file to Gladia storage.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            UploadResponse with audio_url for transcription
            
        Raises:
            GladiaError: If upload fails with API error details
            requests.RequestException: For network errors
        """
        url = _api_base_url() + C.UPLOAD_ENDPOINT
        with open(file_path, "rb") as f:
            files = {"audio": (os.path.basename(file_path), f, "application/octet-stream")}
            resp = self.session.post(url, files=files, timeout=120)
        if resp.status_code >= 400:
            raise GladiaError.from_response(resp, f"Upload failed for {file_path}")
        return UploadResponse.model_validate(resp.json())

    def pre_recorded(self, request: TranscriptionRequest) -> TranscriptionJobResponse:
        """Start batch transcription job.
        
        Args:
            request: TranscriptionRequest with audio_url and options
            
        Returns:
            TranscriptionJobResponse with job id for polling
            
        Raises:
            GladiaError: If transcription request fails with API error details
            requests.RequestException: For network errors
        """
        url = _api_base_url() + C.PRERECORDED_ENDPOINT
        resp = self.session.post(url, json=request.model_dump(by_alias=True, exclude_none=True))
        if resp.status_code >= 400:
            raise GladiaError.from_response(resp, "Transcription request failed")
        return TranscriptionJobResponse.model_validate(resp.json())

    def get_result(self, id: str) -> TranscriptionResult:
        """Get transcription job status and results.
        
        Args:
            id: Job ID from pre_recorded() call
            
        Returns:
            TranscriptionResult with status and transcription data
            
        Raises:
            GladiaError: If request fails with API error details
            requests.RequestException: For network errors
        """
        url = _api_base_url() + f"{C.PRERECORDED_ENDPOINT}/{id}"
        resp = self.session.get(url)
        if resp.status_code >= 400:
            raise GladiaError.from_response(resp, f"Failed to get result for job {id}")
        print(resp.json()) # Debug: print raw JSON response
        return TranscriptionResult.model_validate(resp.json())

    def get_results(self, query: ListResultsQuery) -> ListResultsPage:
        """List transcription jobs with pagination.
        
        Args:
            query: ListResultsQuery with offset/limit and filters
            
        Returns:
            ListResultsPage with jobs array and pagination info
            
        Raises:
            GladiaError: If request fails with API error details
            requests.RequestException: For network errors
        """
        url = _api_base_url() + C.PRERECORDED_ENDPOINT
        params = {k: v for k, v in query.model_dump(exclude_none=True).items() if v is not None and v != []}
        if "status" in params:
            params["status"] = ",".join(params["status"])  # API expects CSV
        resp = self.session.get(url, params=params)
        if resp.status_code >= 400:
            raise GladiaError.from_response(resp, "Failed to list results")
        return ListResultsPage.model_validate(resp.json())

    def delete_result(self, id: str) -> None:
        """Delete transcription job and results.
        
        Args:
            id: Job ID to delete
            
        Raises:
            GladiaError: If deletion fails with API error details
            requests.RequestException: For network errors
        """
        url = _api_base_url() + f"{C.PRERECORDED_ENDPOINT}/{id}"
        resp = self.session.delete(url)
        if resp.status_code >= 400:
            raise GladiaError.from_response(resp, f"Failed to delete job {id}")
        return None
