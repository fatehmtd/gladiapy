import os
import time
from gladiapy.v2 import GladiaRestClient, GladiaError
from gladiapy.v2.rest_models import TranscriptionRequest, SubtitlesConfig


def main():
    """
    Subtitles Generation example demonstrating SRT/VTT subtitle creation.
    This example shows how to:
    1. Configure subtitle generation with different formats (SRT, VTT)
    2. Control subtitle formatting (characters per row, rows per caption)
    3. Access generated subtitle content with proper timing
    4. Export subtitles for video integration
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

    print("SUBTITLES GENERATION EXAMPLE")
    print("=" * 60)
    print("This example demonstrates subtitle generation capabilities:")
    print("- SRT and VTT subtitle format generation")
    print("- Configurable text formatting and timing")
    print("- Multiple style options for different use cases")
    print("- Ready-to-use subtitle files for video integration")
    print()

    try:
        client = GladiaRestClient(api_key)
        
        print(f"Uploading audio: {os.path.basename(test_wav)}")
        upload_result = client.upload(test_wav)
        print(f" Upload successful: {upload_result.audio_url}")

        # Configure subtitles with basic settings
        # Create transcription request with subtitles enabled (basic)
        request = TranscriptionRequest(
            audio_url=upload_result.audio_url,
            subtitles=True  # Enable subtitles with default settings
        )

        print("\nStarting transcription with subtitle generation...")
        job = client.pre_recorded(request)
        print(f"Job ID: {job.id}")

        # Poll for completion
        print("Processing subtitle generation...")
        while True:
            result = client.get_result(job.id)
            print(f"Status: {result.status}")
            
            if result.status == "done":
                break
            elif result.status == "error":
                print(f"ERROR: Job failed with error: {result.error_code}")
                return False
            
            time.sleep(3)

        print("\n" + "=" * 60)
        print("SUBTITLE GENERATION RESULTS")
        print("=" * 60)

        if not (result.result and result.result.transcription):
            print("ERROR: No transcription results available")
            return False

        transcription = result.result.transcription
        
        # Show basic transcript info
        print(f"\nORIGINAL TRANSCRIPT:")
        print(f"Text: \"{transcription.full_transcript}\"")
        print(f"Languages: {transcription.languages}")
        print(f"Total utterances: {len(transcription.utterances)}")

        # Access subtitle data
        if transcription.subtitles:
            print(f"\nSUBTITLE FILES GENERATED:")
            print(f" Generated {len(transcription.subtitles)} subtitle format(s)")
            
            for i, subtitle in enumerate(transcription.subtitles):
                print(f"\n--- SUBTITLE FORMAT {i+1}: {subtitle.format.upper()} ---")
                print(f"Format: {subtitle.format}")
                print(f"Content length: {len(subtitle.subtitles)} characters")
                
                # Show subtitle content preview
                print(f"\nSubtitle content preview:")
                print("-" * 40)
                
                # Show first 1000 characters of subtitle content
                preview_content = subtitle.subtitles[:1000]
                print(preview_content)
                
                if len(subtitle.subtitles) > 1000:
                    print(f"... (showing first 1000 of {len(subtitle.subtitles)} characters)")
                
                print("-" * 40)
                
                # Save subtitle to file for practical use
                subtitle_filename = f"transcript_example.{subtitle.format}"
                subtitle_path = os.path.join(os.path.dirname(__file__), subtitle_filename)
                
                try:
                    with open(subtitle_path, 'w', encoding='utf-8') as f:
                        f.write(subtitle.subtitles)
                    print(f" Saved subtitle file: {subtitle_filename}")
                    print(f"  Full path: {subtitle_path}")
                except Exception as e:
                    print(f"⚠ Failed to save subtitle file: {e}")

        else:
            print("\n⚠ No subtitle data found in results")
            print("This could mean:")
            print("1. Subtitle generation is not enabled for your API key")
            print("2. The audio content was too short for subtitle generation")
            print("3. Subtitle data is structured differently than expected")
            
            # Debug: show what's available in transcription
            print(f"\nAvailable transcription attributes:")
            transcription_attrs = [attr for attr in dir(transcription) if not attr.startswith('_')]
            print(f"  {transcription_attrs}")

        # Show utterance timing for manual subtitle creation reference
        if transcription.utterances:
            print(f"\nUTTERANCE TIMING REFERENCE:")
            print("(Useful for manual subtitle timing verification)")
            
            for i, utterance in enumerate(transcription.utterances):
                # Convert seconds to SRT timestamp format
                start_time = format_srt_timestamp(utterance.start)
                end_time = format_srt_timestamp(utterance.end)
                
                print(f"  {i+1:2d}. {start_time} --> {end_time}")
                print(f"      \"{utterance.text}\"")
                
                if i >= 4:  # Show first 5 utterances
                    remaining = len(transcription.utterances) - 5
                    if remaining > 0:
                        print(f"      ... and {remaining} more utterances")
                    break

        # Show processing metadata
        if result.result.metadata:
            meta = result.result.metadata
            print(f"\nPROCESSING METADATA:")
            print(f"  Audio duration: {meta.audio_duration:.1f}s")
            print(f"  Processing time: {meta.transcription_time:.1f}s")
            print(f"  Billing time: {meta.billing_time:.1f}s")

        print("\n" + "=" * 60)
        print("SUBTITLE CONFIGURATION OPTIONS:")
        print("Available subtitle formats:")
        print("  - SRT: Standard subtitle format (.srt)")
        print("  - VTT: WebVTT format for web videos (.vtt)")
        print()
        print("Formatting options:")
        print("  - maximum_characters_per_row: Control line length")
        print("  - maximum_rows_per_caption: Control subtitle height")
        print("  - style: DEFAULT or custom styling options")
        print()
        print("Usage scenarios:")
        print("  - Video editing software integration")
        print("  - Web video player subtitles")
        print("  - Accessibility compliance")
        print("  - Multi-language video content")

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


def format_srt_timestamp(seconds):
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


if __name__ == "__main__":
    success = main()
    
    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: Subtitle generation example completed!")
        print("The subtitle feature can generate SRT/VTT files with")
        print("precise timing for video integration and accessibility.")
    else:
        print("FAILED: Subtitle generation example encountered issues.")
        print("Check your API key, audio file, and feature availability.")
    print("=" * 60)