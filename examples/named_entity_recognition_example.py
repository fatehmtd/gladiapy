
import time
from typing import Any

from gladiapy.v2 import GladiaRestClient, GladiaError
from gladiapy.v2.rest_models import TranscriptionRequest, NamedEntityRecognitionResult


def main() -> bool:
    import os
    print(f"Current working directory: {os.getcwd()}")
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
        named_entity_recognition = result.result.named_entity_recognition if result.result else None

        if named_entity_recognition is not None:
            _print_ner(named_entity_recognition)
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


def _print_ner(named_entity_recognition: NamedEntityRecognitionResult) -> None:
    # Try to handle the NamedEntityRecognitionResult model or plain dicts
    print("Named Entity Recognition result: ", named_entity_recognition.success, ", is empty: ", named_entity_recognition.is_empty)
    if(named_entity_recognition.success and named_entity_recognition.entity):
        entities = named_entity_recognition.entity
        if isinstance(entities, list):
            for _, entity in enumerate(entities):
                print("entity: ", entity)
        else:
            print("entity: ", entities)

    
if __name__ == "__main__":
    if not main():
        print("Named Entity Recognition example encountered issues.")