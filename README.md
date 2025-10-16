# gladiapy

Python client library for the Gladia speech-to-text API. Provides synchronous REST API access and asynchronous WebSocket streaming for audio transcription with advanced features including translation, summarization, sentiment analysis, and named entity recognition.

## Features

- REST API client for batch audio transcription jobs
- WebSocket client for real-time streaming transcription with typed callbacks (Pydantic models)
- Advanced processing features: translation, summarization, chapterization, sentiment analysis, named entity recognition
- Type-safe data models using Pydantic
- Word-level timing information and confidence scores
- Multi-language support with automatic language detection
- Custom vocabulary and speaker diarization
- Subtitle generation

## Installation

### From Source

```bash
git clone https://github.com/fatehmtd/gladiapy.git
cd gladiapy
pip install -e .
```

## Quick Start

```python
import os, time
from gladiapy.v2 import GladiaRestClient, GladiaError
from gladiapy.v2.rest_models import TranscriptionRequest

client = GladiaRestClient(os.getenv("GLADIA_API_KEY"))

try:
    upload_result = client.upload("audio.wav")
    request = TranscriptionRequest(audio_url=upload_result.audio_url)
    job = client.pre_recorded(request)

    while True:
        result = client.get_result(job.id)
        if result.status == "done":
            print(result.result.transcription.full_transcript)
            break
        elif result.status == "error":
            print(f"Transcription failed: {result.error_code}")
            break
        time.sleep(3)

    client.delete_result(job.id)

except GladiaError as e:
    print(f"API error [{e.status_code}]: {e.message}")
```

### WebSocket quick start

```python
import os, time, wave
from gladiapy.v2 import GladiaWebsocketClient
from gladiapy.v2.ws import InitializeSessionRequest
from gladiapy.v2.ws_models import Transcript, FinalTranscript

audio = wave.open("audio.wav", "rb").readframes(10_000)
client = GladiaWebsocketClient(os.getenv("GLADIA_API_KEY"))

init = InitializeSessionRequest(
    encoding=InitializeSessionRequest.Encoding.WAV_PCM,
    bit_depth=InitializeSessionRequest.BitDepth.BIT_DEPTH_16,
    sample_rate=InitializeSessionRequest.SampleRate.SAMPLE_RATE_16000,
    channels=1,
    messages_config=InitializeSessionRequest.MessagesConfig(
        receive_partial_transcripts=True,
        receive_final_transcripts=True,
    ),
)

session = client.connect(init)

def on_partial(e: Transcript):
    print("Partial:", e.data.utterance.text)

def on_final(e: FinalTranscript):
    print("Final received!", bool(e.data.transcription))

session.set_on_transcript_callback(on_partial)
session.set_on_final_transcript_callback(on_final)

session.connect_and_start()
session.send_audio_binary(audio, len(audio))
time.sleep(0.2)
session.send_stop_signal()
```

## Configuration

Set your Gladia API key as an environment variable:

```bash
export GLADIA_API_KEY="your-api-key"
```

## Examples

The repository includes examples for all features:

```bash
# Basic REST API transcription
python -m examples.rest_example

# Real-time WebSocket transcription
python -m examples.ws_example

# Advanced processing (batch)
python -m examples.sentiment_analysis_example
python -m examples.summarization_example
python -m examples.chapterization_example
python -m examples.named_entity_recognition_example
python -m examples.translation_example

# WebSocket with advanced features
python -m examples.websocket_sentiment_example
python -m examples.websocket_translation_example

# Additional capabilities
python -m examples.speaker_diarization_example
python -m examples.subtitles_example
python -m examples.custom_vocabulary_example
```

## API Reference

Complete API documentation and usage examples are available in [API.md](API.md).

## Requirements

- Python 3.9 or higher
- Dependencies: requests, websocket-client, pydantic

## License

See LICENSE file for terms and conditions.
