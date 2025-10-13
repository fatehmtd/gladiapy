# gladiapy

Python client for the Gladia speech-to-text API. Supports both REST and WebSocket transcription.

## Features

- REST API for batch transcription jobs
- WebSocket API for real-time streaming transcription  
- Type-safe models with Pydantic
- Word-level timing and confidence scores
- Multi-language support with translation

## Installation

### From PyPI (when published)
```bash
pip install gladiapy
```

### From Source
```bash
git clone https://github.com/fatehmtd/gladiapp.git
cd gladiapp
pip install -e .
```

### From GitHub Releases
Download the `.whl` file from [releases](https://github.com/fatehmtd/gladiapp/releases) and install:
```bash
pip install gladiapy-0.1.0-py3-none-any.whl
```

## Quick Start

```python
import os
from gladiapp.v2 import GladiaRestClient
from gladiapp.v2.rest_models import TranscriptionRequest

client = GladiaRestClient(os.getenv("GLADIA_API_KEY"))

# Upload and transcribe
upload = client.upload("audio.wav")
request = TranscriptionRequest(audio_url=upload.audio_url)
job = client.preRecorded(request)

# Get results
result = client.getResult(job.id)
print(result.result.transcription.full_transcript)
```

## Setup

```bash
export GLADIA_API_KEY="your-api-key"
```

## Documentation

See [API.md](API.md) for complete API reference and examples.

## Examples

Run the included examples:

```bash
# REST API batch transcription
python examples/rest_example.py

# WebSocket real-time transcription  
python examples/ws_example.py
```

## Requirements

Python 3.9+ with requests, websocket-client, pydantic, and python-dotenv.