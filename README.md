# antdemo-server
Websocket server for Project Ant Online Demo

## Running

If you have `uv` [installed](https://github.com/astral-sh/uv), you can simply clone the repo and run:
```bash
uv run websocket.py
```

Otherwise, you can do:
```bash
pip install -U websockets rich
python websocket.py
```

## Implementation

The brains are implemented in `ant_server.py`, which defines how to handle messages from the game. You should implement `on_event_triggered` and `on_user_transcript` here.

Generating audio is handled by `cachedvoiceclient.py`, which interfaces with the ElevenLabs API
