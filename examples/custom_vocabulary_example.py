import os
import time
from gladiapy.v2 import GladiaRestClient, GladiaError
from gladiapy.v2.rest_models import TranscriptionRequest, CustomSpellingConfig


def main():
    """
    Custom Vocabulary and Spelling example demonstrating domain-specific transcription enhancement.
    This example shows how to:
    1. Configure custom vocabulary for better recognition of specific terms
    2. Set up custom spelling corrections for consistent terminology
    3. Improve transcription accuracy for technical or specialized content
    4. Handle domain-specific jargon and proper nouns
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

    print("CUSTOM VOCABULARY & SPELLING EXAMPLE")
    print("=" * 60)
    print("This example demonstrates custom vocabulary and spelling capabilities:")
    print("- Custom vocabulary for domain-specific terms")
    print("- Spelling corrections and consistency enforcement")
    print("- Technical jargon and proper noun handling")
    print("- Before/after transcription comparison")
    print()

    try:
        client = GladiaRestClient(api_key)
        
        print(f"Uploading audio: {os.path.basename(test_wav)}")
        upload_result = client.upload(test_wav)
        print(f"✓ Upload successful: {upload_result.audio_url}")

        # First, do a baseline transcription without custom vocabulary
        print("\n--- BASELINE TRANSCRIPTION (No Custom Settings) ---")
        
        baseline_request = TranscriptionRequest(
            audio_url=upload_result.audio_url
        )
        
        print("Starting baseline transcription...")
        baseline_job = client.pre_recorded(baseline_request)
        
        # Wait for baseline completion
        while True:
            baseline_result = client.get_result(baseline_job.id)
            if baseline_result.status == "done":
                break
            elif baseline_result.status == "error":
                print(f"Baseline transcription failed: {baseline_result.error_code}")
                break
            time.sleep(2)
        
        baseline_transcript = ""
        if baseline_result.status == "done" and baseline_result.result and baseline_result.result.transcription:
            baseline_transcript = baseline_result.result.transcription.full_transcript
            print(f"Baseline result: \"{baseline_transcript}\"")
        
        # Clean up baseline job
        try:
            client.delete_result(baseline_job.id)
        except:
            pass

        # Now do enhanced transcription with custom vocabulary and spelling
        print(f"\n--- ENHANCED TRANSCRIPTION (With Custom Settings) ---")
        
        # Upload the audio file again for the enhanced transcription
        # (since the baseline job was cleaned up)
        enhanced_upload = client.upload(test_wav)
        print(f"Enhanced upload successful: {enhanced_upload.audio_url}")
        
        # Configure custom vocabulary for technical terms
        # Note: The exact vocabulary structure may need to be adjusted based on API requirements
        custom_vocabulary = [
            {
                "value": "testing",
                "intensity": 0.8,  # Higher intensity for better recognition
                "pronunciations": ["test-ing", "tes-ting"]
            },
            {
                "value": "one two three four",
                "intensity": 0.9,
                "pronunciations": ["one-two-three-four"]
            },
            {
                "value": "hello",
                "intensity": 0.7,
                "pronunciations": ["hel-lo", "hello"]
            }
        ]

        # Configure custom spelling corrections
        spelling_dictionary = {
            # Map variations to preferred spellings
            "helo": ["hello"],
            "teting": ["testing"], 
            "testin": ["testing"],
            "1 2 3 4": ["one two three four"],
            "wan": ["one"],
            "tu": ["two"],
            "tree": ["three"],
            "for": ["four"]
        }
        
        custom_spelling_config = CustomSpellingConfig(
            spelling_dictionary=spelling_dictionary
        )

        print("Custom vocabulary configured:")
        for vocab in custom_vocabulary:
            print(f"  - '{vocab['value']}' (intensity: {vocab['intensity']})")
        
        print(f"Custom spelling corrections: {len(spelling_dictionary)} rules")
        for original, corrections in spelling_dictionary.items():
            print(f"  - '{original}' → {corrections}")

        # Create enhanced transcription request
        enhanced_request = TranscriptionRequest(
            audio_url=enhanced_upload.audio_url,
            custom_vocabulary_config=custom_vocabulary,  # Custom vocabulary
            custom_spelling=True,
            custom_spelling_config=custom_spelling_config  # Custom spelling
        )

        print("\nStarting enhanced transcription with custom settings...")
        enhanced_job = client.pre_recorded(enhanced_request)
        print(f"Job ID: {enhanced_job.id}")

        # Poll for completion
        print("Processing enhanced transcription...")
        while True:
            result = client.get_result(enhanced_job.id)
            print(f"Status: {result.status}")
            
            if result.status == "done":
                break
            elif result.status == "error":
                print(f"ERROR: Job failed with error: {result.error_code}")
                return False
            
            time.sleep(3)

        print("\n" + "=" * 60)
        print("CUSTOM VOCABULARY & SPELLING RESULTS")
        print("=" * 60)

        if not (result.result and result.result.transcription):
            print("ERROR: No transcription results available")
            return False

        transcription = result.result.transcription
        enhanced_transcript = transcription.full_transcript
        
        # Compare baseline vs enhanced
        print(f"\nTRANSCRIPTION COMPARISON:")
        print(f"Baseline:  \"{baseline_transcript}\"")
        print(f"Enhanced:  \"{enhanced_transcript}\"")
        
        # Analyze improvements
        print(f"\nIMPROVEMENT ANALYSIS:")
        
        if baseline_transcript != enhanced_transcript:
            print("✓ Transcription was modified by custom settings")
            
            # Check for specific improvements
            improvements = []
            
            # Check if custom vocabulary terms are better recognized
            for vocab_item in custom_vocabulary:
                term = vocab_item['value']
                if term.lower() in enhanced_transcript.lower() and term.lower() not in baseline_transcript.lower():
                    improvements.append(f"Better recognition of '{term}'")
            
            # Check for spelling corrections
            for original, corrections in spelling_dictionary.items():
                for correction in corrections:
                    if correction.lower() in enhanced_transcript.lower() and original.lower() in baseline_transcript.lower():
                        improvements.append(f"Spelling correction: '{original}' → '{correction}'")
            
            if improvements:
                print("Detected improvements:")
                for improvement in improvements:
                    print(f"  - {improvement}")
            else:
                print("Transcription changed, but specific improvements not automatically detected")
                print("Manual review may be needed to assess quality improvements")
        
        else:
            print("ⓘ Transcription identical to baseline")
            print("This could mean:")
            print("  - The original transcription was already accurate")
            print("  - Custom settings didn't match the audio content")
            print("  - More specific vocabulary terms may be needed")

        # Show detailed utterance information
        print(f"\nDETAILED TRANSCRIPTION INFO:")
        print(f"Languages: {transcription.languages}")
        print(f"Total utterances: {len(transcription.utterances)}")
        
        if transcription.utterances:
            for i, utterance in enumerate(transcription.utterances):
                print(f"\nUtterance {i+1}: [{utterance.start:.2f}s-{utterance.end:.2f}s]")
                print(f"  Text: \"{utterance.text}\"")
                print(f"  Confidence: {utterance.confidence:.2f}")
                
                # Show word-level details
                if utterance.words:
                    print(f"  Words ({len(utterance.words)} total):")
                    for j, word in enumerate(utterance.words[:8]):  # Show first 8 words
                        print(f"    {j+1}. '{word.word}' [{word.start:.2f}s-{word.end:.2f}s] conf: {word.confidence:.2f}")
                    
                    if len(utterance.words) > 8:
                        print(f"    ... and {len(utterance.words) - 8} more words")

        # Show processing metadata
        if result.result.metadata:
            meta = result.result.metadata
            print(f"\nPROCESSING METADATA:")
            print(f"  Audio duration: {meta.audio_duration:.1f}s")
            print(f"  Processing time: {meta.transcription_time:.1f}s")
            print(f"  Billing time: {meta.billing_time:.1f}s")

        print("\n" + "=" * 60)
        print("CUSTOM VOCABULARY & SPELLING BEST PRACTICES:")
        print("1. Use domain-specific terms relevant to your audio content")
        print("2. Set appropriate intensity levels (0.5-1.0) for vocabulary items")
        print("3. Include common mispronunciations in spelling corrections")
        print("4. Test with and without custom settings to measure improvement")
        print("5. Regularly update vocabulary based on transcription results")
        
        print(f"\nCONFIGURATION SUMMARY:")
        print(f"  Custom vocabulary items: {len(custom_vocabulary)}")
        print(f"  Spelling correction rules: {len(spelling_dictionary)}")
        print(f"  Custom spelling enabled: {enhanced_request.custom_spelling}")

        # Clean up
        try:
            client.delete_result(enhanced_job.id)
            print(f"\n✓ Cleaned up job: {enhanced_job.id}")
        except Exception as e:
            print(f"WARNING: Failed to delete job {enhanced_job.id}: {e}")

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
        print("SUCCESS: Custom vocabulary & spelling example completed!")
        print("These features can significantly improve transcription accuracy")
        print("for domain-specific, technical, or specialized content.")
    else:
        print("FAILED: Custom vocabulary & spelling example encountered issues.")
        print("Check your API key, audio file, and feature availability.")
    print("=" * 60)