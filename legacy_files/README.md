# Legacy Files

This directory contains files from the original Unity/Unreal game integration system.

These files are **archived** and no longer used by the web interface, but are preserved for reference.

## Archived Files

### Game Integration
- **`websocket.py`** - WebSocket server for game clients (Unity/Unreal)
- **`ant_server.py`** - HTTP server wrapper for game integration
- **`protocol.py`** - Game communication protocol definitions
- **`start.sh`** - Startup script for WebSocket game server
- **`start-http.sh`** - Startup script for HTTP game server

### Audio/TTS
- **`cachedvoiceclient.py`** - TTS voice client with caching (ElevenLabs/Kokoro)
- **`ttsprovider.py`** - TTS provider interface

### Game-Specific Content
- **`project_one_demo/`** - Original game-specific dialogue system and prompts
- **`qa_research/`** - Research and testing code
- **`murrays_work/`** - Research data and experiments

## Why Archived?

The system has been refactored to focus on the web interface:
- **Web-first approach** - Browser-based chat is now the primary interface
- **Modular design** - Characters and scenes are now in separate modules
- **Simpler architecture** - No need for game engine protocol complexity

## If You Need Game Integration

If you need to connect Unity/Unreal game clients again:

1. **Option A: Use the web interface** - Embed the web chat in your game using a WebView
2. **Option B: Restore game integration** - Copy these files back and integrate with the new modular system

## Legacy System Architecture

```
Game Client (Unity/Unreal)
    ↓ WebSocket
websocket.py / ant_server.py
    ↓
project_one_demo/generate_project1_dialogue.py
    ↓
Claude API
```

## New System Architecture

```
Web Browser
    ↓ WebSocket
web_server.py
    ↓
characters/ + scenes/ (modular)
    ↓
llm_prompt_core/
    ↓
Claude API
```

## TTS Integration Note

The TTS files (`cachedvoiceclient.py`, `ttsprovider.py`) will be refactored and moved to the `audio/` module when voice features are added to the web interface.

---

**These files are kept for reference only and are not maintained.**

For the current system, see the main [README.md](../README.md).
