import os
import time
from typing import Any

from gladiapy.v2 import GladiaRestClient, GladiaError
from gladiapy.v2.rest_models import TranscriptionRequest, SummarizationConfig


def main() -> bool:
    api_key = os.getenv("GLADIA_API_KEY")
    if not api_key:
        print("ERROR: Set GLADIA_API_KEY in environment")
        return False

    test_wav = os.path.abspath(os.path.join(os.path.dirname(__file__), "testing.wav"))
    if not os.path.exists(test_wav):
        print(f"ERROR: Audio file not found: {test_wav}")
        return False

    print("Summarization Example")
    print("=" * 40)

    client = GladiaRestClient(api_key)
    job_id: str | None = None
    try:
        print("Summarization Example\n======================")
        upload_result = client.upload(test_wav)
        print(f"Upload successful! Audio URL: {upload_result.audio_url}")
        request = TranscriptionRequest(audio_url=upload_result.audio_url, summarization=True)
        print("Starting transcription with summarization...")
        job = client.pre_recorded(request)
        job_id = job.id
        print(f"Job ID: {job_id}")
        # Poll for completion
        while True:
            result = client.get_result(job_id)
            print(f"Status: {result.status}")
            if result.status == "done":
                break
            if result.status == "error":
                print(f"Error: Job failed with error code {result.error_code}")
                return False
            time.sleep(4)
        if not result.result:
            print("Error: Missing result payload")
            return False
        # Prefer top-level summarization if present; otherwise check nested in transcription
        s = getattr(result.result, "summarization", None)
        if s is None:
            tr = getattr(result.result, "transcription", None)
            if tr is not None:
                s = getattr(tr, "summarization", None)
        print("\nSummary\n-------")
        if s and getattr(s, "results", None) is not None:
            _print_summary(s.results)
        else:
            print("No summarization data available in the response.")
        # Show minimal metadata
        meta = getattr(result.result, "metadata", None)
        if meta is not None:
            print(f"Audio duration: {getattr(meta, 'audio_duration', 0):.1f}s | Processing: {getattr(meta, 'transcription_time', 0):.1f}s | Billing: {getattr(meta, 'billing_time', 0):.1f}s")

        print("\n" + "-" * 40)
        print("Summary")
        print("-" * 40)
        if s and getattr(s, "results", None) is not None:
            _print_summary(s.results)
        else:
            print("No summarization data available in the response.")

        # Show minimal metadata
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
        if getattr(e, "validation_errors", None):
            print(f"Validation errors: {e.validation_errors}")
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


def _print_summary(results: Any) -> None:
    # Handle a few common structures defensively
    if isinstance(results, str):
        print(results)
        return
    if isinstance(results, (list, tuple)):
        for i, item in enumerate(results, 1):
            print(f"{i}. {item}")
        return
    if isinstance(results, dict):
        # Print a compact view for dict-like results
        for k, v in results.items():
            if isinstance(v, (str, int, float)):
                print(f"{k}: {v}")
            else:
                s = str(v)
                print(f"{k}: {s[:200]}{'...' if len(s) > 200 else ''}")
        return
    print(str(results))


if __name__ == "__main__":
    ok = main()
    print("\n" + "=" * 40)
    print("Summarization example completed." if ok else "Summarization example failed.")
    print("=" * 40)