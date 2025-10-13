from __future__ import annotations
import os
import json
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional, Any, Dict, TYPE_CHECKING
from websocket import WebSocketApp
from .constants import headers as H, common as C
from .errors import TranscriptionError
from dotenv import load_dotenv
import requests

# Import for type hints - avoid circular import
if TYPE_CHECKING:
    from .rest_models import TranscriptionResult


class events:
    AUDIO_CHUNK = "audio_chunk"
    STOP_RECORDING = "stop_recording"
    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"
    TRANSCRIPT = "transcript"
    TRANSLATION = "translation"
    NAMED_ENTITY_RECOGNITION = "named_entity_recognition"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    POST_TRANSCRIPTION = "post_transcript"
    FINAL_TRANSCRIPTION = "post_final_transcript"
    CHAPTERIZATION = "post_chapterization"
    SUMMARIZATION = "post_summarization"
    START_SESSION = "start_session"
    END_SESSION = "end_session"
    START_RECORDING = "start_recording"
    END_RECORDING = "end_recording"


def _api_base_url() -> str:
    return f"https://{C.HOST}"


"""
Gladia WebSocket client for real-time audio transcription.

This module provides a Pythonic API mirroring the C++ gladiapp WebSocket client, supporting all event types, session lifecycle, and typed event payloads.

Usage:
    from gladiapp.v2.ws import GladiaWebsocketClient, InitializeSessionRequest
    client = GladiaWebsocketClient(api_key)
    session = client.connect(InitializeSessionRequest(...))
    session.set_on_transcript_callback(lambda transcript: print(transcript.text))
    session.connect_and_start()
    session.send_audio_binary(audio_bytes, len(audio_bytes))
    session.send_stop_signal()
    session.disconnect()
"""

import os
import json
import threading
import time
import base64
from dataclasses import dataclass
from typing import Callable, Optional, Any, Dict, List
from websocket import WebSocketApp
from .constants import headers as H, common as C
from .errors import TranscriptionError
from dotenv import load_dotenv
import requests

__all__ = [
    "GladiaWebsocketClient",
    "GladiaWebsocketClientSession",
    "InitializeSessionRequest",
    "events",
]

class events:
    AUDIO_CHUNK = "audio_chunk"
    STOP_RECORDING = "stop_recording"
    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"
    TRANSCRIPT = "transcript"
    TRANSLATION = "translation"
    NAMED_ENTITY_RECOGNITION = "named_entity_recognition"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    POST_TRANSCRIPTION = "post_transcript"
    FINAL_TRANSCRIPTION = "post_final_transcript"
    CHAPTERIZATION = "post_chapterization"
    SUMMARIZATION = "post_summarization"
    START_SESSION = "start_session"
    END_SESSION = "end_session"
    START_RECORDING = "start_recording"
    END_RECORDING = "end_recording"

@dataclass
class InitializeSessionRequest:
    # Minimal subset for now; can be expanded to full parity.
    region: str = "us-west"
    encoding: str = "wav_pcm"
    bit_depth: int = 16
    sample_rate: int = 16000
    channels: int = 1
    model: str = "solaria-1"
    endpointing: float = 0.05
    maximum_duration_without_endpointing: int = 5
    messages_config: Optional[Dict[str, Any]] = None
    realtime_processing: Optional[Dict[str, Any]] = None
    post_processing: Optional[Dict[str, Any]] = None
    custom_metadata: Optional[str] = None

    def to_json(self) -> Dict[str, Any]:
        # Convert encoding format: wav_pcm -> wav/pcm
        encoding = self.encoding.replace("_", "/") if self.encoding else "wav/pcm"
        
        return {
            # region is passed in URL query param, not in body
            "encoding": encoding,
            "bit_depth": self.bit_depth,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "model": self.model,
            "endpointing": self.endpointing,
            "maximum_duration_without_endpointing": self.maximum_duration_without_endpointing,
            **({"messages_config": self.messages_config} if self.messages_config else {}),
            **({"realtime_processing": self.realtime_processing} if self.realtime_processing else {}),
            **({"post_processing": self.post_processing} if self.post_processing else {}),
            **({"custom_metadata": self.custom_metadata} if self.custom_metadata else {}),
        }


class GladiaWebsocketClient:
    """Client for Gladia WebSocket API real-time transcription."""
    
    def __init__(self, api_key: Optional[str] = None) -> None:
        load_dotenv()
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("API key is required (set GLADIA_API_KEY or pass api_key)")
        self._http = requests.Session()
        self._http.headers.update({
            "User-Agent": C.USER_AGENT,
            H.X_GLADIA_KEY: self.api_key,
        })

    def connect(self, init_request: InitializeSessionRequest, transcription_error: Optional[TranscriptionError] = None) -> Optional["GladiaWebsocketClientSession"]:
        """Create WebSocket session for real-time transcription.
        
        Args:
            init_request: Session configuration (audio format, options)
            
        Returns:
            GladiaWebsocketClientSession for streaming audio
        """
        # Start session via REST to get ws URL and ID, with region as query param (as in C++ impl)
        region = init_request.region
        url = _api_base_url() + f"{C.LIVE_ENDPOINT}?region={region}"
        resp = self._http.post(url, json=init_request.to_json())
        if resp.status_code >= 400:
            if transcription_error is not None:
                try:
                    data = resp.json()
                except Exception:
                    data = {"status": resp.status_code, "message": resp.text}
                te = TranscriptionError.from_json(data)
                transcription_error.timestamp = getattr(te, "timestamp", "")
                transcription_error.path = getattr(te, "path", "")
                transcription_error.request_id = te.request_id
                transcription_error.status_code = te.status_code
                transcription_error.message = te.message
                transcription_error.validation_errors = te.validation_errors
            resp.raise_for_status()
        data = resp.json()
        session_id = data.get("id")
        ws_url = data.get("url")
        if not session_id or not ws_url:
            return None
        return GladiaWebsocketClientSession(session_id=session_id, ws_url=ws_url, api_key=self.api_key)

    def get_result(self, id: str, transcription_error: Optional[TranscriptionError] = None) -> "TranscriptionResult":
        """Get WebSocket session transcription results.
        
        Args:
            id: Session ID from connect() call
            
        Returns:
            TranscriptionResult with final transcription data
        """
        from .rest_models import TranscriptionResult
        url = _api_base_url() + f"{C.LIVE_ENDPOINT}/{id}"
        resp = self._http.get(url)
        if resp.status_code >= 400:
            if transcription_error is not None:
                try:
                    data = resp.json()
                except Exception:
                    data = {"status": resp.status_code, "message": resp.text}
                te = TranscriptionError.from_json(data)
                transcription_error.timestamp = getattr(te, "timestamp", "")
                transcription_error.path = getattr(te, "path", "")
                transcription_error.request_id = te.request_id
                transcription_error.status_code = te.status_code
                transcription_error.message = te.message
                transcription_error.validation_errors = te.validation_errors
            resp.raise_for_status()
        return TranscriptionResult.model_validate(resp.json())

    def delete_result(self, id: str, transcription_error: Optional[TranscriptionError] = None) -> bool:
        """Delete WebSocket session transcription results.
        
        Args:
            id: Session ID to delete
            
        Returns:
            bool: True if deletion was successful
        """
        url = _api_base_url() + f"{C.LIVE_ENDPOINT}/{id}"
        resp = self._http.delete(url)
        if resp.status_code >= 400:
            if transcription_error is not None:
                try:
                    data = resp.json()
                except Exception:
                    data = {"status": resp.status_code, "message": resp.text}
                te = TranscriptionError.from_json(data)
                transcription_error.timestamp = getattr(te, "timestamp", "")
                transcription_error.path = getattr(te, "path", "")
                transcription_error.request_id = te.request_id
                transcription_error.status_code = te.status_code
                transcription_error.message = te.message
                transcription_error.validation_errors = te.validation_errors
            resp.raise_for_status()
        return True


class GladiaWebsocketClientSession:
    """Active WebSocket session for streaming audio transcription."""
    
    def __init__(self, session_id: str, ws_url: str, api_key: str) -> None:
        self._id = session_id
        self._url = ws_url
        self._api_key = api_key
        self._ws: Optional[WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        # callbacks
        self._on_connected: Optional[Callable[[], None]] = None
        self._on_disconnected: Optional[Callable[[], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        # event callbacks
        self._on_speech_start: Optional[Callable[[dict], None]] = None
        self._on_speech_end: Optional[Callable[[dict], None]] = None
        self._on_transcript: Optional[Callable[[dict], None]] = None
        self._on_translation: Optional[Callable[[dict], None]] = None
        self._on_ner: Optional[Callable[[dict], None]] = None
        self._on_sentiment: Optional[Callable[[dict], None]] = None
        self._on_post_transcript: Optional[Callable[[dict], None]] = None
        self._on_final_transcript: Optional[Callable[[dict], None]] = None
        self._on_chapterization: Optional[Callable[[dict], None]] = None
        self._on_summarization: Optional[Callable[[dict], None]] = None
        self._on_audio_ack: Optional[Callable[[dict], None]] = None
        self._on_stop_ack: Optional[Callable[[dict], None]] = None
        self._on_start_session: Optional[Callable[[dict], None]] = None
        self._on_end_session: Optional[Callable[[dict], None]] = None
        self._on_start_recording: Optional[Callable[[dict], None]] = None
        self._on_end_recording: Optional[Callable[[dict], None]] = None

    def get_session_info(self) -> dict:
        return {"id": self._id, "url": self._url}

    def connect_and_start(self) -> bool:
        """Connect to WebSocket session and start real-time transcription.
        
        Returns:
            bool: True when connection is established
        """
        # No need to attach auth header to WS: token is embedded in the URL
        headers = ["User-Agent: " + C.USER_AGENT]

        def on_open(ws):
            if self._on_connected:
                self._on_connected()

        def on_close(ws, status_code, msg):
            if self._on_disconnected:
                self._on_disconnected()

        def on_error(ws, error):
            if self._on_error:
                self._on_error(str(error))

        def on_message(ws, message):
            try:
                data = json.loads(message)
            except Exception:
                if self._on_error:
                    self._on_error("Invalid JSON from server")
                return
            t = data.get("type")
            # route events
            if t == events.SPEECH_START and self._on_speech_start:
                self._on_speech_start(data)
            elif t == events.SPEECH_END and self._on_speech_end:
                self._on_speech_end(data)
            elif t == events.TRANSCRIPT and self._on_transcript:
                self._on_transcript(data)
            elif t == events.TRANSLATION and self._on_translation:
                self._on_translation(data)
            elif t == events.NAMED_ENTITY_RECOGNITION and self._on_ner:
                self._on_ner(data)
            elif t == events.SENTIMENT_ANALYSIS and self._on_sentiment:
                self._on_sentiment(data)
            elif t == events.POST_TRANSCRIPTION and self._on_post_transcript:
                self._on_post_transcript(data)
            elif t == events.FINAL_TRANSCRIPTION and self._on_final_transcript:
                self._on_final_transcript(data)
            elif t == events.CHAPTERIZATION and self._on_chapterization:
                self._on_chapterization(data)
            elif t == events.SUMMARIZATION and self._on_summarization:
                self._on_summarization(data)
            elif t == events.AUDIO_CHUNK and self._on_audio_ack:
                self._on_audio_ack(data)
            elif t == events.STOP_RECORDING and self._on_stop_ack:
                self._on_stop_ack(data)
            elif t == events.START_SESSION and self._on_start_session:
                self._on_start_session(data)
            elif t == events.END_SESSION and self._on_end_session:
                self._on_end_session(data)
            elif t == events.START_RECORDING and self._on_start_recording:
                self._on_start_recording(data)
            elif t == events.END_RECORDING and self._on_end_recording:
                self._on_end_recording(data)

        self._ws = WebSocketApp(self._url, header=headers, on_open=on_open, on_close=on_close, on_error=on_error, on_message=on_message)
        self._thread = threading.Thread(target=self._ws.run_forever, kwargs={"ping_interval": 20, "ping_timeout": 10}, daemon=True)
        self._thread.start()
        # crude wait for connection
        time.sleep(0.5)
        return True

    def send_stop_signal(self) -> bool:
        """Send stop signal to end transcription session.
        
        Returns:
            bool: True if stop signal was sent successfully
        """
        if not self._ws:
            return False
        payload = json.dumps({"type": events.STOP_RECORDING})
        self._ws.send(payload)
        return True

    def disconnect(self) -> None:
        if self._ws:
            try:
                self._ws.close()
            finally:
                self._ws = None

    def send_audio_binary(self, audio_data: bytes | bytearray | memoryview, size: int) -> bool:
        """Send audio data to WebSocket as binary frame.
        
        Args:
            audio_data: Raw audio bytes
            size: Number of bytes to send
            
        Returns:
            bool: True if data was sent successfully
        """
        if not self._ws:
            return False
        # send as binary frame
        self._ws.send(audio_data[:size], opcode=0x2)  # 0x2 = OPCODE_BINARY
        return True

    def send_audio_json(self, audio_data: bytes | bytearray | memoryview, size: int) -> bool:
        if not self._ws:
            return False
        import base64
        chunk_b64 = base64.b64encode(bytes(audio_data[:size])).decode("ascii")
        payload = json.dumps({"type": events.AUDIO_CHUNK, "data": {"chunk": chunk_b64}})
        self._ws.send(payload)
        return True

    # callback setters
    def set_on_connected_callback(self, cb: Callable[[], None]):
        self._on_connected = cb

    def set_on_disconnected_callback(self, cb: Callable[[], None]):
        self._on_disconnected = cb

    def set_on_error_callback(self, cb: Callable[[str], None]):
        self._on_error = cb

    def set_on_speech_started_callback(self, cb: Callable[[dict], None]):
        self._on_speech_start = cb

    def set_on_speech_ended_callback(self, cb: Callable[[dict], None]):
        self._on_speech_end = cb

    def set_on_transcript_callback(self, cb: Callable[[dict], None]):
        self._on_transcript = cb

    def set_on_translation_callback(self, cb: Callable[[dict], None]):
        self._on_translation = cb

    def set_on_named_entity_recognition_callback(self, cb: Callable[[dict], None]):
        self._on_ner = cb

    def set_on_sentiment_analysis_callback(self, cb: Callable[[dict], None]):
        self._on_sentiment = cb

    def set_on_post_transcript_callback(self, cb: Callable[[dict], None]):
        self._on_post_transcript = cb

    def set_on_final_transcript_callback(self, cb: Callable[[dict], None]):
        self._on_final_transcript = cb

    def setOnChapterizationCallback(self, cb: Callable[[dict], None]):
        self._on_chapterization = cb

    def setOnSummarizationCallback(self, cb: Callable[[dict], None]):
        self._on_summarization = cb

    def setOnAudioChunkAcknowledgedCallback(self, cb: Callable[[dict], None]):
        self._on_audio_ack = cb

    def setOnStopRecordingAcknowledgedCallback(self, cb: Callable[[dict], None]):
        self._on_stop_ack = cb

    def setOnStartSessionCallback(self, cb: Callable[[dict], None]):
        self._on_start_session = cb

    def setOnEndSessionCallback(self, cb: Callable[[dict], None]):
        self._on_end_session = cb

    def setOnStartRecordingCallback(self, cb: Callable[[dict], None]):
        self._on_start_recording = cb

    def setOnEndRecordingCallback(self, cb: Callable[[dict], None]):
        self._on_end_recording = cb
