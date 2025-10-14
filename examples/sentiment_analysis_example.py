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

        transcription = result.result.transcription

        print("\n" + "-" * 40)
        print("Analysis")
        print("-" * 40)

        # Prefer top-level sentiment if present
        rr = result.result
        if rr is not None:
            sentiment_obj = getattr(rr, "sentiment_analysis", None)
            if sentiment_obj is not None:
                print(str(sentiment_obj))

        # Utterance-level scan for any sentiment attributes
        if transcription.utterances:
            for i, utterance in enumerate(transcription.utterances[:3], 1):
                attrs = [a for a in dir(utterance) if not a.startswith("_") and "sentiment" in a.lower()]
                if attrs:
                    print(f"Utterance {i} sentiment attributes: {attrs}")
                    for a in attrs:
                        try:
                            v = getattr(utterance, a)
                            print(f"  {a}: {v}")
                        except Exception:
                            pass

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

        print("Sentiment Analysis Example\n==========================")
        client = GladiaRestClient(api_key)
        try:
            upload_result = client.upload(test_wav)
            print(f"Upload successful! Audio URL: {upload_result.audio_url}")
            request = TranscriptionRequest(audio_url=upload_result.audio_url, sentiment_analysis=True)
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
            print("Sentiment Analysis Result:")
            sentiment = getattr(result.result, "sentiment_analysis", None)
            if sentiment is not None:
                print(sentiment)
            else:
                print("No sentiment analysis results available.")
            meta = getattr(result.result, "metadata", None)
            if meta is not None:
                print(f"Audio duration: {getattr(meta, 'audio_duration', 0):.1f}s | Processing: {getattr(meta, 'transcription_time', 0):.1f}s | Billing: {getattr(meta, 'billing_time', 0):.1f}s")
            client.delete_result(job_id)
            print(f"Job cleaned up: {job_id}")
            print("Sentiment analysis example completed.")
            return True
        except GladiaError as e:
            print(f"API Error: [{e.status_code}] {e.message}")
            if getattr(e, "request_id", None):
                print(f"Request ID: {e.request_id}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

if __name__ == "__main__":
    ok = main()
    print("\n" + "=" * 40)
    print("Sentiment analysis example completed." if ok else "Sentiment analysis example failed.")
    print("=" * 40)