import os
import time
from gladiapy.v2 import GladiaRestClient, GladiaError
from gladiapy.v2.rest_models import TranscriptionRequest, DiarizationConfig


def main():
    """
    Speaker Diarization example demonstrating speaker identification and separation.
    This example shows how to:
    1. Configure speaker diarization with different settings
    2. Identify who spoke when in multi-speaker audio
    3. Access speaker-specific utterances and timing
    4. Understand speaker separation and labeling
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

    print("SPEAKER DIARIZATION EXAMPLE")
    print("=" * 60)
    print("This example demonstrates speaker diarization capabilities:")
    print("- Automatic speaker detection and separation")
    print("- Speaker-specific utterance attribution")
    print("- Configurable number of speakers")
    print("- Enhanced diarization for better accuracy")
    print()

    try:
        client = GladiaRestClient(api_key)
        
        print(f"Uploading audio: {os.path.basename(test_wav)}")
        upload_result = client.upload(test_wav)
        print(f" Upload successful: {upload_result.audio_url}")

        # Configure diarization with different approaches
        diarization_config = DiarizationConfig(
                    min_speakers=1,  # Minimum 1 speaker
                    max_speakers=4,  # Maximum 4 speakers
                    enhanced=True
                )
        print(f"\nTesting diarization with: {diarization_config}")

        # Create transcription request with diarization enabled
        request = TranscriptionRequest(
            audio_url=upload_result.audio_url,
            diarization=True,
            diarization_config=diarization_config
        )

        print("\nStarting transcription with speaker diarization...")
        job = client.pre_recorded(request)
        print(f"Job ID: {job.id}")

        # Poll for completion
        print("Processing speaker diarization (this may take longer)...")
        while True:
            result = client.get_result(job.id)
            print(f"Status: {result.status}")
            
            if result.status == "done":
                break
            elif result.status == "error":
                print(f"ERROR: Job failed with error: {result.error_code}")
                return False
            
            time.sleep(4)  # Diarization takes longer

        print("\n" + "=" * 60)
        print("SPEAKER DIARIZATION RESULTS")
        print("=" * 60)

        if not (result.result and result.result.transcription):
            print("ERROR: No transcription results available")
            return False

        transcription = result.result.transcription
        
        # Show basic transcript info
        print(f"\nORIGINAL TRANSCRIPT:")
        print(f"Full text: \"{transcription.full_transcript}\"")
        print(f"Languages: {transcription.languages}")
        print(f"Total utterances: {len(transcription.utterances)}")

        # Analyze speaker information
        if transcription.utterances:
            print(f"\nSPEAKER ANALYSIS:")
            
            # Collect unique speakers
            speakers = set()
            speaker_utterances = {}
            
            for utterance in transcription.utterances:
                speaker_id = utterance.speaker
                speakers.add(speaker_id)
                
                # group utterances by speaker
                if speaker_id not in speaker_utterances:
                    speaker_utterances[speaker_id] = []
                speaker_utterances[speaker_id].append(utterance)
            
            print(f" Detected speakers: {len(speakers)}")
            print(f"Speaker IDs: {sorted(list(speakers)) if None not in speakers else 'Speaker identification may not be available'}")

            # Show detailed breakdown by speaker
            print(f"\nSPEAKER BREAKDOWN:")
            for speaker_id in sorted(speakers, key=lambda x: (x is None, x)):
                speaker_name = f"Speaker {speaker_id}" if speaker_id is not None else "Unknown Speaker"
                utterances = speaker_utterances[speaker_id]
                
                print(f"\n{speaker_name}:")
                print(f"  Total utterances: {len(utterances)}")
                
                # Calculate total speaking time
                total_duration = sum(utt.end - utt.start for utt in utterances)
                print(f"  Total speaking time: {total_duration:.1f}s")
                
                # Show first few utterances
                print(f"  Sample utterances:")
                for i, utt in enumerate(utterances[:3]):  # Show first 3
                    print(f"    {i+1}. [{utt.start:.2f}s-{utt.end:.2f}s] \"{utt.text}\"")
                    print(f"       Confidence: {utt.confidence:.2f}")
                
                if len(utterances) > 3:
                    print(f"    ... and {len(utterances) - 3} more utterances")

            # Show chronological speaker timeline
            print(f"\nCHRONOLOGICAL SPEAKER TIMELINE:")
            sorted_utterances = sorted(transcription.utterances, key=lambda x: x.start)
            
            for i, utt in enumerate(sorted_utterances):
                speaker_name = f"Speaker {utt.speaker}" if utt.speaker is not None else "Unknown"
                print(f"  {i+1:2d}. [{utt.start:5.2f}s-{utt.end:5.2f}s] {speaker_name:12s}: \"{utt.text[:50]}{'...' if len(utt.text) > 50 else ''}\"")

            # Analyze speaker transitions
            print(f"\nSPEAKER TRANSITION ANALYSIS:")
            transitions = 0
            current_speaker = None
            
            for utt in sorted_utterances:
                if current_speaker is not None and utt.speaker != current_speaker:
                    transitions += 1
                    print(f"  Transition {transitions}: Speaker {current_speaker} → Speaker {utt.speaker} at {utt.start:.2f}s")
                current_speaker = utt.speaker
            
            print(f"Total speaker transitions: {transitions}")

        else:
            print("No utterances found for speaker analysis")

        # Show processing metadata
        if result.result.metadata:
            meta = result.result.metadata
            print(f"\nPROCESSING METADATA:")
            print(f"  Audio duration: {meta.audio_duration:.1f}s")
            print(f"  Processing time: {meta.transcription_time:.1f}s")
            print(f"  Billing time: {meta.billing_time:.1f}s")
            print(f"  Audio channels: {meta.number_of_distinct_channels}")

        print("\n" + "=" * 60)

        # Clean up
        try:
            client.delete_result(job.id)
            print(f"\n Cleaned up job: {job.id}")
        except Exception as e:
            print(f"WARNING: Failed to delete job {job.id}: {e}")

        return True

    except GladiaError as e:
        print(f"\nGladia API Error: [{e.status_code}] {e.message}")
        if e.request_id:
            print(f"Request ID: {e.request_id}")
        return False
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    
    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: Speaker diarization example completed!")
        print("The diarization feature can identify and separate speakers")
        print("in multi-speaker audio with timing and attribution.")
    else:
        print("FAILED: Speaker diarization example encountered issues.")
        print("Check your API key, audio file, and feature availability.")
    print("=" * 60)