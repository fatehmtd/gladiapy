from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class UploadAudioMetadata(BaseModel):
    """
    Metadata for uploaded audio files.
    """    
    id: str
    filename: str
    extension: str
    size: int
    audio_duration: float
    number_of_channels: int


class UploadResponse(BaseModel):
    """
    Response model for audio file uploads.
    """    
    audio_url: str
    audio_metadata: UploadAudioMetadata


class TranscriptionJobResponse(BaseModel):
    """
    Response model for transcription job submission.
    """    
    id: str
    result_url: str


class Word(BaseModel):
    """Individual word with timing and confidence data."""
    word: str
    start: float
    end: float
    confidence: float


class Utterance(BaseModel):
    """Speech segment with timing, text, and word-level details."""
    language: str
    start: float
    end: float
    confidence: float
    channel: int
    words: List[Word] = Field(default_factory=list)
    text: str
    speaker: Optional[int] = None


class Subtitle(BaseModel):
    """Subtitle data in various formats (SRT, VTT, etc.)."""
    format: str
    subtitles: str


class Metadata(BaseModel):
    """Processing metadata for transcription jobs."""
    audio_duration: float
    number_of_distinct_channels: int
    billing_time: float
    transcription_time: float


class TranscriptionObjectResult(BaseModel):
    """Complete transcription results with text, utterances, and subtitles."""
    full_transcript: str
    languages: List[str] = Field(default_factory=list)
    utterances: List[Utterance] = Field(default_factory=list)
    subtitles: List[Subtitle] = Field(default_factory=list)


class TranscriptionObject(BaseModel):
    """Container for transcription results and processing metadata."""
    metadata: Metadata
    transcription: Optional[TranscriptionObjectResult] = None


class TranscriptionFile(BaseModel):
    """Audio file information for transcription jobs."""
    id: str
    filename: str
    source: Optional[str] = None
    audio_duration: Optional[float] = None
    number_of_channels: int


class TranscriptionResult(BaseModel):
    """Complete transcription job result with status and data."""
    id: str
    request_id: str
    version: int
    status: str
    created_at: str
    kind: str
    completed_at: Optional[str] = None
    error_code: Optional[int] = None
    file: Optional[TranscriptionFile] = None
    request_params: Optional[Dict[str, Any]] = None
    result: Optional[TranscriptionObject] = None


class ListResultsPage(BaseModel):
    """Paginated list of transcription results."""
    first: str
    current: str
    next: Optional[str] = None
    items: List[TranscriptionResult] = Field(default_factory=list)


class CallbackConfig(BaseModel):
    """Configuration for webhook callbacks on job completion."""
    url: str
    method: str = Field(pattern=r"^(POST|PUT)$")


class SubtitlesConfig(BaseModel):
    """Configuration for subtitle generation (SRT, VTT formats)."""
    formats: List[str]
    maximum_characters_per_row: Optional[int] = None
    maximum_rows_per_caption: Optional[int] = None
    style: Optional[str] = "DEFAULT"


class DiarizationConfig(BaseModel):
    """Configuration for speaker diarization (who spoke when)."""
    number_of_speakers: Optional[int] = None
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None
    enhanced: Optional[bool] = None


class TranslationConfig(BaseModel):
    """Configuration for multi-language translation."""
    model: str = "BASE"
    target_languages: List[str] = Field(default_factory=list)
    match_original_utterances: Optional[bool] = True
    lipsync: Optional[bool] = True
    context_adaptation: Optional[bool] = True
    context: Optional[str] = None
    informal: Optional[bool] = False


class SummarizationConfig(BaseModel):
    """Configuration for AI-powered content summarization."""
    types: List[str]


class CustomSpellingConfig(BaseModel):
    """Configuration for custom spelling corrections and vocabulary."""
    spelling_dictionary: Dict[str, List[str]]


class StructuredDataExtractionConfig(BaseModel):
    """Configuration for extracting structured data from transcripts."""
    classes: List[str]


class AudioToLLMConfig(BaseModel):
    """Configuration for LLM processing of audio transcripts."""
    prompts: List[str]


class LanguageConfig(BaseModel):
    """Configuration for language detection and code-switching."""
    languages: List[str]
    code_switching: bool = False


class TranscriptionRequest(BaseModel):
    """Complete configuration for transcription jobs with all available features."""
    audio_url: str
    custom_vocabulary_config: Optional[List[Dict[str, Any]]] = None

    callback: bool = False
    callback_config: Optional[CallbackConfig] = None

    subtitles: bool = False
    subtitles_config: Optional[SubtitlesConfig] = None

    diarization: bool = False
    diarization_config: Optional[DiarizationConfig] = None

    translation: bool = False
    translation_config: TranslationConfig = Field(default_factory=TranslationConfig)

    summarization: bool = False
    summarization_config: Optional[SummarizationConfig] = None

    moderation: bool = False
    named_entity_recognition: bool = False
    chapterization: bool = False
    name_consistency: bool = False

    custom_spelling: bool = False
    custom_spelling_config: Optional[CustomSpellingConfig] = None

    structured_data_extraction: bool = False
    structured_data_extraction_config: Optional[StructuredDataExtractionConfig] = None

    sentiment_analysis: bool = False
    audio_to_llm: bool = False
    audio_to_llm_config: Optional[AudioToLLMConfig] = None

    sentences: bool = False
    display_mode: bool = False
    punctuation_enhanced: bool = False
    language_config: Optional[LanguageConfig] = None


class ListResultsQuery(BaseModel):
    """Query parameters for listing transcription results with pagination and filtering."""
    offset: int = 0
    limit: int = 20
    date: Optional[str] = None
    before_date: Optional[str] = None
    after_date: Optional[str] = None
    status: List[str] = Field(default_factory=list)
