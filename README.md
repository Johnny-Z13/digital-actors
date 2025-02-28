# antdemo-server
Websocket server for Project Ant Online Demo (with optional local text-to-speech)

## Running

If you have `uv` [installed](https://github.com/astral-sh/uv), you can simply clone the repo and run:
```bash
uv run websocket.py
```

Otherwise, you can do:
```bash
pip install -r requirements.txt
python websocket.py
```

To run local models on GPU, install the PyTorch version that matches your CUDA toolkit version, eg:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

Check you installed CUDA toolkit version with:
```bash
nvcc --version  # If CUDA toolkit is installed
```
or
```bash
nvidia-smi  # To check the CUDA version supported by your GPU driver
```

## Implementation

The brains are implemented in `ant_server.py`, which defines how to handle messages from the game. You should implement `on_event_triggered` and `on_user_transcript` here.

Generating audio is handled by `cachedvoiceclient.py`, which interfaces with the ElevenLabs API or local text-to-speech (Kokoro). This file can also be run directly to test Kokoro (see https://huggingface.co/hexgrad/Kokoro-82M)

Switch between text-to-speech providers, ElevenLabs or Kokoro, at the top of websocket.py:

`voice_client = CachedVoiceClient(None, None, None, tts_provider="kokoro")`

