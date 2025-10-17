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
from .ws_models import (
    events,
    SpeechEvent,
    Transcript,
    Translation,
    NamedEntityRecognition,
    SentimentAnalysis,
    PostTranscript,
    FinalTranscript,
    Chapterization,
    Summarization,
    AudioChunkAcknowledgment,
    StopRecordingAcknowledgment,
    LifecycleEvent,
)

# Import for type hints - avoid circular import
if TYPE_CHECKING:
    from .rest_models import TranscriptionResult

__all__ = [
    "GladiaWebsocketClient",
    "GladiaWebsocketClientSession",
    "InitializeSessionRequest",
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
        # event callbacks (typed)
        self._on_speech_start: Optional[Callable[[SpeechEvent], None]] = None
        self._on_speech_end: Optional[Callable[[SpeechEvent], None]] = None
        self._on_transcript: Optional[Callable[[Transcript], None]] = None
        self._on_translation: Optional[Callable[[Translation], None]] = None
        self._on_ner: Optional[Callable[[NamedEntityRecognition], None]] = None
        self._on_sentiment: Optional[Callable[[SentimentAnalysis], None]] = None
        self._on_post_transcript: Optional[Callable[[PostTranscript], None]] = None
        self._on_final_transcript: Optional[Callable[[FinalTranscript], None]] = None
        self._on_chapterization: Optional[Callable[[Chapterization], None]] = None
        self._on_summarization: Optional[Callable[[Summarization], None]] = None
        self._on_audio_ack: Optional[Callable[[AudioChunkAcknowledgment], None]] = None
        self._on_stop_ack: Optional[Callable[[StopRecordingAcknowledgment], None]] = None
        self._on_start_session: Optional[Callable[[LifecycleEvent], None]] = None
        self._on_end_session: Optional[Callable[[LifecycleEvent], None]] = None
        self._on_start_recording: Optional[Callable[[LifecycleEvent], None]] = None
        self._on_end_recording: Optional[Callable[[LifecycleEvent], None]] = None

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
            # Surface close reason to error callback for diagnostics
            if self._on_error and status_code is not None:
                try:
                    self._on_error(f"WebSocket closed: code={status_code} msg={msg}")
                except Exception:
                    pass
            if self._on_disconnected:
                self._on_disconnected()

        def on_error(ws, error):
            # Suppress normal close-frame notifications (opcode=8 / code 1000)
            msg = str(error)
            if ("opcode=8" in msg) or ("1000" in msg) or ("STATUS_NORMAL" in msg):
                # Treat as normal closure; no error callback
                return
            if self._on_error:
                self._on_error(msg)

        def on_message(ws, message):
            try:
                data = json.loads(message)
            except Exception:
                if self._on_error:
                    self._on_error("Invalid JSON from server")
                return
            event_type = data.get("type")
            print(f"[WS] Received event type: {event_type}")
            # route events
            try:
                if event_type == events.SPEECH_START and self._on_speech_start:
                    self._on_speech_start(SpeechEvent.model_validate(data))
                elif event_type == events.SPEECH_END and self._on_speech_end:
                    self._on_speech_end(SpeechEvent.model_validate(data))
                elif event_type == events.TRANSCRIPT and self._on_transcript:
                    print(f"[WS] Routing TRANSCRIPT event : {data}")
                    self._on_transcript(Transcript.model_validate(data))
                elif event_type == events.TRANSLATION and self._on_translation:
                    self._on_translation(Translation.model_validate(data))
                elif event_type == events.NAMED_ENTITY_RECOGNITION and self._on_ner:
                    self._on_ner(NamedEntityRecognition.model_validate(data))
                elif event_type == events.SENTIMENT_ANALYSIS and self._on_sentiment:
                    self._on_sentiment(SentimentAnalysis.model_validate(data))
                elif event_type == events.POST_TRANSCRIPTION and self._on_post_transcript:
                    print(f"[WS] Routing POST_TRANSCRIPTION event: {data}")
                    self._on_post_transcript(PostTranscript.model_validate(data))
                elif event_type == events.FINAL_TRANSCRIPTION and self._on_final_transcript:
                    print(f"[WS] Routing FINAL_TRANSCRIPTION event : {data}")
                    self._on_final_transcript(FinalTranscript.model_validate(data))
                elif event_type == events.CHAPTERIZATION and self._on_chapterization:
                    self._on_chapterization(Chapterization.model_validate(data))
                elif event_type == events.SUMMARIZATION and self._on_summarization:
                    self._on_summarization(Summarization.model_validate(data))
                elif event_type == events.AUDIO_CHUNK and self._on_audio_ack:
                    self._on_audio_ack(AudioChunkAcknowledgment.model_validate(data))
                elif event_type == events.STOP_RECORDING and self._on_stop_ack:
                    self._on_stop_ack(StopRecordingAcknowledgment.model_validate(data))
                elif event_type == events.START_SESSION and self._on_start_session:
                    self._on_start_session(LifecycleEvent.model_validate(data))
                elif event_type == events.END_SESSION and self._on_end_session:
                    self._on_end_session(LifecycleEvent.model_validate(data))
                elif event_type == events.START_RECORDING and self._on_start_recording:
                    self._on_start_recording(LifecycleEvent.model_validate(data))
                elif event_type == events.END_RECORDING and self._on_end_recording:
                    self._on_end_recording(LifecycleEvent.model_validate(data))
            except Exception as e:
                if self._on_error:
                    self._on_error(f"Failed to parse event {event_type}: {e}")

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

    def set_on_speech_started_callback(self, cb: Callable[[SpeechEvent], None]):
        self._on_speech_start = cb

    def set_on_speech_ended_callback(self, cb: Callable[[SpeechEvent], None]):
        self._on_speech_end = cb

    def set_on_transcript_callback(self, cb: Callable[[Transcript], None]):
        self._on_transcript = cb

    def set_on_translation_callback(self, cb: Callable[[Translation], None]):
        self._on_translation = cb

    def set_on_named_entity_recognition_callback(self, cb: Callable[[NamedEntityRecognition], None]):
        self._on_ner = cb

    def set_on_sentiment_analysis_callback(self, cb: Callable[[SentimentAnalysis], None]):
        self._on_sentiment = cb

    def set_on_post_transcript_callback(self, cb: Callable[[PostTranscript], None]):
        self._on_post_transcript = cb

    def set_on_final_transcript_callback(self, cb: Callable[[FinalTranscript], None]):
        self._on_final_transcript = cb

    def set_on_chapterization_callback(self, cb: Callable[[Chapterization], None]):
        self._on_chapterization = cb

    def set_on_summarization_callback(self, cb: Callable[[Summarization], None]):
        self._on_summarization = cb

    def set_on_audio_chunk_acknowledged_callback(self, cb: Callable[[AudioChunkAcknowledgment], None]):
        self._on_audio_ack = cb

    def set_on_stop_recording_acknowledged_callback(self, cb: Callable[[StopRecordingAcknowledgment], None]):
        self._on_stop_ack = cb

    def set_on_start_session_callback(self, cb: Callable[[LifecycleEvent], None]):
        self._on_start_session = cb

    def set_on_end_session_callback(self, cb: Callable[[LifecycleEvent], None]):
        self._on_end_session = cb

    def set_on_start_recording_callback(self, cb: Callable[[LifecycleEvent], None]):
        self._on_start_recording = cb

    def set_on_end_recording_callback(self, cb: Callable[[LifecycleEvent], None]):
        self._on_end_recording = cb
