# gladiapy

Python client library for the Gladia speech-to-text API. Provides synchronous REST API access and asynchronous WebSocket streaming for audio transcription with advanced features including translation, summarization, sentiment analysis, and named entity recognition.

## Features

- REST API client for batch audio transcription jobs
- WebSocket client for real-time streaming transcription
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
import os
from gladiapy.v2 import GladiaRestClient, GladiaError
from gladiapy.v2.rest_models import TranscriptionRequest

client = GladiaRestClient(os.getenv("GLADIA_API_KEY"))

try:
    # Upload audio file
    upload_result = client.upload("audio.wav")
    
    # Create transcription request
    request = TranscriptionRequest(audio_url=upload_result.audio_url)
    job = client.pre_recorded(request)

    # Poll for completion
    while True:
        result = client.get_result(job.id)
        if result.status == "done":
            print(result.result.transcription.full_transcript)
            break
        elif result.status == "error":
            print(f"Transcription failed: {result.error_code}")
            break
        time.sleep(3)
        
    # Clean up
    client.delete_result(job.id)
    
except GladiaError as e:
    print(f"API error [{e.status_code}]: {e.message}")
```

## Configuration

Set your Gladia API key as an environment variable:

```bash
export GLADIA_API_KEY="your-api-key"
```

## Examples

The library includes comprehensive examples demonstrating all features:

```bash
# Basic REST API transcription
python examples/rest_example.py

# Real-time WebSocket transcription
python examples/ws_example.py

# Advanced processing features
python examples/sentiment_analysis_example.py
python examples/summarization_example.py
python examples/chapterization_example.py
python examples/named_entity_recognition_example.py
python examples/translation_example.py

# WebSocket with advanced features
python examples/websocket_sentiment_example.py
python examples/websocket_translation_example.py

# Additional capabilities
python examples/speaker_diarization_example.py
python examples/subtitles_example.py
python examples/custom_vocabulary_example.py
```

## API Reference

Complete API documentation and usage examples are available in [API.md](API.md).

## Requirements

- Python 3.9 or higher
- Dependencies: requests, websocket-client, pydantic

## License

See LICENSE file for terms and conditions.