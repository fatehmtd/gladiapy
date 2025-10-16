import os
import time
from typing import Any

from gladiapy.v2 import GladiaRestClient, GladiaError
from gladiapy.v2.rest_models import TranscriptionRequest, SummarizationConfig, SummarizationResult


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
        
        # get summarization results
        summarization = result.result.summarization
        
        if summarization is not None and summarization.success:
            print("\nSummary\n-------")
            print(summarization.results)
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


if __name__ == "__main__":
    ok = main()
    print("\n" + "=" * 40)
    print("Summarization example completed." if ok else "Summarization example failed.")
    print("=" * 40)