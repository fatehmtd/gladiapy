import os
import time
from gladiapp.v2 import GladiaRestClient
from gladiapp.v2.rest_models import TranscriptionRequest, ListResultsQuery


def main():
    """
    REST API example that demonstrates audio transcription using the REST endpoint.
    This example shows how to:
    1. Upload an audio file to Gladia
    2. Start a transcription job
    3. Poll for completion
    4. Retrieve detailed transcription results with word-level timing
    5. Manage and clean up transcription jobs
    """
    api_key = os.getenv("GLADIA_API_KEY") or os.getenv("GLADIA_KEY")
    if not api_key:
        print("ERROR: Set GLADIA_API_KEY in environment or .env")
        print("   You can get an API key from: https://gladia.io")
        return False

    # Use the testing.wav file in the examples directory
    test_wav = os.path.join(os.path.dirname(__file__), "testing.wav")
    test_wav = os.path.abspath(test_wav)
    print(f"Loading audio file: {test_wav}")
    
    if not os.path.exists(test_wav):
        print(f"ERROR: Audio file not found: {test_wav}")
        return False
    
    try:
        client = GladiaRestClient(api_key)
        upload_result = client.upload(test_wav)
        print(f"SUCCESS: Upload successful! Audio URL: {upload_result.audio_url}")
    except Exception as e:
        print(f"ERROR: Upload failed: {e}")
        return False

    # Create transcription request with basic settings
    req = TranscriptionRequest(audio_url=upload_result.audio_url)

    print("Starting transcription job...")
    job = client.preRecorded(req)
    print(f"Job ID: {job.id}")

    # Wait for completion
    status = ""
    while status not in ("done", "error"):
        result = client.getResult(job.id)
        status = result.status
        print(f"Status: {status}")
        
        if status == "done":
            break
        elif status == "error":
            print(f"ERROR: Job failed with error: {result.error_code}")
            return False
            
        time.sleep(3)

    # Get final result
    final_result = client.getResult(job.id)
    
    if final_result.status == "done" and final_result.result and final_result.result.transcription:
        print("\nREST TRANSCRIPTION COMPLETED!")
        print("=" * 50)
        
        trans = final_result.result.transcription
        print(f"Full Transcript: \"{trans.full_transcript}\"")
        print(f"Languages: {trans.languages}")
        print(f"Utterances: {len(trans.utterances)}")
        
        # Show first utterance details
        if trans.utterances:
            utterance = trans.utterances[0]
            print(f"\nFirst Utterance:")
            print(f"   Text: \"{utterance.text}\"")
            print(f"   Time: {utterance.start:.2f}s - {utterance.end:.2f}s")
            print(f"   Confidence: {utterance.confidence:.2f}")
            
            # Show first few words
            if utterance.words:
                print(f"   First 3 words:")
                for i, word in enumerate(utterance.words[:3]):
                    print(f"     {i+1}. \"{word.word.strip()}\" [{word.start:.2f}s-{word.end:.2f}s] conf: {word.confidence:.2f}")
        
        # Show metadata
        if final_result.result.metadata:
            meta = final_result.result.metadata
            print(f"\nMetadata:")
            print(f"   Audio duration: {meta.audio_duration:.1f}s")
            print(f"   Processing time: {meta.transcription_time:.1f}s")
            print(f"   Billing time: {meta.billing_time:.1f}s")
        
        print("=" * 50)
    else:
        print(f"ERROR: Transcription failed or no result available")
        return False

    # List recent results
    print("\nListing recent results...")
    try:
        page = client.getResults(ListResultsQuery(offset=0, limit=5))
        print(f"Found {len(page.items)} recent results")
        
        for i, item in enumerate(page.items[:3]):  # Show first 3
            print(f"  {i+1}. ID: {item.id} | Status: {item.status} | Created: {item.created_at}")
    except Exception as e:
        print(f"ERROR: Failed to list results: {e}")

    # Clean up - delete the job we just created
    try:
        client.deleteResult(job.id)
        print(f"Cleaned up job: {job.id}")
    except Exception as e:
        print(f"WARNING: Failed to delete job {job.id}: {e}")
    
    return True


if __name__ == "__main__":
    print("REST API TRANSCRIPTION EXAMPLE")
    print("=" * 50)
    print("This example demonstrates REST-based audio transcription.")
    print("The REST API allows you to upload audio files and receive")  
    print("detailed transcriptions with word-level timing and confidence scores.\n")
    
    success = main()
    
    print("\n" + "=" * 50)
    if success:
        print("SUCCESS: REST example completed successfully!")
        print("The REST API is working properly and can transcribe audio")
        print("files with detailed word-level timing and metadata.")
    else:
        print("FAILED: REST example encountered issues.")
        print("This may be due to network connectivity, file issues, or API configuration.")
        print("Please check your API key and audio file, then try again.")
    print("=" * 50)