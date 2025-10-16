# gladiapy API Reference

Python client library for Gladia's speech-to-text API. Provides REST and WebSocket interfaces for audio transcription with advanced processing capabilities. The WebSocket client uses typed events (Pydantic models) for safer, clearer callbacks.

## Installation

```bash
git clone https://github.com/fatehmtd/gladiapy.git
cd gladiapy
pip install -e .
```

## Authentication

```python
import os
from gladiapy.v2 import GladiaRestClient, GladiaWebsocketClient

# Configure API key
api_key = os.getenv("GLADIA_API_KEY")
```

## REST API

### GladiaRestClient

Primary client class for batch transcription operations.

```python
client = GladiaRestClient(api_key)
```

#### Core Methods

##### upload(file_path: str) → UploadResponse

Uploads audio file to Gladia servers.

- **Parameters:** `file_path` - Local path to audio file
- **Returns:** Object containing `audio_url` field for transcription requests

##### pre_recorded(request: TranscriptionRequest) → JobResponse

Initiates batch transcription job.

- **Parameters:** `request` - Configured transcription request object
- **Returns:** Job object with `id` field for status polling

##### get_result(job_id: str) → TranscriptionResult

Retrieves transcription job status and results.

- **Parameters:** `job_id` - Job identifier from pre_recorded call
- **Returns:** Result object with `status`, `result`, and `error_code` fields

##### list_results(limit: int = 20, offset: int = 0) → ResultsPage

Lists recent transcription jobs.

- **Parameters:** `limit` - Maximum results to return, `offset` - Pagination offset
- **Returns:** Page object containing `items` array of job summaries

##### delete_result(job_id: str) → None

Removes transcription job and associated data.

- **Parameters:** `job_id` - Job identifier to delete

#### Request Models

##### TranscriptionRequest

Primary configuration object for transcription jobs.

```python
from gladiapy.v2.rest_models import TranscriptionRequest

request = TranscriptionRequest(
    audio_url="https://api.gladia.io/file/...",
    # Basic options
    language="auto",  # or specific language code
    transcription_hint="",  # Context for better accuracy
    
    # Advanced processing features
    translation=True,
    translation_config=TranslationConfig(target_languages=["fr", "es"]),
    summarization=True,
    summarization_config=SummarizationConfig(types=["general"]),
    chapterization=True,
    sentiment_analysis=True,
    named_entity_recognition=True,
    
    # Audio processing
    diarization=True,  # Speaker identification
    custom_vocabulary=["technical", "terms"],
    subtitles=True,
    subtitles_config=SubtitlesConfig(formats=["srt", "vtt"])
)
```

#### Response Models

##### TranscriptionResult

Complete transcription job result structure.

- `status`: Job status ("queued" | "processing" | "done" | "error")
- `result.transcription.full_transcript`: Complete transcribed text
- `result.transcription.utterances[]`: Time-segmented speech array
- `result.transcription.utterances[].words[]`: Word-level timing data
- `result.metadata`: Processing metadata (duration, billing information)
- `result.translation`: Translation results if enabled
- `result.summarization`: Summary text if enabled
- `result.chapterization`: Chapter breakdown if enabled
- `result.sentiment_analysis`: Sentiment data if enabled
- `result.named_entity_recognition`: Entity extraction if enabled

#### REST API Example

```python
import time
from gladiapy.v2 import GladiaRestClient
from gladiapy.v2.rest_models import TranscriptionRequest

client = GladiaRestClient(api_key)

# Upload audio file
upload_result = client.upload("audio.wav")

# Configure transcription with advanced features
request = TranscriptionRequest(
    audio_url=upload_result.audio_url,
    summarization=True,
    sentiment_analysis=True,
    named_entity_recognition=True
)

# Start transcription job
job = client.pre_recorded(request)

# Poll for completion
while True:
    result = client.get_result(job.id)
    if result.status == "done":
        print("Transcript:", result.result.transcription.full_transcript)
        print("Summary:", result.result.summarization.results)
        break
    elif result.status == "error":
        print("Error:", result.error_code)
        break
    time.sleep(3)

# Clean up
client.delete_result(job.id)
```

## WebSocket API

### GladiaWebsocketClient

Client interface for real-time streaming transcription. Events are delivered as typed models defined in `gladiapy.v2.ws_models`.

```python
client = GladiaWebsocketClient(api_key)
```

#### Client Methods

##### connect(config: InitializeSessionRequest) → GladiaWebsocketClientSession

Creates new WebSocket transcription session.

- **Parameters:** `config` - Session configuration object
- **Returns:** Active session instance for audio streaming

##### get_result(session_id: str) → TranscriptionResult

Retrieves final transcription result after streaming completion.

- **Parameters:** `session_id` - Session identifier
- **Returns:** Complete transcription result object

##### delete_result(session_id: str) → None

Cleans up WebSocket session and associated resources.

- **Parameters:** `session_id` - Session identifier to remove

### GladiaWebsocketClientSession

Active WebSocket session instance for real-time audio streaming operations.

#### Session Management Methods

##### get_session_info() → dict

Returns session metadata including session ID and connection details.

##### connect_and_start() → bool

Establishes WebSocket connection and initializes transcription session.

- **Returns:** Boolean indicating connection success

##### send_audio_binary(data: bytes, size: int) → None

Streams audio data chunk to transcription service.

- **Parameters:** `data` - Audio data bytes, `size` - Chunk size in bytes

##### send_stop_signal() → None

Signals end of audio stream to complete transcription processing.

#### Event Callback Configuration (typed)

Each callback receives a typed Pydantic model from `gladiapy.v2.ws_models`.

- `set_on_connected_callback(callback: () -> None)`
- `set_on_disconnected_callback(callback: () -> None)`
- `set_on_error_callback(callback: (str) -> None)`
- `set_on_speech_started_callback(callback: (SpeechEvent) -> None)`
- `set_on_speech_ended_callback(callback: (SpeechEvent) -> None)`
- `set_on_transcript_callback(callback: (Transcript) -> None)`
- `set_on_translation_callback(callback: (Translation) -> None)`
- `set_on_named_entity_recognition_callback(callback: (NamedEntityRecognition) -> None)`
- `set_on_sentiment_analysis_callback(callback: (SentimentAnalysis) -> None)`
- `set_on_post_transcript_callback(callback: (PostTranscript) -> None)`
- `set_on_final_transcript_callback(callback: (FinalTranscript) -> None)`
- `setOnChapterizationCallback(callback: (Chapterization) -> None)`
- `setOnSummarizationCallback(callback: (Summarization) -> None)`
- `setOnAudioChunkAcknowledgedCallback(callback: (AudioChunkAcknowledgment) -> None)`
- `setOnStopRecordingAcknowledgedCallback(callback: (StopRecordingAcknowledgment) -> None)`
- `setOnStartSessionCallback(callback: (LifecycleEvent) -> None)`
- `setOnEndSessionCallback(callback: (LifecycleEvent) -> None)`
- `setOnStartRecordingCallback(callback: (LifecycleEvent) -> None)`
- `setOnEndRecordingCallback(callback: (LifecycleEvent) -> None)`

CamelCase aliases are provided for parity with the C++ API (e.g., `setOnTranscriptCallback`).

#### Session Configuration

##### InitializeSessionRequest

Configuration object for WebSocket session parameters.

```python
from gladiapy.v2.ws import InitializeSessionRequest

config = InitializeSessionRequest(
    # Audio format specification
    encoding="wav_pcm",          # Audio encoding format
    bit_depth=16,                # Audio bit depth
    sample_rate=16000,           # Audio sample rate in Hz
    channels=1,                  # Number of audio channels
    
    # Processing configuration
    endpointing=1.5,             # Silence detection threshold (seconds)
    maximum_duration_without_endpointing=45,  # Maximum processing duration
    
    # Feature enablement
    sentiment_analysis=True,     # Real-time sentiment analysis
    translation=True,            # Real-time translation
    translation_config={"target_languages": ["fr", "es"]},
    
    # Message delivery options
    messages_config={
        "receive_final_transcripts": True,
        "receive_partial_transcripts": True,
        "receive_speech_events": False,
        "receive_lifecycle_events": False,
    }
)
```

#### WebSocket Streaming Example (typed callbacks)

```python
import wave
import time
from gladiapy.v2 import GladiaWebsocketClient
from gladiapy.v2.ws import InitializeSessionRequest
from gladiapy.v2.ws_models import Transcript, FinalTranscript

# Load audio file
with wave.open("audio.wav", "rb") as wav_file:
    audio_data = wav_file.readframes(wav_file.getnframes())

# Initialize WebSocket client
client = GladiaWebsocketClient(api_key)

# Configure session with real-time features
config = InitializeSessionRequest(
    encoding="wav_pcm",
    bit_depth=16,
    sample_rate=16000,
    channels=1,
    sentiment_analysis=True,
    translation=True,
    translation_config={"target_languages": ["es"]},
    messages_config={
        "receive_final_transcripts": True,
        "receive_partial_transcripts": True
    }
)

# Create session and configure callbacks
session = client.connect(config)
def on_partial(event: Transcript):
    print(f"Partial: {event.data.utterance.text}")

def on_final(event: FinalTranscript):
    print("Final transcript received")

session.set_on_transcript_callback(on_partial)
session.set_on_final_transcript_callback(on_final)

# Stream audio in chunks
if session.connect_and_start():
    chunk_size = 8000
    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i:i + chunk_size]
        session.send_audio_binary(chunk, len(chunk))
        time.sleep(0.1)
    
    session.send_stop_signal()
    
    # Retrieve final result
    session_info = session.get_session_info()
    result = client.get_result(session_info["id"])
    print("Complete transcript:", result.result.transcription.full_transcript)
    
    # Clean up
    client.delete_result(session_info["id"])
```

## Error Handling

### GladiaError Exception

All API errors are wrapped in GladiaError exceptions containing structured error information.

```python
from gladiapy.v2 import GladiaError

try:
    result = client.get_result(job_id)
    if result.status == "error":
        print(f"Transcription failed: {result.error_code}")
except GladiaError as e:
    print(f"API error [{e.status_code}]: {e.message}")
    if hasattr(e, 'request_id'):
        print(f"Request ID: {e.request_id}")
    if hasattr(e, 'validation_errors'):
        print(f"Validation errors: {e.validation_errors}")
```

## Data Structures

### Transcription Result Format

```python
{
    "full_transcript": "Complete transcribed text content",
    "languages": ["en"],
    "utterances": [
        {
            "text": "Individual speech segment text",
            "start": 0.34,           # Start time in seconds
            "end": 2.15,             # End time in seconds  
            "confidence": 0.95,      # Confidence score (0-1)
            "channel": 0,            # Audio channel identifier
            "words": [
                {
                    "word": "Hello",
                    "start": 0.34,
                    "end": 0.67,
                    "confidence": 0.98
                }
            ]
        }
    ]
}
```

### Processing Metadata

```python
{
    "audio_duration": 11.2,              # Total audio duration (seconds)
    "transcription_time": 3.4,           # Processing time (seconds)
    "billing_time": 11.2,                # Billable duration (seconds)
    "number_of_distinct_channels": 1     # Audio channel count
}
```

## Configuration

### Environment Variables

```bash
export GLADIA_API_KEY="your-api-key-here"
```

### Configuration File

Create `.env` file in your project directory:

```bash
GLADIA_API_KEY=your-api-key-here
```

## Advanced Features

### Available Processing Options

- **Translation**: Real-time or batch translation to multiple target languages
- **Summarization**: Automatic content summarization with configurable types
- **Sentiment Analysis**: Emotional tone and sentiment classification
- **Named Entity Recognition**: Extraction of persons, organizations, locations
- **Chapterization**: Content segmentation with headlines and summaries
- **Speaker Diarization**: Multi-speaker identification and separation
- **Custom Vocabulary**: Domain-specific terminology recognition
- **Subtitles**: Multiple format subtitle generation (SRT, VTT, etc.)

### Processing Configuration Examples

Examples for each feature are in the `/examples` directory (run with `python -m ...`):

- `sentiment_analysis_example.py`
- `summarization_example.py`
- `named_entity_recognition_example.py`
- `chapterization_example.py`
- `translation_example.py`
- `speaker_diarization_example.py`
- `subtitles_example.py`
- `custom_vocabulary_example.py`
