# Audio Module

This directory will contain audio processing functionality for future voice integration.

## Planned Structure

```
audio/
├── __init__.py
├── tts.py          # Text-to-speech providers (ElevenLabs, Kokoro, etc.)
├── stt.py          # Speech-to-text providers (Whisper, etc.)
├── cache.py        # Audio caching system
└── processors.py   # Audio processing utilities
```

## Future Features

### Text-to-Speech (TTS)
- Multiple provider support (ElevenLabs, Kokoro, Azure, etc.)
- Voice caching to reduce API calls
- Character-specific voice mappings
- Real-time audio streaming

### Speech-to-Text (STT)
- Multiple provider support (Whisper, Google, Azure, etc.)
- Real-time transcription
- Wake word detection
- Noise filtering

## Integration with Web Interface

The web interface will be extended to support:
1. **Voice input** - Click microphone button to speak
2. **Voice output** - Character responses played as audio
3. **Voice settings** - Choose character voice, speed, pitch
4. **Push-to-talk** - Press key to activate voice input

## Existing Files

The legacy TTS files (`cachedvoiceclient.py`, `ttsprovider.py`) from the game integration
are preserved in `legacy_files/` for reference but will be refactored for the new system.
