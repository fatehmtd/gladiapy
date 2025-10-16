
from __future__ import annotations
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from pydantic import BaseModel, Field

# Import shared models from rest_models to avoid duplication
from .rest_models import (
    Word,
    Utterance,
    Subtitle,
    Metadata,
    TranscriptionFile,
)

if TYPE_CHECKING:
    from .ws import InitializeSessionRequest

class events:
    """WebSocket event types."""
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

# ============================================================================
# WebSocket Response Models
# ============================================================================

class InitializeSessionResponse(BaseModel):
    """Response for initializing a WebSocket session."""
    id: str
    url: str


class Error(BaseModel):
    """Common error structure for WebSocket responses."""
    status_code: Optional[int] = None
    exception: Optional[str] = None
    message: Optional[str] = None


class SpeechEventData(BaseModel):
    """Data structure for speech events."""
    time: float
    channel: int


class SpeechEvent(BaseModel):
    """Represents a speech event (started/ended)."""
    session_id: str
    created_at: str
    type: str
    data: SpeechEventData


# Type aliases for speech events
SpeechStarted = SpeechEvent
SpeechEnded = SpeechEvent


class TranscriptData(BaseModel):
    """Data structure for transcript events."""
    id: str
    is_final: bool
    utterance: Utterance


class Transcript(BaseModel):
    """Represents a transcript event."""
    session_id: str
    created_at: str
    type: str
    data: TranscriptData


class TranslationData(BaseModel):
    """Data structure for translation events."""
    utterance_id: str
    utterance: Utterance
    original_language: str
    target_language: str
    translated_utterance: Utterance


class Translation(BaseModel):
    """Represents a translation event."""
    session_id: str
    created_at: str
    type: str
    error: Optional[Error] = None
    data: Optional[TranslationData] = None


class NamedEntityRecognitionResultItem(BaseModel):
    """Individual named entity recognition result."""
    entity_type: str
    text: str
    start: float
    end: float


class NamedEntityRecognitionData(BaseModel):
    """Data structure for named entity recognition events."""
    utterance_id: str
    utterance: Utterance
    results: List[NamedEntityRecognitionResultItem] = Field(default_factory=list)


class NamedEntityRecognition(BaseModel):
    """Represents a named entity recognition event."""
    session_id: str
    created_at: str
    type: str
    error: Optional[Error] = None
    data: Optional[NamedEntityRecognitionData] = None


class Sentence(BaseModel):
    """Represents a sentence in the transcription."""
    success: bool
    is_empty: bool
    exec_time: float
    error: Optional[Error] = None
    results: Optional[List[str]] = None


class GenericResult(BaseModel):
    """Generic format of various post-processing results."""
    success: bool
    is_empty: bool
    exec_time: float
    error: Optional[Error] = None
    results: List[str] = Field(default_factory=list)


# Type aliases for generic results
SummarizationResult = GenericResult
ModerationResult = GenericResult
NameConsistencyResult = GenericResult
CustomSpellingResult = GenericResult
SpeakerReidentificationResult = GenericResult
StructuredDataExtractionResult = GenericResult
SentimentAnalysisResult = GenericResult


class NamedEntityRecognitionResultFinal(BaseModel):
    """Named entity recognition result structure for final transcript."""
    success: bool
    is_empty: bool
    exec_time: float
    error: Optional[Error] = None
    entity: Optional[str] = None


class ResultPair(BaseModel):
    """Prompt-response pair for Audio to LLM results."""
    prompt: Optional[str] = None
    response: Optional[str] = None


class AudioToLLMResultItem(BaseModel):
    """Individual Audio to LLM result item."""
    success: bool
    is_empty: bool
    exec_time: float
    error: Optional[Error] = None
    results: Optional[List[ResultPair]] = None


class AudioToLLMResult(BaseModel):
    """Audio to LLM result structure."""
    success: bool
    is_empty: bool
    exec_time: float
    error: Optional[Error] = None
    results: Optional[List[AudioToLLMResultItem]] = None


class DisplayMode(BaseModel):
    """Display mode result structure."""
    success: bool
    is_empty: bool
    exec_time: float
    error: Optional[Error] = None
    results: Optional[List[str]] = None


class ChapterizationResult(BaseModel):
    """Chapterization result structure."""
    success: bool
    is_empty: bool
    exec_time: float
    error: Optional[Error] = None
    results: Optional[str] = None  # Format undefined in API reference


class DiarizationResultItem(BaseModel):
    """Individual diarization result item."""
    start: float
    end: float
    confidence: float
    channel: int
    speaker: Optional[int] = None
    words: List[Word] = Field(default_factory=list)
    text: str
    language: str


class DiarizationResult(BaseModel):
    """Diarization result structure."""
    success: bool
    is_empty: bool
    exec_time: float
    error: Optional[Error] = None
    results: Optional[List[DiarizationResultItem]] = None


# Type alias for enhanced diarization
DiarizationEnhancedResult = DiarizationResult


class Transcription(BaseModel):
    """Represents the transcription event after post-processing."""
    full_transcript: str
    languages: List[str] = Field(default_factory=list)
    subtitles: List[Subtitle] = Field(default_factory=list)
    utterances: List[Utterance] = Field(default_factory=list)
    summarization: Optional[SummarizationResult] = None
    moderation: Optional[ModerationResult] = None
    named_entity_recognition: Optional[NamedEntityRecognitionResultFinal] = None
    name_consistency: Optional[NameConsistencyResult] = None
    custom_spelling: Optional[CustomSpellingResult] = None
    speaker_reidentification: Optional[SpeakerReidentificationResult] = None
    structured_data_extraction: Optional[StructuredDataExtractionResult] = None
    sentiment_analysis: Optional[SentimentAnalysisResult] = None
    audio_to_llm: Optional[AudioToLLMResult] = None
    display_mode: Optional[DisplayMode] = None
    chapters: Optional[ChapterizationResult] = None
    diarization_enhanced: Optional[DiarizationEnhancedResult] = None
    diarization: Optional[DiarizationResult] = None


class PostTranscriptData(BaseModel):
    """Data structure for post-transcript events."""
    full_transcript: str
    languages: List[str] = Field(default_factory=list)
    utterances: List[Utterance] = Field(default_factory=list)
    sentences: List[Sentence] = Field(default_factory=list)
    results: Optional[List[str]] = None
    subtitles: Optional[List[Subtitle]] = None


class PostTranscript(BaseModel):
    """Represents a post-transcript event."""
    session_id: str
    created_at: str
    type: str
    error: Optional[Error] = None
    data: PostTranscriptData


class FinalTranscriptData(BaseModel):
    """Data structure for final transcript events."""
    metadata: Metadata
    transcription: Optional[Transcription] = None
    translation: Optional["TranslationResultForLive"] = None


class FinalTranscript(BaseModel):
    """Represents the final transcript event."""
    session_id: str
    created_at: str
    type: str
    error: Optional[Error] = None
    data: FinalTranscriptData


class SummarizationData(BaseModel):
    """Data structure for summarization events."""
    results: str


class Summarization(BaseModel):
    """Represents a summarization event."""
    session_id: str
    created_at: str
    type: str
    error: Optional[Error] = None
    data: Optional[SummarizationData] = None


class SentimentAnalysisResultItem(BaseModel):
    """Individual sentiment analysis result item."""
    sentiment: str
    emotion: str
    text: str
    start: float
    end: float
    channel: float


class SentimentAnalysisData(BaseModel):
    """Data structure for sentiment analysis events."""
    utterance_id: str
    utterance: Utterance
    results: List[SentimentAnalysisResultItem] = Field(default_factory=list)


class SentimentAnalysis(BaseModel):
    """Represents a sentiment analysis event."""
    session_id: str
    created_at: str
    type: str
    data: SentimentAnalysisData


class Chapter(BaseModel):
    """Represents a chapter in chapterization results."""
    headline: str
    gist: str
    keywords: List[str] = Field(default_factory=list)
    start: float
    end: float
    sentences: List[Sentence] = Field(default_factory=list)
    text: str
    abstractive_summary: str
    extractive_summary: str
    summary: str


class ChapterizationData(BaseModel):
    """Data structure for chapterization events."""
    results: List[Chapter] = Field(default_factory=list)


class Chapterization(BaseModel):
    """Represents a chapterization event."""
    session_id: str
    created_at: str
    type: str
    error: Optional[Error] = None
    data: Optional[ChapterizationData] = None


class LifecycleEvent(BaseModel):
    """Represents a lifecycle event."""
    session_id: str
    created_at: str
    type: str


# Type aliases for lifecycle events
StartSession = LifecycleEvent
EndSession = LifecycleEvent
StartRecording = LifecycleEvent
EndRecording = LifecycleEvent


class AudioChunkAcknowledgmentData(BaseModel):
    """Data structure for audio chunk acknowledgment."""
    byte_range: List[float] = Field(default_factory=list)
    time_range: List[float] = Field(default_factory=list)


class AudioChunkAcknowledgment(BaseModel):
    """Represents an audio chunk acknowledgment event."""
    session_id: str
    created_at: str
    type: str
    acknowledged: bool
    error: Optional[Error] = None
    data: Optional[AudioChunkAcknowledgmentData] = None


class StopRecordingAcknowledgmentData(BaseModel):
    """Data structure for stop recording acknowledgment."""
    recording_duration: float
    recording_left_to_process: float


class StopRecordingAcknowledgment(BaseModel):
    """Represents a stop recording acknowledgment event."""
    session_id: str
    created_at: str
    type: str
    acknowledged: bool
    error: Optional[Error] = None
    data: Optional[StopRecordingAcknowledgmentData] = None


class TranslationResultEntry(BaseModel):
    """Individual translation result entry."""
    error: Optional[Error] = None
    full_transcript: str
    languages: List[str] = Field(default_factory=list)
    utterances: List[Utterance] = Field(default_factory=list)
    sentences: Optional[List[Sentence]] = None
    subtitles: Optional[List[Subtitle]] = None


class TranslationResultForLive(BaseModel):
    """Translation result structure for live transcription."""
    success: bool
    is_empty: bool
    exec_time: float
    error: Optional[Error] = None
    results: Optional[List[TranslationResultEntry]] = None


class LiveTranscriptionResultData(BaseModel):
    """Data structure for live transcription result."""
    metadata: Metadata
    messages: List[str] = Field(default_factory=list)
    transcription: Optional[Transcription] = None
    translation: Optional[TranslationResultForLive] = None
    summarization: Optional[SummarizationResult] = None
    moderation: Optional[ModerationResult] = None
    named_entity_recognition: Optional[NamedEntityRecognitionResultFinal] = None
    name_consistency: Optional[NameConsistencyResult] = None
    custom_spelling: Optional[CustomSpellingResult] = None
    speaker_reidentification: Optional[SpeakerReidentificationResult] = None
    structured_data_extraction: Optional[StructuredDataExtractionResult] = None
    sentiment_analysis: Optional[SentimentAnalysisResult] = None
    audio_to_llm: Optional[AudioToLLMResult] = None
    display_mode: Optional[DisplayMode] = None
    chapters: Optional[ChapterizationResult] = None
    diarization_enhanced: Optional[DiarizationEnhancedResult] = None
    diarization: Optional[DiarizationResult] = None


class LiveTranscriptionResult(BaseModel):
    """Represents a live transcription result."""
    id: str
    request_id: str
    version: int
    status: str
    created_at: str
    completed_at: Optional[str] = None
    kind: str
    custom_metadata: Optional[str] = None
    error_code: Optional[int] = None
    file: TranscriptionFile
    request_params: Dict[str, Any]  # InitializeSessionRequest - kept as Dict to avoid circular import
    result: LiveTranscriptionResultData

