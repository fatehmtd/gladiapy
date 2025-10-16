import os
import time

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

    print("Sentiment Analysis Example")
    print("=" * 40)

    client = GladiaRestClient(api_key)
    job_id: str | None = None
    try:
        print(f"Uploading audio: {os.path.basename(test_wav)}")
        upload_result = client.upload(test_wav)
        print(f"Upload URL: {upload_result.audio_url}")

        request = TranscriptionRequest(
            audio_url=upload_result.audio_url,
            sentiment_analysis=True,
        )
        print("Starting transcription with sentiment analysis...")
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
            time.sleep(3)

        if not (result.result and result.result.transcription):
            print("Error: No transcription results available")
            return False

        print("\n" + "-" * 40)
        print("Analysis")
        print("-" * 40)

        # print sentiment analysis
        sentiment_analysis = result.result.sentiment_analysis
        if sentiment_analysis is not None and sentiment_analysis.success:
            print("Sentiment Analysis Result")
            if sentiment_analysis.results:
                for entry in sentiment_analysis.results:
                    print(f"text: {entry.text}, sentiment: {entry.sentiment}, start: {entry.start:.2f}, end: {entry.end:.2f}, channel: {entry.channel}")
        else:
            print("No sentiment analysis data available.")                    

        # Minimal metadata
        if result.result.metadata:
            meta = result.result.metadata
            print("\nMetadata")
            print("-" * 40)
            print(f"Audio duration: {meta.audio_duration:.1f}s")
            print(f"Processing time: {meta.transcription_time:.1f}s")
            print(f"Billing time: {meta.billing_time:.1f}s")

        print("\n" + "=" * 40)
        print("Configuration:")
        print(f"  Feature enabled: {request.sentiment_analysis}")
        print("  Analysis scope: Utterance and word-level sentiment detection")
        print("  Output format: Sentiment scores and classifications")

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

if __name__ == "__main__":
    ok = main()
    print("\n" + "=" * 40)
    print("Sentiment analysis example completed." if ok else "Sentiment analysis example failed.")
    print("=" * 40)