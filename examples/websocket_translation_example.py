import os
import time
import wave
import threading
from gladiapy.v2 import GladiaWebsocketClient
from gladiapy.v2.ws import InitializeSessionRequest


def read_wav_pcm_data(path: str) -> bytes:
    with wave.open(path, "rb") as w:
        frames = w.readframes(w.getnframes())
    return frames


def main():
    """
    WebSocket Real-time Translation example demonstrating live multilingual translation.
    This example shows how to:
    1. Configure real-time translation during WebSocket streaming
    2. Receive original transcripts and translations simultaneously
    3. Handle multiple target languages in real-time
    4. Process translation events and callbacks
    """
    api_key = os.getenv("GLADIA_API_KEY")
    if not api_key:
        print("ERROR: Set GLADIA_API_KEY environment variable")
        return False

    test_wav = os.path.join(os.path.dirname(__file__), "testing.wav")
    test_wav = os.path.abspath(test_wav)
    
    if not os.path.exists(test_wav):
        print(f"ERROR: Audio file not found: {test_wav}")
        return False

    print("WEBSOCKET REAL-TIME TRANSLATION EXAMPLE")
    print("=" * 60)
    print("This example demonstrates real-time translation capabilities:")
    print("- Live translation during audio streaming")
    print("- Multiple target languages simultaneously")
    print("- Original transcript + translations in real-time")
    print("- Translation timing and synchronization")
    print()

    try:
        print(f"Loading audio: {test_wav}")
        audio = read_wav_pcm_data(test_wav)
        print(f"Audio loaded: {len(audio)} bytes ({len(audio)/16000/2:.1f}s estimated)")

        client = GladiaWebsocketClient(api_key)
        
        # Configure WebSocket session with real-time translation
        translation_config = InitializeSessionRequest.RealtimeProcessing.TranslationConfig(
            model="base",  # Use base translation model
            target_languages=["fr", "es"],  # French and Spanish
            match_original_utterances=True,
            lipsync=True,
            context_adaptation=True,
            informal=False  # Formal translation style
        )
        
        realtime_processing = InitializeSessionRequest.RealtimeProcessing(
            translation=True,
            translation_config=translation_config
        )

        # Configure messages to receive both transcripts and translations
        messages_config = InitializeSessionRequest.MessagesConfig(
            receive_final_transcripts=True,
            receive_partial_transcripts=True,  # Real-time transcripts
            receive_realtime_processing_events=True,  # Translation events
            receive_speech_events=False,
            receive_lifecycle_events=False,
        )

        init = InitializeSessionRequest(
            region=InitializeSessionRequest.Region.US_WEST,
            encoding=InitializeSessionRequest.Encoding.WAV_PCM,
            bit_depth=InitializeSessionRequest.BitDepth.BIT_DEPTH_16,
            sample_rate=InitializeSessionRequest.SampleRate.SAMPLE_RATE_16000,
            channels=1,
            model=InitializeSessionRequest.Model.SOLARIA_1,
            endpointing=1.5,
            maximum_duration_without_endpointing=45,
            realtime_processing=realtime_processing,  # Enable translation
            messages_config=messages_config,
        )
        
        print("\nConfiguring WebSocket session with translation...")
        print(f"Translation model: {translation_config.model}")
        langs = translation_config.target_languages or []
        print(f"Target languages: {', '.join(langs)}")
        print(f"Match original timing: {translation_config.match_original_utterances}")

        session = client.connect(init)
        if not session:
            print("ERROR: Failed to create session")
            return False

        session_info = session.get_session_info()
        session_id = session_info["id"]
        print(f"Session created: {session_id}")
        
        # Track connection and results
        connection_established = threading.Event()
        websocket_finished = threading.Event()
        translation_data = []
        transcript_data = []
        websocket_lock = threading.Lock()
        
        def on_connected():
            connection_established.set()
            print("WebSocket Connected and ready for real-time translation!")
        
        def on_disconnected():
            websocket_finished.set()
            print("WebSocket Disconnected")
        
        def on_error(msg):
            print(f"WebSocket Error: {msg}")
        
        def on_partial_transcript(data):
            """Handle partial transcripts (original language)"""
            try:
                if isinstance(data, dict) and 'data' in data:
                    utterance = data['data'].get('utterance', {})
                    text = utterance.get('text', '').strip()
                    if text:
                        print(f"[ORIGINAL] {text}")
            except Exception as e:
                print(f"Error processing partial transcript: {e}")
        
        def on_translation(data):
            """Handle real-time translation events"""
            try:
                with websocket_lock:
                    translation_data.append(data)
                
                print(f"[TRANSLATION] Translation event received")
                
                if isinstance(data, dict):
                    # Extract translation information
                    if 'data' in data:
                        trans_data = data['data']
                        
                        # Look for translation content
                        if 'translation' in trans_data:
                            translation_info = trans_data['translation']
                            
                            # Handle different translation data structures
                            if isinstance(translation_info, dict):
                                for lang, content in translation_info.items():
                                    if isinstance(content, dict) and 'text' in content:
                                        print(f"[{lang.upper()}] {content['text']}")
                                    elif isinstance(content, str):
                                        print(f"[{lang.upper()}] {content}")
                            else:
                                print(f"[TRANSLATION] {translation_info}")
                        
                        # Alternative: look for utterance with language info
                        elif 'utterance' in trans_data:
                            utterance = trans_data['utterance']
                            text = utterance.get('text', '')
                            language = utterance.get('language', 'unknown')
                            if text and language != 'en':  # Non-English might be translation
                                print(f"[{language.upper()}] {text}")
                    
                    # Debug: show structure if translation not found as expected
                    if 'data' not in data or 'translation' not in data.get('data', {}):
                        print(f"Translation data structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                        if isinstance(data, dict) and 'data' in data:
                            print(f"  Data keys: {list(data['data'].keys())}")
            
            except Exception as e:
                print(f"Error processing translation: {e}")
        
        def on_final_transcript(data):
            """Handle final transcripts"""
            with websocket_lock:
                transcript_data.append(data)
            
            print(f"\n[FINAL] Final transcript received!")
            websocket_finished.set()

        # Set up callbacks
        session.set_on_connected_callback(on_connected)
        session.set_on_disconnected_callback(on_disconnected)
        session.set_on_error_callback(on_error)
        session.set_on_transcript_callback(on_partial_transcript)
        session.set_on_translation_callback(on_translation)  # Translation callback
        session.set_on_final_transcript_callback(on_final_transcript)

        print("\nConnecting to WebSocket...")
        if not session.connect_and_start():
            print("ERROR: Failed to start WebSocket connection")
            return False
        
        # Wait for connection
        if connection_established.wait(timeout=10):
            print("Connection confirmed, starting real-time translation streaming!")
        else:
            print("WARNING: Connection not confirmed, but proceeding...")
        
        print("\nStreaming audio with real-time translation...")
        print("Watch for [ORIGINAL], [FR], [ES] messages below:")
        print("-" * 60)
        
        # Stream audio
        chunk_size = 8000
        chunks_sent = 0
        
        try:
            for i in range(0, len(audio), chunk_size):
                if websocket_finished.is_set():
                    print(f"Early completion at chunk {chunks_sent}")
                    break

                chunk = audio[i:i + chunk_size]
                actual_size = min(chunk_size, len(audio) - i)

                session.send_audio_binary(chunk, actual_size)
                chunks_sent += 1

                progress = (i + actual_size) / len(audio) * 100
                print(f"[STREAM] Chunk {chunks_sent:2d}: {actual_size:5d} bytes ({progress:5.1f}% complete)")

                time.sleep(0.05)  # Small delay for real-time processing

            print(f"[STREAM] Audio streaming completed! Sent {chunks_sent} chunks")
            session.send_stop_signal()
            print(f"[STREAM] Stop signal sent")

        except Exception as e:
            print(f"ERROR: Streaming failed: {e}")
            return False
        
        print("-" * 60)
        
        # Wait for processing to complete
        print(f"\nWaiting for translation processing to complete...")
        
        if websocket_finished.wait(timeout=60):
            print("WebSocket processing completed!")
        else:
            print("Processing timeout, checking final status...")
        
        # Show final results
        print(f"\n" + "=" * 60)
        print("REAL-TIME TRANSLATION SUMMARY")
        print("=" * 60)
        
        with websocket_lock:
            print(f"Translation events received: {len(translation_data)}")
            print(f"Final transcripts received: {len(transcript_data)}")
            
            if translation_data:
                print(f"\nTRANSLATION EVENTS SUMMARY:")
                for i, trans_event in enumerate(translation_data[:5]):  # Show first 5
                    print(f"  Event {i+1}: {str(trans_event)[:100]}...")
                
                if len(translation_data) > 5:
                    print(f"  ... and {len(translation_data) - 5} more events")
        
        # Try to get final result via API
        try:
            print(f"\nGetting final result via API...")
            final_result = client.get_result(session_id)

            if final_result.status == 'done' and final_result.result and final_result.result.transcription:
                trans = final_result.result.transcription
                print(f"Final transcript: \"{trans.full_transcript}\"")

                # Look for translation data in final result
                if hasattr(final_result.result, 'translation'):
                    print(f"Translation data found in final result")
                else:
                    print(f"Translation data structure may be different in final result")
                    result_attrs = [attr for attr in dir(final_result.result) if not attr.startswith('_')]
                    trans_attrs = [attr for attr in result_attrs if 'trans' in attr.lower()]
                    print(f"Translation-related attributes: {trans_attrs}")

        except Exception as e:
            print(f"Final result check failed: {e}")

        print(f"\nREAL-TIME TRANSLATION CONFIGURATION:")
        print(f"  Model: {translation_config.model}")
        langs = translation_config.target_languages or []
        print(f"  Target languages: {', '.join(langs)}")
        print(f"  Context adaptation: {translation_config.context_adaptation}")
        print(f"  Lipsync: {translation_config.lipsync}")
        print(f"  Match timing: {translation_config.match_original_utterances}")

        # Clean up
        try:
            client.delete_result(session_id)
            print(f"\nCleaned up session: {session_id}")
        except Exception as e:
            print(f"WARNING: Failed to delete session {session_id}: {e}")

        return True

    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    
    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: WebSocket real-time translation example completed!")
        print("The real-time translation feature can translate speech")
        print("in multiple languages during live audio streaming.")
    else:
        print("FAILED: WebSocket real-time translation example encountered issues.")
        print("Check your API key, audio file, and feature availability.")
    print("=" * 60)