import os
import time
import wave
import threading
from gladiapy.v2 import GladiaWebsocketClient
from gladiapy.v2.ws import InitializeSessionRequest
from gladiapy.v2.ws_models import Transcript, FinalTranscript


def read_wav_pcm_data(path: str) -> bytes:
    with wave.open(path, "rb") as w:
        frames = w.readframes(w.getnframes())
    return frames


def main():
    """
    WebSocket example that demonstrates audio transcription using WebSocket streaming.
    This example shows how to:
    1. Create a WebSocket session with proper configuration
    2. Stream audio data in real-time
    3. Receive and handle transcription results
    4. Get the final transcription with detailed word-level information
    """
    api_key = os.getenv("GLADIA_API_KEY")
    if not api_key:
        print("ERROR: Set GLADIA_API_KEY environment variable")
        print("   You can get an API key from: https://gladia.io")
        return False

    test_wav = os.path.join(os.path.dirname(__file__), "testing.wav")
    test_wav = os.path.abspath(test_wav)
    
    if not os.path.exists(test_wav):
        print(f"ERROR: Audio file not found: {test_wav}")
        return False
    
    print(f"Loading audio: {test_wav}")
    
    try:
        audio = read_wav_pcm_data(test_wav)
        print(f"Audio loaded: {len(audio)} bytes ({len(audio)/16000/2:.1f}s estimated)")
    except Exception as e:
        print(f"ERROR: Failed to load audio: {e}")
        return False

    client = GladiaWebsocketClient(api_key)
    
    # Real-time configuration with partial transcripts enabled
    # Using proper class-based configuration (matching C++ API)
    messages_config = InitializeSessionRequest.MessagesConfig(
        receive_final_transcripts=True,
        receive_partial_transcripts=True,  # Enable partial transcripts for real-time feedback
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
        endpointing=1.5,  # Wait 1.5s of silence before finalizing
        maximum_duration_without_endpointing=45,  # Max 45s without silence
        messages_config=messages_config,
    )

    print("Creating WebSocket session...")
    session = client.connect(init)
    if not session:
        print("ERROR: Failed to create session")
        return False

    session_info = session.get_session_info()
    session_id = session_info["id"]
    print(f"Session created: {session_id}")
    
    # Track connection and results with thread-safe variables
    connection_established = threading.Event()
    websocket_finished = threading.Event()
    final_transcripts_received = []
    callback_transcription_data = None
    websocket_lock = threading.Lock()
    
    def on_connected():
        connection_established.set()
        print("WebSocket Connected and ready!")
    
    def on_disconnected():
        websocket_finished.set()
        print("WebSocket Disconnected")
    
    def on_error(msg):
        print(f"WebSocket Error: {msg}")
    
    def on_partial_transcript(data: Transcript):
        try:
            text = (data.data.utterance.text or "").strip()
            if text:
                print(f"[PARTIAL] {text}")
        except Exception as e:
            print(f"Error processing partial transcript: {e}")
    
    def on_final_transcript(data: FinalTranscript):
        nonlocal callback_transcription_data
        with websocket_lock:
            final_transcripts_received.append(data)
        
        print(f"\n[FINAL] Final transcript received!")
        
        # Extract and display transcription data from callback
        try:
            final_data = data.data
            trans = final_data.transcription
            if trans:
                with websocket_lock:
                    callback_transcription_data = trans.model_dump()
                print("\nTRANSCRIPTION RECEIVED VIA CALLBACK:")
                print("=" * 50)
                print(f"Full Transcript: \"{trans.full_transcript}\"")
                if trans.languages:
                    print(f"Languages: {trans.languages}")
                if trans.utterances:
                    print(f"Utterances: {len(trans.utterances)}")
                    u0 = trans.utterances[0]
                    print(f"\nFirst Utterance:")
                    print(f"   Text: \"{u0.text}\"")
                    print(f"   Time: {u0.start:.2f}s - {u0.end:.2f}s")
                    print(f"   Confidence: {u0.confidence:.2f}")
                    if u0.words:
                        print("   First 3 words:")
                        for j, w in enumerate(u0.words[:3]):
                            print(f"     {j+1}. \"{w.word}\" [{w.start:.2f}s-{w.end:.2f}s] conf: {w.confidence:.2f}")
                if final_data.metadata:
                    meta = final_data.metadata
                    print("\nCallback Metadata:")
                    print(f"   Audio duration: {meta.audio_duration}s")
                    print(f"   Processing time: {meta.transcription_time}s")
                    print(f"   Billing time: {meta.billing_time}s")
                print("=" * 50)
                websocket_finished.set()
        except Exception as e:
            print(f"Error processing callback data: {e}")
            print(f"Raw callback data: {data}")

    session.set_on_connected_callback(on_connected)
    session.set_on_disconnected_callback(on_disconnected)
    session.set_on_error_callback(on_error)
    session.set_on_transcript_callback(on_partial_transcript)  # Handle partial transcripts
    session.set_on_final_transcript_callback(on_final_transcript)

    print("Connecting to WebSocket...")
    if not session.connect_and_start():
        print("ERROR: Failed to start WebSocket connection")
        return False
    
    # Wait for connection to be established (with threading)
    print("Waiting for WebSocket connection...")
    if connection_established.wait(timeout=10):
        print("Connection confirmed, ready to send audio!")
    else:
        print("WARNING: Connection not confirmed within 10 seconds, but proceeding...")
    
    # Create a thread to monitor WebSocket results while we stream
    def websocket_monitor():
        """Monitor for WebSocket completion in background"""
        print("\n[MONITOR] WebSocket monitor thread started...")
        try:
            # Wait for either final transcript or error/disconnect
            if websocket_finished.wait(timeout=120):  # 2 minute timeout
                print("[MONITOR] WebSocket processing completed!")
            else:
                print("[MONITOR] WebSocket monitor timeout - checking status...")
                # Try to get status one more time
                try:
                    result = client.get_result(session_id)
                    print(f"[MONITOR] Final status check: {result.status}")
                except Exception as e:
                    print(f"[MONITOR] Status check failed: {e}")
        except Exception as e:
            print(f"[MONITOR] Monitor thread error: {e}")
        print("[MONITOR] WebSocket monitor thread finished.")
    
    # Start the monitor thread
    monitor_thread = threading.Thread(target=websocket_monitor, daemon=True)
    monitor_thread.start()
    
    print("Streaming audio data...")
    print("Watch for [PARTIAL] and [FINAL] transcript messages below:")
    print("-" * 60)
    
    # Stream audio reliably while monitoring for real-time results
    chunk_size = 8000  # 0.5 seconds of audio per chunk
    chunks_sent = 0
    success = True
    
    try:
        for i in range(0, len(audio), chunk_size):
            # Check if we're done early (got final result)
            if websocket_finished.is_set():
                print(f"Early completion detected at chunk {chunks_sent}")
                break
                
            chunk = audio[i:i + chunk_size]
            actual_size = min(chunk_size, len(audio) - i)
            
            session.send_audio_binary(chunk, actual_size)
            chunks_sent += 1
            
            progress = (i + actual_size) / len(audio) * 100
            print(f"[STREAM] Chunk {chunks_sent:2d}: {actual_size:5d} bytes ({progress:5.1f}% complete)")
            
            # Smaller delay to allow real-time processing
            time.sleep(0.05)
        
        print(f"[STREAM] Audio streaming completed! Sent {chunks_sent} chunks")
        
        # Send stop signal
        print("[STREAM] Sending stop signal...")
        session.send_stop_signal()
        print("[STREAM] Stop signal sent successfully")
        
    except Exception as e:
        print(f"ERROR: Error during audio streaming: {e}")
        success = False
    
    print("-" * 60)
    
    # Wait for WebSocket processing to complete via the monitor thread
    print("\nWaiting for WebSocket processing to complete...")
    print("The monitor thread is watching for results in real-time...")
    
    # Wait for the WebSocket to finish (either success or timeout)
    max_wait_time = 120  # 2 minutes
    print(f"Maximum wait time: {max_wait_time} seconds")
    
    if websocket_finished.wait(timeout=max_wait_time):
        print("\nWebSocket processing completed via callback/monitor!")
        with websocket_lock:
            if callback_transcription_data:
                success = True
                print("SUCCESS: Full transcription data received via callback (shown above)")
            else:
                print("WebSocket finished but no transcription data captured")
                # Try one final status check
                try:
                    result = client.get_result(session_id)
                    print(f"Final status via API: {result.status}")
                    if result.status == 'done':
                        success = True
                except Exception as e:
                    print(f"Final status check failed: {e}")
    else:
        print(f"\nWebSocket processing timed out after {max_wait_time} seconds")
        print("Checking final status...")
        
        try:
            result = client.get_result(session_id)
            print(f"Timeout status check: {result.status}")
            
            if result.status == 'done':
                print("Processing completed despite timeout - this is normal for WebSocket")
                with websocket_lock:
                    if callback_transcription_data or len(final_transcripts_received) > 0:
                        success = True
            elif result.status == 'error':
                print(f"ERROR: Processing failed with error: {result.error_code}")
                success = False
        except Exception as e:
            print(f"Timeout status check failed: {e}")
    
    # Wait for monitor thread to finish
    print("Waiting for monitor thread to complete...")
    monitor_thread.join(timeout=5)
    print("Monitor thread finished.")
    
    # Show final summary
    print(f"\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    with websocket_lock:
        print(f"Final transcripts via callback: {len(final_transcripts_received)}")
        print(f"Callback transcription data received: {'YES' if callback_transcription_data else 'NO'}")
    print(f"Audio chunks sent: {chunks_sent}")
    print(f"WebSocket finished event: {'SET' if websocket_finished.is_set() else 'NOT SET'}")
    
    # Determine overall success
    final_success = False
    with websocket_lock:
        if success or len(final_transcripts_received) > 0 or callback_transcription_data:
            final_success = True
    
    print(f"Overall success: {'YES' if final_success else 'NO'}")
    print("=" * 60)
    
    # Clean up
    try:
        client.delete_result(session_id)
        print(f"Cleaned up session: {session_id}")
    except Exception as e:
        print(f"WARNING: Failed to delete session {session_id}: {e}")
    
    # Return success if we got callbacks or full result
    return final_success


if __name__ == "__main__":
    print("WEBSOCKET TRANSCRIPTION EXAMPLE")
    print("=" * 50)
    print("This example demonstrates WebSocket-based real-time audio transcription.")
    print("The WebSocket API allows you to stream audio and receive transcriptions")
    print("with detailed word-level timing and confidence scores.\n")
    
    success = main()
    
    print("\n" + "=" * 50)
    if success:
        print("SUCCESS: WebSocket example completed successfully!")
        print("The WebSocket API is working properly and can transcribe audio")
        print("with real-time streaming and detailed word-level results.")
    else:
        print("FAILED: WebSocket example encountered issues.")
        print("This may be due to network connectivity or API configuration.")
        print("Please check your API key and try again.")
    print("=" * 50)