# gladiapy API Reference

Python client for Gladia's speech-to-text API. Supports both REST and WebSocket transcription.

## Installation

```bash
pip install gladiapy
```

## Quick Start

```python
import os
from gladiapp.v2 import GladiaRestClient, GladiaWebsocketClient

# Set your API key
api_key = os.getenv("GLADIA_API_KEY")
```

## REST API

### GladiaRestClient

Main client for batch transcription jobs.

```python
client = GladiaRestClient(api_key)
```

#### Methods

**upload(file_path: str) → UploadResponse**
- Uploads audio file to Gladia
- Returns: Object with `audio_url` field

**preRecorded(request: TranscriptionRequest) → JobResponse**  
- Starts transcription job
- Returns: Object with `id` field for job tracking

**getResult(job_id: str) → TranscriptionResult**
- Gets transcription status/results
- Returns: Object with `status`, `result`, `error_code` fields

**getResults(query: ListResultsQuery) → ResultsPage**
- Lists recent transcription jobs
- Returns: Object with `items` array

**deleteResult(job_id: str) → None**
- Deletes transcription job

#### Models

**TranscriptionRequest**
```python
from gladiapp.v2.rest_models import TranscriptionRequest

request = TranscriptionRequest(
    audio_url="https://api.gladia.io/file/...",
    # Optional parameters:
    # language="en",
    # language_behaviour="automatic",
    # transcription_hint="",
    # translation=True,
    # translation_config={"target_languages": ["fr", "es"]},
    # summarization=True,
    # chapterization=True
)
```

**TranscriptionResult**
- `status`: "queued" | "processing" | "done" | "error"
- `result.transcription.full_transcript`: Complete text
- `result.transcription.utterances[]`: Array of speech segments
- `result.transcription.utterances[].words[]`: Word-level timing
- `result.metadata`: Processing info (duration, billing time)

#### Example

```python
from gladiapp.v2 import GladiaRestClient
from gladiapp.v2.rest_models import TranscriptionRequest

client = GladiaRestClient(api_key)

# Upload and transcribe
upload = client.upload("audio.wav")
request = TranscriptionRequest(audio_url=upload.audio_url)
job = client.preRecorded(request)

# Wait for completion
while True:
    result = client.getResult(job.id)
    if result.status == "done":
        print(result.result.transcription.full_transcript)
        break
    time.sleep(3)
```

## WebSocket API

### GladiaWebsocketClient

Client for real-time transcription streaming.

```python
client = GladiaWebsocketClient(api_key)
```

#### Methods

**connect(config: InitializeSessionRequest) → GladiaWebsocketClientSession**
- Creates WebSocket session
- Returns: Session object for streaming

**getResult(session_id: str) → TranscriptionResult**
- Gets final transcription result
- Same format as REST API result

**deleteResult(session_id: str) → None**
- Cleans up session

### GladiaWebsocketClientSession

Active WebSocket session for audio streaming.

#### Methods

**getSessionInfo() → dict**
- Returns session metadata (id, url)

**connectAndStart() → bool**
- Establishes WebSocket connection
- Returns: Success status

**sendAudioBinary(data: bytes, size: int) → None**
- Streams audio chunk

**sendStopSignal() → None**
- Signals end of audio stream

#### Callbacks

**setOnConnectedCallback(callback: callable)**
**setOnDisconnectedCallback(callback: callable)**
**setOnErrorCallback(callback: callable)**
**setOnTranscriptCallback(callback: callable)**
- Handles partial transcripts during streaming

**setOnFinalTranscriptCallback(callback: callable)**
- Handles final transcription result

#### Configuration

**InitializeSessionRequest**
```python
from gladiapp.v2.ws import InitializeSessionRequest

config = InitializeSessionRequest(
    encoding="wav_pcm",           # Audio format
    bit_depth=16,                # Bits per sample
    sample_rate=16000,           # Hz
    channels=1,                  # Mono/stereo
    endpointing=1.5,             # Silence detection (seconds)
    maximum_duration_without_endpointing=45, # Max processing time
    messages_config={
        "receive_final_transcripts": True,
        "receive_partial_transcripts": True,  # Real-time results
        "receive_speech_events": False,
        "receive_lifecycle_events": False,
    }
)
```

#### Example

```python
import wave
from gladiapp.v2 import GladiaWebsocketClient
from gladiapp.v2.ws import InitializeSessionRequest

# Load audio
with wave.open("audio.wav", "rb") as w:
    audio_data = w.readframes(w.getnframes())

# Configure session
client = GladiaWebsocketClient(api_key)
config = InitializeSessionRequest(
    encoding="wav_pcm", bit_depth=16, sample_rate=16000, channels=1,
    messages_config={"receive_final_transcripts": True, "receive_partial_transcripts": True}
)

# Set up callbacks
session = client.connect(config)
session.setOnTranscriptCallback(lambda data: print(f"Partial: {data['data']['utterance']['text']}"))
session.setOnFinalTranscriptCallback(lambda data: print("Final transcript received"))

# Stream audio
if session.connectAndStart():
    chunk_size = 8000
    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i:i + chunk_size]
        session.sendAudioBinary(chunk, len(chunk))
        time.sleep(0.1)
    
    session.sendStopSignal()
    
    # Get final result
    result = client.getResult(session.getSessionInfo()["id"])
    print(result.result.transcription.full_transcript)
```

## Error Handling

```python
from gladiapp.v2 import TranscriptionError

try:
    result = client.getResult(job_id)
    if result.status == "error":
        print(f"Transcription failed: {result.error_code}")
except TranscriptionError as e:
    print(f"API error: {e}")
```

## Data Models

### Transcription Structure
```python
{
    "full_transcript": "Complete transcribed text",
    "languages": ["en"],
    "utterances": [
        {
            "text": "Segment text",
            "start": 0.34,    # seconds
            "end": 2.15,      # seconds
            "confidence": 0.95,
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

### Metadata
```python
{
    "audio_duration": 11.2,        # seconds
    "transcription_time": 3.4,     # processing time
    "billing_time": 11.2,          # billable duration
    "number_of_distinct_channels": 1
}
```

## Environment Setup

```bash
export GLADIA_API_KEY="your-api-key-here"
```

Or use a `.env` file:
```
GLADIA_API_KEY=your-api-key-here
```