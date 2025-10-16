import os
import time
from gladiapy.v2 import GladiaRestClient, GladiaError
from gladiapy.v2.rest_models import TranscriptionRequest, TranslationConfig


def main():
    """
    Translation example demonstrating multilingual translation capabilities.
    This example shows how to:
    1. Configure translation for multiple target languages
    2. Enable context adaptation and lipsync features
    3. Access translated utterances with timing preservation
    4. Compare original and translated text
    """
    api_key = os.getenv("GLADIA_API_KEY")
    if not api_key:
        print("ERROR: Set GLADIA_API_KEY in environment")
        return False

    test_wav = os.path.join(os.path.dirname(__file__), "testing.wav")
    test_wav = os.path.abspath(test_wav)
    
    if not os.path.exists(test_wav):
        print(f"ERROR: Audio file not found: {test_wav}")
        return False

    print("Translation Example")
    print("=" * 40)

    try:
        client = GladiaRestClient(api_key)
        print(f"Uploading audio: {os.path.basename(test_wav)}")
        upload_result = client.upload(test_wav)
        print(f"Upload successful: {upload_result.audio_url}")

        translation_config = TranslationConfig(
            model="base",
            target_languages=["fr", "es", "de"],
        )
        request = TranscriptionRequest(
            audio_url=upload_result.audio_url,
            translation=True,
            translation_config=translation_config
        )
        print("Request payload:")
        print(request.model_dump(by_alias=True, exclude_none=True))
        print("Starting transcription with translation...")
        job = client.pre_recorded(request)
        print(f"Job ID: {job.id}")
        print("Processing...")
        while True:
            result = client.get_result(job.id)
            print(f"Status: {result.status}")
            if result.status == "done":
                break
            elif result.status == "error":
                print(f"Error: Job failed with error: {result.error_code}")
                return False
            time.sleep(5)

        print("\n" + "=" * 40)
        print("Translation Results")
        print("=" * 40)
        if not (result.result and result.result.transcription):
            print("Error: No transcription results available")
            return False
        transcription = result.result.transcription
        print("Original transcript:")
        print(f"Language: {transcription.languages}")
        print(f"Text: {transcription.full_transcript}")
        if not transcription.utterances:
            print("No utterances found")
            return False
        print("Original utterances:")
        for i, utterance in enumerate(transcription.utterances):
            print(f"  {i+1}. [{utterance.start:.2f}s-{utterance.end:.2f}s] {utterance.text}      Language: {utterance.language}, Confidence: {utterance.confidence}")
            
        print("Translation status:")
        # get translation data
        translation_data = result.result.translation
        if translation_data is None or not translation_data.results:
            print("No translation data available")
            return False
        else:
            for translation_result in translation_data.results:
                print(f"  {translation_result.languages}:")
                print(f"    Full text: {translation_result.full_transcript}")
                if translation_result.utterances:
                    print(f"    Utterances ({len(translation_result.utterances)} total):")
                    for j, trans_utterance in enumerate(translation_result.utterances):
                        print(f"      {j+1}. [{trans_utterance.start:.2f}s-{trans_utterance.end:.2f}s] {trans_utterance.text}, confidence: {trans_utterance.confidence}")
                else:
                    print("    No utterances found")

        if result.result.metadata:
            meta = result.result.metadata
            print("Processing metadata:")
            print(f"  Audio duration: {meta.audio_duration:.1f}s")
            print(f"  Processing time: {meta.transcription_time:.1f}s")
            print(f"  Billing time: {meta.billing_time:.1f}s")

        print("\n" + "=" * 40)
        print("Translation configuration:")
        print(f"  Model: {translation_config.model}")
        print(f"  Target languages: {', '.join(translation_config.target_languages)}")
        print(f"  Context adaptation: {translation_config.context_adaptation}")
        print(f"  Lipsync: {translation_config.lipsync}")
        print(f"  Match original timing: {translation_config.match_original_utterances}")
        print(f"  Style: {'Formal' if not translation_config.informal else 'Informal'}")
        try:
            client.delete_result(job.id)
            print(f"Cleaned up job: {job.id}")
        except Exception as e:
            print(f"Warning: Failed to delete job {job.id}: {e}")
        return True
    except GladiaError as e:
        print(f"API Error: [{e.status_code}] {e.message}")
        if e.request_id:
            print(f"Request ID: {e.request_id}")
        if hasattr(e, 'validation_errors'):
            print(f"Validation errors: {e.validation_errors}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    
    print("\n" + "=" * 40)
    if success:
        print("Translation example completed.")
        sys.exit(0)
    else:
        print("Translation example failed.")
        sys.exit(1)