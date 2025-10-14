
import os
import time
import requests
import json
from typing import Any

from gladiapy.v2 import GladiaRestClient, GladiaError
from gladiapy.v2.rest_models import TranscriptionRequest


def main() -> bool:
    import os
    print(f"Current working directory: {os.getcwd()}")
    print(f"About to fetch raw API response for job_id: {job_id}")
    api_key = os.getenv("GLADIA_API_KEY")
    if not api_key:
        print("ERROR: Set GLADIA_API_KEY in environment")
        return False

    test_wav = os.path.abspath(os.path.join(os.path.dirname(__file__), "testing.wav"))
    if not os.path.exists(test_wav):
        print(f"ERROR: Audio file not found: {test_wav}")
        return False

    print("Named Entity Recognition Example")
    print("=" * 40)

    client = GladiaRestClient(api_key)
    job_id: str | None = None
    try:
        print(f"Uploading audio: {os.path.basename(test_wav)}")
        try:
            upload_result = client.upload(test_wav)
            print(f"Upload URL: {upload_result.audio_url}")
        except Exception as e:
            print(f"ERROR during upload: {e}")
            return False

        try:
            request = TranscriptionRequest(
                audio_url=upload_result.audio_url,
                named_entity_recognition=True,
            )
            print("Starting transcription with NER...")
            job = client.pre_recorded(request)
            job_id = job.id
            print(f"Job ID: {job_id}")
        except Exception as e:
            print(f"ERROR during job creation: {e}")
            return False

        # Poll for completion
        result = None
        try:
            while True:
                print("Polling for job status...")
                result = client.get_result(job_id)
                print(f"Status: {result.status}")
                if result.status == "done":
                    break
                if result.status == "error":
                    print(f"Error: Job failed with error code {result.error_code}")
                    return False
                time.sleep(3)
        except Exception as e:
            print(f"ERROR during polling: {e}")
            return False

        print("\nNamed Entity Recognition Result (GladiaPy):")
        ner = getattr(result.result, "named_entity_recognition", None)
        if ner is not None:
            print(ner)
        else:
            print("No named entity recognition results available.")

        if not (result.result and result.result.transcription):
            print("Error: No transcription results available")
            return False

        transcription = result.result.transcription

        print("\n" + "-" * 40)
        print("Entity Analysis")
        print("-" * 40)

        # Prefer top-level NER results if present; otherwise check nested
        ner_obj = None
        rr = result.result
        if rr is not None:
            ner_obj = getattr(rr, "named_entity_recognition", None)
        if ner_obj is None and transcription is not None:
            ner_obj = getattr(transcription, "named_entity_recognition", None)

        if ner_obj is not None:
            _print_ner(ner_obj)
        else:
            print("No named entity recognition data available in the response.")

        # Show a short utterance scan for any entity-like attributes
        if transcription.utterances:
            u = transcription.utterances[0]
            attrs = [a for a in dir(u) if not a.startswith("_") and ("entit" in a.lower() or "ner" in a.lower())]
            if attrs:
                print("\nUtterance attributes containing entity-related data:")
                for a in attrs:
                    try:
                        v = getattr(u, a)
                        print(f"  {a}: {v}")
                    except Exception:
                        print(f"  {a}: <unavailable>")

        # Minimal metadata
        if result.result.metadata:
            meta = result.result.metadata
            print("\nMetadata")
            print("-" * 40)
            print(f"Audio duration: {meta.audio_duration:.1f}s")
            print(f"Processing time: {meta.transcription_time:.1f}s")
            print(f"Billing time: {meta.billing_time:.1f}s")

        return True
    except GladiaError as e:
        print(f"API Error: [{e.status_code}] {e.message}")
        if getattr(e, "request_id", None):
            print(f"Request ID: {e.request_id}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    finally:
        if job_id:
            try:
                client.delete_result(job_id)
                print(f"Cleaned up job: {job_id}")
            except Exception:
                pass


def _print_ner(ner_obj: Any) -> None:
    # Try to handle the NamedEntityRecognitionResult model or plain dicts
    container = None
    if hasattr(ner_obj, "entity"):
        container = getattr(ner_obj, "entity")
    else:
        container = ner_obj

    if isinstance(container, dict):
        for k, v in container.items():
            if isinstance(v, list):
                print(f"{k}:")
                for item in v:
                    print(f"  {item}")
    
