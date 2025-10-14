
"""
Gladia WebSocket client for real-time audio transcription.

This module provides a Pythonic API for gladiapy WebSocket client, supporting all event types, session lifecycle, and typed event payloads.

Usage:
    from gladiapy.v2.ws import GladiaWebsocketClient, InitializeSessionRequest
    client = GladiaWebsocketClient(api_key)
    session = client.connect(InitializeSessionRequest(...))
    session.set_on_transcript_callback(lambda transcript: print(transcript.text))
    session.connect_and_start()
    session.send_audio_binary(audio_bytes, len(audio_bytes))
    session.send_stop_signal()
    session.disconnect()
"""

from __future__ import annotations
import os
import json
import threading
import time
import base64
from dataclasses import dataclass, asdict, fields
from typing import Callable, Optional, Any, Dict, List, TYPE_CHECKING
from websocket import WebSocketApp
from .constants import headers as H, common as C
from .errors import GladiaError
import requests

# Import for type hints - avoid circular import
if TYPE_CHECKING:
    from .rest_models import TranscriptionResult

__all__ = [
    "GladiaWebsocketClient",
    "GladiaWebsocketClientSession",
    "InitializeSessionRequest",
    "events",
]


def _api_base_url() -> str:
    return f"https://{C.HOST}"


def _dataclass_to_dict(obj: Any, exclude_none: bool = True) -> Any:
    """
    Convert a dataclass instance to a dictionary, recursively handling nested dataclasses.
    
    Args:
        obj: Dataclass instance to convert
        exclude_none: Whether to exclude None values from the output
    
    Returns:
        Dictionary representation suitable for JSON serialization
    """
    if not hasattr(obj, '__dataclass_fields__'):
        # Not a dataclass, return as-is
        if isinstance(obj, (list, tuple)):
            return [_dataclass_to_dict(item, exclude_none) for item in obj]
        elif isinstance(obj, dict):
            return {k: _dataclass_to_dict(v, exclude_none) for k, v in obj.items()}
        return obj
    
    result = {}
    for field in fields(obj):
        value = getattr(obj, field.name)
        
        # Skip None values if requested
        if exclude_none and value is None:
            continue
        
        # Recursively convert nested dataclasses
        if hasattr(value, '__dataclass_fields__'):
            result[field.name] = _dataclass_to_dict(value, exclude_none)
        elif isinstance(value, (list, tuple)):
            # Handle lists/tuples that might contain dataclasses
            converted_list = []
            for item in value:
                if hasattr(item, '__dataclass_fields__'):
                    converted_list.append(_dataclass_to_dict(item, exclude_none))
                else:
                    converted_list.append(item)
            if converted_list or not exclude_none:  # Include empty lists if not excluding None
                result[field.name] = converted_list
        elif isinstance(value, dict):
            # Handle dicts that might contain dataclasses
            result[field.name] = {k: _dataclass_to_dict(v, exclude_none) for k, v in value.items()}
        else:
            # Primitive value
            result[field.name] = value
    
    return result


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
    """Contains the parameters for initializing a WebSocket session."""
    
    # Enums
    class Region:
        US_WEST = "us-west"
        EU_WEST = "eu-west"
    
    class Encoding:
        WAV_PCM = "wav/pcm"
        WAV_ALAW = "wav/alaw"
        WAV_ULAW = "wav/ulaw"
    
    class BitDepth:
        BIT_DEPTH_8 = 8
        BIT_DEPTH_16 = 16
        BIT_DEPTH_24 = 24
        BIT_DEPTH_32 = 32
    
    class SampleRate:
        SAMPLE_RATE_8000 = 8000
        SAMPLE_RATE_16000 = 16000
        SAMPLE_RATE_32000 = 32000
        SAMPLE_RATE_44100 = 44100
        SAMPLE_RATE_48000 = 48000
    
    class Model:
        SOLARIA_1 = "solaria-1"
    
    @dataclass
    class LanguageConfig:
        """Language configuration"""
        languages: Optional[List[str]] = None
        code_switching: bool = False
        
        def __post_init__(self):
            if self.languages is None:
                self.languages = []
    
    @dataclass
    class PreProcessing:
        """Pre-processing configuration"""
        audio_enhancer: bool = False
        speech_threshold: float = 0.6  # VAD threshold, between 0 (Permissive) and 1 (Strict)
    
    @dataclass
    class RealtimeProcessing:
        """Real-time processing configuration"""
        
        @dataclass
        class Vocabulary:
            """Represents a single vocabulary entry"""
            value: str = ""
            intensity: float = 0.5
            pronunciations: Optional[List[str]] = None
            language: str = "en"
            
            def __post_init__(self):
                if self.pronunciations is None:
                    self.pronunciations = []
        
        @dataclass
        class CustomVocabularyConfig:
            """Configuration for custom vocabulary"""
            vocabulary: Optional[List["InitializeSessionRequest.RealtimeProcessing.Vocabulary"]] = None
            default_intensity: Optional[float] = 0.5
        
        @dataclass
        class CustomSpellingConfig:
            """Configuration for custom spelling"""
            spelling_dictionary: Optional[Dict[str, List[str]]] = None
            
            def __post_init__(self):
                if self.spelling_dictionary is None:
                    self.spelling_dictionary = {}
        
        @dataclass
        class TranslationConfig:
            """Configuration for audio translation"""
            
            class Model:
                BASE = "base"
                ENHANCED = "enhanced"
            
            model: str = "base"
            target_languages: Optional[List[str]] = None
            match_original_utterances: Optional[bool] = True
            lipsync: Optional[bool] = True
            context_adaptation: Optional[bool] = False
            context: Optional[str] = None
            informal: Optional[bool] = False
            
            def __post_init__(self):
                if self.target_languages is None:
                    self.target_languages = []
        
        custom_vocabulary: bool = False
        custom_vocabulary_config: Optional[CustomVocabularyConfig] = None
        custom_spelling: bool = False
        custom_spelling_config: Optional[CustomSpellingConfig] = None
        translation: bool = False
        translation_config: Optional[TranslationConfig] = None
        named_entity_recognition: Optional[bool] = False
        sentiment_analysis: Optional[bool] = False
    
    @dataclass
    class PostProcessing:
        """Configuration for post-processing"""
        
        @dataclass
        class SummarizationConfig:
            """Configuration for summarization"""
            
            class Type:
                GENERAL = "general"
                BULLET_POINTS = "bullet_points"
                CONCISE = "concise"
            
            type: str = "general"
        
        summarization: Optional[bool] = False
        summarization_config: Optional[SummarizationConfig] = None
        chapterization: Optional[bool] = False
    
    @dataclass
    class MessagesConfig:
        """Configuration for message handling"""
        receive_partial_transcripts: Optional[bool] = False
        receive_final_transcripts: Optional[bool] = True
        receive_speech_events: Optional[bool] = True
        receive_pre_processing_events: Optional[bool] = True
        receive_realtime_processing_events: Optional[bool] = True
        receive_post_processing_events: Optional[bool] = True
        receive_acknowledgments: Optional[bool] = True
        receive_errors: Optional[bool] = True
        receive_lifecycle_events: Optional[bool] = True
    
    @dataclass
    class CallbackConfig:
        """Configuration for callbacks"""
        url: Optional[str] = None
        receive_partial_transcripts: Optional[bool] = False
        receive_final_transcripts: Optional[bool] = True
        receive_speech_events: Optional[bool] = False
        receive_pre_processing_events: Optional[bool] = True
        receive_realtime_processing_events: Optional[bool] = True
        receive_post_processing_events: Optional[bool] = True
        receive_acknowledgments: Optional[bool] = False
        receive_errors: Optional[bool] = False
        receive_lifecycle_events: Optional[bool] = True
    
    # Main fields
    region: str = "us-west"
    encoding: str = "wav/pcm"
    bit_depth: int = 16
    sample_rate: int = 16000
    channels: int = 1
    custom_metadata: Optional[str] = None
    model: str = "solaria-1"
    endpointing: float = 0.05
    maximum_duration_without_endpointing: int = 5
    language_config: Optional[LanguageConfig] = None
    pre_processing: Optional[PreProcessing] = None
    realtime_processing: Optional[RealtimeProcessing] = None
    post_processing: Optional[PostProcessing] = None
    messages_config: Optional[MessagesConfig] = None
    callback: Optional[bool] = False
    callback_config: Optional[CallbackConfig] = None

    def to_json(self) -> Dict[str, Any]:
        """
        Convert this request to a JSON-serializable dictionary.
        Uses Python's dataclass introspection for clean, automatic conversion.
        """
        # Convert the entire dataclass hierarchy to dict, excluding None values
        result = _dataclass_to_dict(self, exclude_none=True)
        
        # Region is passed as URL query param, not in body, so exclude it
        result.pop('region', None)
        
        return result


class GladiaWebsocketClient:
    """Client for Gladia WebSocket API real-time transcription."""

    def __init__(self, api_key: str) -> None:
        self.api_key: str = api_key
        self._http = requests.Session()
        self._http.headers.update({
            "User-Agent": C.USER_AGENT,
            H.X_GLADIA_KEY: self.api_key,
        })

    def connect(self, init_request: InitializeSessionRequest) -> "GladiaWebsocketClientSession":
        """Create WebSocket session for real-time transcription.
        
        Args:
            init_request: Session configuration (audio format, options)
            
        Returns:
            GladiaWebsocketClientSession for streaming audio
            
        Raises:
            GladiaError: If session creation fails with API error details
            requests.RequestException: For network errors
            ValueError: If response is missing session_id or ws_url
        """
        # Start session via REST to get ws URL and ID, with region as query param (as in C++ impl)
        region = init_request.region
        url = _api_base_url() + f"{C.LIVE_ENDPOINT}?region={region}"
        resp = self._http.post(url, json=init_request.to_json())
        if resp.status_code >= 400:
            raise GladiaError.from_response(resp, "Failed to create WebSocket session")
        data = resp.json()
        session_id = data.get("id")
        ws_url = data.get("url")
        if not session_id or not ws_url:
            raise ValueError(f"Invalid response: missing session_id or ws_url: {data}")
        return GladiaWebsocketClientSession(session_id=session_id, ws_url=ws_url, api_key=self.api_key)

    def get_result(self, id: str) -> "TranscriptionResult":
        """Get WebSocket session transcription results.
        
        Args:
            id: Session ID from connect() call
            
        Returns:
            TranscriptionResult with final transcription data
            
        Raises:
            GladiaError: If request fails with API error details
            requests.RequestException: For network errors
        """
        from .rest_models import TranscriptionResult
        url = _api_base_url() + f"{C.LIVE_ENDPOINT}/{id}"
        resp = self._http.get(url)
        if resp.status_code >= 400:
            raise GladiaError.from_response(resp, f"Failed to get result for session {id}")
        return TranscriptionResult.model_validate(resp.json())

    def delete_result(self, id: str) -> bool:
        """Delete WebSocket session transcription results.
        
        Args:
            id: Session ID to delete
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            GladiaError: If deletion fails with API error details
            requests.RequestException: For network errors
        """
        url = _api_base_url() + f"{C.LIVE_ENDPOINT}/{id}"
        resp = self._http.delete(url)
        if resp.status_code >= 400:
            raise GladiaError.from_response(resp, f"Failed to delete session {id}")
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
