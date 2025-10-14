"""
Chapterization Example for GladiaPy
Demonstrates chapterization feature using GladiaPy client only.
"""
import os
import time
from typing import Any

from gladiapy.v2 import GladiaRestClient, GladiaError
from gladiapy.v2.rest_models import TranscriptionRequest


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
            chapterization=True,
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

        print("\n" + "-" * 40)
        print("Chapterization Analysis")
        print("-" * 40)

        # Prefer top-level chapterization if present; otherwise check nested
        chapters_obj = None
        rr = getattr(result.result, "chapterization", None)
        if rr is not None:
            chapters_obj = rr
        if chapters_obj is None and transcription is not None:
            chapters_obj = getattr(transcription, "chapterization", None)

        if chapters_obj is not None:
            _print_chapters(chapters_obj)
        else:
            print("No chapterization data available.")

        # Metadata
        if getattr(result.result, "metadata", None):
            meta = result.result.metadata
            print("\nMetadata")
            print("-" * 40)
            print(f"Audio duration: {getattr(meta, 'audio_duration', 0):.1f}s")
            print(f"Processing time: {getattr(meta, 'transcription_time', 0):.1f}s")
            print(f"Billing time: {getattr(meta, 'billing_time', 0):.1f}s")
        else:
            print("No chapterization data available.")

        # Minimal metadata
            if hasattr(result.result, "metadata") and result.result.metadata:
                meta = result.result.metadata
                print("\nMetadata")
            print("-" * 40)
            print(f"Audio duration: {getattr(meta, 'audio_duration', 0):.1f}s")
            print(f"Processing time: {getattr(meta, 'transcription_time', 0):.1f}s")
            print(f"Billing time: {getattr(meta, 'billing_time', 0):.1f}s")

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


def analyze_content_structure(text: str):
    """
    Simple content structure analysis for demonstration.
    """
    import re
    
    analysis = {}
    
    # Basic statistics
    # ...existing code...
    analysis['Total characters'] = len(text)
    analysis['Sentences'] = len([s for s in text.split('.') if s.strip()])
    
    # Look for repeated phrases (might indicate sections)
    words = text.lower().split()
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Find most common words (excluding common stop words)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'this', 'that'}
    common_words = [(word, count) for word, count in word_freq.items() 
                   if count > 1 and word not in stop_words and len(word) > 2]
    common_words.sort(key=lambda x: x[1], reverse=True)
    
    if common_words:
        analysis['Most repeated words'] = ', '.join([f"{word}({count})" for word, count in common_words[:5]])
    
    # Look for numbers (might indicate structure)
    numbers = re.findall(r'\b(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b', text.lower())
    if numbers:
        analysis['Numbers/counts found'] = ', '.join(set(numbers))
    
    return analysis


def _print_chapters(chapters_obj: Any) -> None:
    # Handle the ChapterizationResult model or plain structures
    payload = chapters_obj
    if hasattr(chapters_obj, "results"):
        payload = getattr(chapters_obj, "results")

    if isinstance(payload, dict):
        for k, v in payload.items():
            s = str(v)
            print(f"{k}: {s[:200]}{'...' if len(s) > 200 else ''}")
    elif isinstance(payload, (list, tuple)):
        for i, item in enumerate(payload, 1):
            s = str(item)
            print(f"{i}. {s[:200]}{'...' if len(s) > 200 else ''}")
    else:
        s = str(payload)
        print(s if len(s) <= 500 else s[:500] + "...")


if __name__ == "__main__":
    ok = main()
    print("\n" + "=" * 40)
    print("Chapterization example completed." if ok else "Chapterization example failed.")
    print("=" * 40)