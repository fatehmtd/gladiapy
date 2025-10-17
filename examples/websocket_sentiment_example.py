import os
import time
import wave
import threading
from gladiapy.v2 import GladiaWebsocketClient
from gladiapy.v2.ws import InitializeSessionRequest
from gladiapy.v2.ws_models import Transcript, SentimentAnalysis

def read_wav_pcm_data(path: str) -> bytes:
    with wave.open(path, "rb") as w:
        frames = w.readframes(w.getnframes())
    return frames

def main():
    api_key = os.getenv("GLADIA_API_KEY")
    if not api_key:
        print("ERROR: Set GLADIA_API_KEY environment variable")
        return False

    test_wav = os.path.join(os.path.dirname(__file__), "testing.wav")
    test_wav = os.path.abspath(test_wav)
    if not os.path.exists(test_wav):
        print(f"ERROR: Audio file not found: {test_wav}")
        return False

    print("WEBSOCKET REAL-TIME SENTIMENT ANALYSIS EXAMPLE")
    print("=" * 60)
    print("This example demonstrates real-time sentiment analysis capabilities:")
    print("- Live sentiment detection during audio streaming")
    print("- Emotional tone classification in real-time")
    print("- Sentiment scores and confidence levels")
    print("- Original transcript + sentiment analysis simultaneously")
    print()

    try:
        print(f"Loading audio: {test_wav}")
        audio = read_wav_pcm_data(test_wav)
        print(f"Audio loaded: {len(audio)} bytes ({len(audio)/16000/2:.1f}s estimated)")
    except Exception as e:
        print(f"ERROR: Failed to load audio: {e}")
        return False

    client = GladiaWebsocketClient(api_key)
    messages_config = InitializeSessionRequest.MessagesConfig(
        receive_final_transcripts=True,
        receive_partial_transcripts=True,
        receive_realtime_processing_events=True,
        receive_speech_events=False,
        receive_lifecycle_events=False,
    )
    realtime_processing = InitializeSessionRequest.RealtimeProcessing(
        sentiment_analysis=True
    )
    init = InitializeSessionRequest(
        region=InitializeSessionRequest.Region.US_WEST,
        encoding=InitializeSessionRequest.Encoding.WAV_PCM,
        bit_depth=InitializeSessionRequest.BitDepth.BIT_DEPTH_16,
        sample_rate=InitializeSessionRequest.SampleRate.SAMPLE_RATE_16000,
        channels=1,
        model=InitializeSessionRequest.Model.SOLARIA_1,
        endpointing=0.5,
        maximum_duration_without_endpointing=5,
        realtime_processing=realtime_processing,
        messages_config=messages_config,
    )
    session = client.connect(init)
    if not session:
        print("ERROR: Failed to create session")
        return False
    session_info = session.get_session_info()
    session_id = session_info["id"]
    print(f"Session created: {session_id}")
    connection_established = threading.Event()
    websocket_finished = threading.Event()
    sentiment_data = []
    transcript_data = []
    websocket_lock = threading.Lock()

    def on_connected():
        connection_established.set()
        print("WebSocket Connected and ready for real-time sentiment analysis!")
    def on_disconnected():
        websocket_finished.set()
        print("WebSocket Disconnected")
    def on_error(msg):
        print(f"WebSocket Error: {msg}")
    def on_transcript(data: Transcript):
        try:
            text = (data.data.utterance.text or "").strip()
            if text:
                if data.data.is_final:
                    print(f"[FINAL in transcript] {text}")
                else:
                    print(f"[PARTIAL] {text}")
        except Exception as e:
            print(f"Error processing transcript: {e}")
    def on_sentiment_analysis(data: SentimentAnalysis):
        try:
            with websocket_lock:
                sentiment_data.append(data)
            print(f"[SENTIMENT] Sentiment event received")
            if data.data and data.data.results:
                for r in data.data.results[:3]:
                    print(f"[SENTIMENT] {r.sentiment} ({r.emotion}) {r.start:.2f}-{r.end:.2f}s: {r.text}")
        except Exception as e:
            print(f"Error processing sentiment: {e}")
    def on_final_transcript(data):
        with websocket_lock:
            transcript_data.append(data)
        print(f"\n[FINAL] Final transcript received!")
        websocket_finished.set()

    session.set_on_connected_callback(on_connected)
    session.set_on_disconnected_callback(on_disconnected)
    session.set_on_error_callback(on_error)
    session.set_on_transcript_callback(on_transcript)
    session.set_on_sentiment_analysis_callback(on_sentiment_analysis)
    session.set_on_final_transcript_callback(on_final_transcript)

    print("\nConnecting to WebSocket...")
    if not session.connect_and_start():
        print("ERROR: Failed to start WebSocket connection")
        return False
    if connection_established.wait(timeout=10):
        print("Connection confirmed, starting real-time sentiment analysis streaming!")
    else:
        print("WARNING: Connection not confirmed, but proceeding...")
    print("\nStreaming audio with real-time sentiment analysis...")
    print("Watch for [TRANSCRIPT] and [SENTIMENT] messages below:")
    print("-" * 60)
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
            time.sleep(0.05)
        print(f"[STREAM] Audio streaming completed! Sent {chunks_sent} chunks")
        session.send_stop_signal()
        print(f"[STREAM] Stop signal sent")
    except Exception as e:
        print(f"ERROR: Streaming failed: {e}")
        return False
    if websocket_finished.wait(timeout=60):
        print("WebSocket processing completed!")
    else:
        print("Processing timeout, checking final status...")
    print(f"\n" + "=" * 60)
    print("REAL-TIME SENTIMENT ANALYSIS SUMMARY")
    print("=" * 60)
    with websocket_lock:
        print(f"Sentiment events received: {len(sentiment_data)}")
        print(f"Final transcripts received: {len(transcript_data)}")
        if sentiment_data:
            print(f"\nSENTIMENT EVENTS SUMMARY:")
            for i, sentiment_event in enumerate(sentiment_data):
                print(f"  Event {i+1}: {str(sentiment_event)}...")
        if not sentiment_data:
            print(f"\nNo sentiment events detected during streaming.")
            print("This could mean:")
            print("- Sentiment analysis is not enabled for your API key")
            print("- The audio content doesn't have detectable sentiment")
            print("- Sentiment events use a different callback mechanism")
    try:
        print(f"\nGetting final result via API...")
        final_result = client.get_result(session_id)
        if final_result.status == 'done' and final_result.result and final_result.result.transcription:
            trans = final_result.result.transcription
            print(f"Final transcript: \"{trans.full_transcript}\"")
            result_attrs = [attr for attr in dir(final_result.result) if not attr.startswith('_')]
            sentiment_attrs = [attr for attr in result_attrs if 'sentiment' in attr.lower()]
            if sentiment_attrs:
                print(f"Sentiment-related attributes in final result: {sentiment_attrs}")
                for attr in sentiment_attrs:
                    try:
                        sentiment_value = getattr(final_result.result, attr)
                        print(f"  {attr}: {sentiment_value}")
                    except Exception as e:
                        print(f"  {attr}: <could not access: {e}>")
            else:
                print(f"No sentiment attributes found in final result")
                print(f"Available result attributes: {result_attrs}")
    except Exception as e:
        print(f"Final result check failed: {e}")
    print(f"\nREAL-TIME SENTIMENT ANALYSIS CONFIGURATION:")
    print(f"  Sentiment analysis enabled: {realtime_processing.sentiment_analysis}")
    print(f"  Real-time processing events: enabled")
    print(f"  Partial transcripts: enabled")
    print(f"\nSENTIMENT ANALYSIS APPLICATIONS:")
    print("- Customer service call monitoring")
    print("- Live meeting sentiment tracking")
    print("- Real-time feedback analysis")
    print("- Emotional tone detection in conversations")
    print("- Quality assurance for voice interactions")
    try:
        client.delete_result(session_id)
        print(f"\n Cleaned up session: {session_id}")
    except Exception as e:
        print(f"WARNING: Failed to delete session {session_id}: {e}")
    return True

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: WebSocket real-time sentiment analysis example completed!")
        print("The real-time sentiment feature can analyze emotional tone")
        print("and sentiment during live audio streaming.")
    else:
        print("FAILED: WebSocket real-time sentiment analysis example encountered issues.")
        print("Check your API key, audio file, and feature availability.")
    print("=" * 60)