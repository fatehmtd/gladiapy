"""
Chapterization Example for GladiaPy
Demonstrates chapterization feature using GladiaPy client only.
"""
import os
import time
from typing import Any

from gladiapy.v2 import GladiaRestClient, GladiaError
from gladiapy.v2.rest_models import TranscriptionRequest, ChapterizationResult


def main() -> bool:
    api_key = os.getenv("GLADIA_API_KEY")
    if not api_key:
        print("ERROR: Set GLADIA_API_KEY in environment")
        return False

    test_wav = os.path.abspath(os.path.join(os.path.dirname(__file__), "testing.wav"))
    if not os.path.exists(test_wav):
        print(f"ERROR: Audio file not found: {test_wav}")
        return False

    print("Chapterization Example")
    print("=" * 40)

    client = GladiaRestClient(api_key)
    job_id: str | None = None
    try:
        print(f"Uploading audio: {os.path.basename(test_wav)}")
        upload_result = client.upload(test_wav)
        print(f"Upload URL: {upload_result.audio_url}")

        request = TranscriptionRequest(
            audio_url=upload_result.audio_url,
            chapterization=True,  # Enable chapterization
        )
        print("Starting transcription with chapterization...")
        job = client.pre_recorded(request)
        job_id = job.id
        print(f"Job ID: {job_id}")

        # Poll for completion using gladiapy client
        result = None
        while True:
            result = client.get_result(job_id)
            print(f"Status: {result.status}")
            if result.status == "done":
                break
            if result.status == "error":
                print(f"Error: Job failed with error code {result.error_code}")
                return False
            time.sleep(3)

        # Print result summary
        print("\nChapterization Result (GladiaPy):")
        print(result)

        if not (result.result and result.result.transcription):
            print("Error: No transcription results available")
            return False

        transcription = result.result.transcription

        # Print full transcript
        print("\nFull Transcript")
        print("-" * 40)
        print(transcription.full_transcript)

        print("\n" + "-" * 40)
        print("Chapterization Analysis")
        print("-" * 40)

        # retrieve chapters
        chapterization_result = result.result.chapterization       

        if chapterization_result is not None:
            print_chapters(chapterization_result)
        else:
            print("No chapterization data available.")

        # Metadata
        meta = result.result.metadata
        if meta is not None:
            print("\nMetadata")
            print("-" * 40)
            print(f"Audio duration: {meta.audio_duration:.1f}s")
            print(f"Processing time: {meta.transcription_time:.1f}s")
            print(f"Billing time: {meta.billing_time:.1f}s")
        else:
            print("No chapterization data available.")

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


def print_chapters(chapterization_result: ChapterizationResult) -> None:
    # Handle the ChapterizationResult model or plain structures
    print("Chapterization result: ", chapterization_result.success, ", is empty: ", chapterization_result.is_empty)
    if(chapterization_result.success and chapterization_result.results):
        for _, chapter in enumerate(chapterization_result.results):
            print("chapter: ", chapter)
            


if __name__ == "__main__":
    ok = main()
    print("\n" + "=" * 40)
    print("Chapterization example completed." if ok else "Chapterization example failed.")
    print("=" * 40)