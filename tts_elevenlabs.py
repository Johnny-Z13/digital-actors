"""
ElevenLabs Text-to-Speech Integration

Provides voice synthesis for NPC characters using ElevenLabs API.
Audio is streamed back to the client alongside text for synchronized playback.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
from io import BytesIO
from typing import TYPE_CHECKING, Any, Optional

from dotenv import load_dotenv

# Import emotion processing modules
from emotion_extractor import EmotionExtractor
from emotion_engine import EmotionEngine

load_dotenv()

logger = logging.getLogger(__name__)

# Check if ElevenLabs is available
ELEVENLABS_AVAILABLE = False
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

if ELEVENLABS_API_KEY and ELEVENLABS_API_KEY != "your-elevenlabs-api-key-here":
    try:
        from elevenlabs.client import ElevenLabs
        ELEVENLABS_AVAILABLE = True
        logger.info("ElevenLabs TTS enabled")
    except ImportError:
        logger.warning("ElevenLabs package not installed. Run: pip install elevenlabs")
else:
    logger.info("ElevenLabs TTS disabled (no API key configured)")


# Default voice IDs for each character
# These can be overridden via environment variables
DEFAULT_VOICE_IDS = {
    # Rachel - calm, professional female voice
    "eliza": os.getenv("ELEVENLABS_VOICE_ELIZA", "21m00Tcm4TlvDq8ikWAM"),
    # Adam - deep, authoritative male voice (good for engineer)
    "engineer": os.getenv("ELEVENLABS_VOICE_ENGINEER", "pNInz6obpgDQGcFmaJgB"),
    # Clyde - older, wise male voice (good for wizard)
    "wizard": os.getenv("ELEVENLABS_VOICE_WIZARD", "2EiwWnXFnvU5JabPnv8n"),
    # Arnold - gruff male voice (good for detective)
    "detective": os.getenv("ELEVENLABS_VOICE_DETECTIVE", "VR6AewLTigWG4xSOukaG"),
    # Default fallback voice
    "default": os.getenv("ELEVENLABS_VOICE_DEFAULT", "21m00Tcm4TlvDq8ikWAM"),
}

# Voice settings per character for personality
VOICE_SETTINGS = {
    "eliza": {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True,
    },
    "engineer": {
        "stability": 0.4,  # Slightly less stable for stress/emotion
        "similarity_boost": 0.8,
        "style": 0.2,  # Some style variation for urgency
        "use_speaker_boost": True,
    },
    "wizard": {
        "stability": 0.7,  # More stable, measured speech
        "similarity_boost": 0.6,
        "style": 0.1,
        "use_speaker_boost": True,
    },
    "detective": {
        "stability": 0.5,
        "similarity_boost": 0.7,
        "style": 0.15,
        "use_speaker_boost": True,
    },
    "default": {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True,
    },
}


class TTSManager:
    """Manages text-to-speech synthesis using ElevenLabs."""

    def __init__(self):
        self.client = None
        self.enabled = False
        self.emotion_extractor = EmotionExtractor()
        self.emotion_engine = EmotionEngine()

        if ELEVENLABS_AVAILABLE:
            try:
                self.client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
                self.enabled = True
                logger.info("TTSManager initialized with ElevenLabs and emotion processing")
            except Exception as e:
                logger.error("Failed to initialize ElevenLabs client: %s", e)

    def is_enabled(self) -> bool:
        """Check if TTS is available and enabled."""
        return self.enabled and self.client is not None

    def get_voice_id(self, character_id: str) -> str:
        """Get the ElevenLabs voice ID for a character."""
        return DEFAULT_VOICE_IDS.get(character_id, DEFAULT_VOICE_IDS["default"])

    def _get_base_voice_settings(self, character_id: str) -> dict[str, Any]:
        """
        Get base voice settings for a character (before emotion adjustments).

        Returns the character's default voice parameters which will be modified
        by the emotion engine based on emotional cues, phase, and character style.
        """
        return VOICE_SETTINGS.get(character_id, VOICE_SETTINGS["default"]).copy()

    def clean_text_for_tts(self, text: str) -> str:
        """
        Clean text for TTS, handling voice annotations.

        Converts annotations like [static] into SSML-like pauses or removes them,
        and cleans up text for natural speech.
        """
        # Remove or convert voice annotations
        # [static], [crackle] -> short pause
        text = re.sub(r'\[static[^\]]*\]', '...', text, flags=re.IGNORECASE)
        text = re.sub(r'\[crackle[^\]]*\]', '...', text, flags=re.IGNORECASE)

        # [breathing heavily], [breath] -> natural pause
        text = re.sub(r'\[breath[^\]]*\]', '...', text, flags=re.IGNORECASE)

        # [voice cracks], [voice breaks] -> keep as pause, voice will naturally vary
        text = re.sub(r'\[voice [^\]]*\]', '...', text, flags=re.IGNORECASE)

        # [pause], [silence] -> pause
        text = re.sub(r'\[pause[^\]]*\]', '...', text, flags=re.IGNORECASE)
        text = re.sub(r'\[silence[^\]]*\]', '...', text, flags=re.IGNORECASE)

        # [whisper] -> keep text but could adjust in future with SSML
        text = re.sub(r'\[whisper[^\]]*\]', '', text, flags=re.IGNORECASE)

        # [alarm], [warning], [signal lost] -> remove (these are SFX, not speech)
        text = re.sub(r'\[alarm[^\]]*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[warning[^\]]*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[signal[^\]]*\]', '', text, flags=re.IGNORECASE)

        # Remove any remaining bracketed annotations
        text = re.sub(r'\[[^\]]+\]', '', text)

        # Clean up multiple spaces and ellipses
        text = re.sub(r'\.{4,}', '...', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    async def synthesize_speech(
        self,
        text: str,
        character_id: str = "default",
        emotion_context: Optional[str] = None,
        scene_phase: Optional[int] = None,
        scene_type: Optional[str] = None,
    ) -> bytes | None:
        """
        Synthesize speech for the given text with emotional expression.

        Args:
            text: The text to convert to speech
            character_id: Character ID for voice selection
            emotion_context: Optional legacy emotional context (e.g., "panicked", "calm")
            scene_phase: Current scene phase (1-4) for phase-aware modulation
            scene_type: Scene type identifier for phase configuration

        Returns:
            Audio bytes (MP3 format) or None if TTS is disabled/failed
        """
        if not self.is_enabled():
            return None

        # Extract emotional cues BEFORE cleaning
        cleaned_text, emotional_cues = self.emotion_extractor.extract_cues(text)

        # If no extracted cues, fall back to emotion_context (backward compatible)
        if not emotional_cues and emotion_context:
            emotional_cues = [emotion_context]

        if not cleaned_text or len(cleaned_text) < 2:
            logger.debug("Text too short for TTS after cleaning: '%s'", text)
            return None

        # Get voice ID and base settings
        voice_id = self.get_voice_id(character_id)
        base_settings = self._get_base_voice_settings(character_id)

        # Generate emotion profile if we have cues
        settings = base_settings
        if emotional_cues:
            try:
                # Categorize cues
                categorized_cues = [
                    self.emotion_extractor.categorize_cue(cue)
                    for cue in emotional_cues
                ]

                # Analyze cues and generate emotion profile
                emotion_profile = self.emotion_engine.analyze_cues(categorized_cues)

                # Apply phase context if available
                if scene_phase is not None and scene_type:
                    emotion_profile = self.emotion_engine.apply_phase_context(
                        emotion_profile, scene_phase, scene_type
                    )

                # Apply character-specific emotion style
                from characters import CHARACTERS
                character = CHARACTERS.get(character_id)
                if character:
                    emotion_profile = self.emotion_engine.apply_character_style(
                        emotion_profile, character
                    )

                # Generate final voice parameters from emotion profile
                settings = self.emotion_engine.get_voice_parameters(
                    emotion_profile, base_settings
                )

                logger.debug(
                    "Emotion processing: %s (intensity %.2f) -> stability=%.2f, style=%.2f",
                    emotion_profile.primary_emotion,
                    emotion_profile.intensity,
                    settings['stability'],
                    settings['style']
                )

            except Exception as e:
                logger.warning("Emotion processing failed, using base settings: %s", e)
                settings = base_settings

        try:
            # Run synthesis in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            audio_bytes = await loop.run_in_executor(
                None,
                self._sync_synthesize,
                cleaned_text,
                voice_id,
                settings,
            )
            return audio_bytes

        except Exception as e:
            logger.error("TTS synthesis failed: %s", e)
            return None

    def _sync_synthesize(
        self,
        text: str,
        voice_id: str,
        settings: dict[str, Any],
    ) -> bytes:
        """Synchronous synthesis (run in thread pool)."""
        from elevenlabs import VoiceSettings

        voice_settings = VoiceSettings(
            stability=settings.get("stability", 0.5),
            similarity_boost=settings.get("similarity_boost", 0.75),
            style=settings.get("style", 0.0),
            use_speaker_boost=settings.get("use_speaker_boost", True),
        )

        # Use streaming to get audio chunks
        response = self.client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_turbo_v2_5",  # Fast, good quality
            output_format="mp3_44100_128",  # Good quality MP3
            voice_settings=voice_settings,
        )

        # Collect audio bytes
        audio_buffer = BytesIO()
        for chunk in response:
            if chunk:
                audio_buffer.write(chunk)

        audio_buffer.seek(0)
        return audio_buffer.read()

    async def synthesize_speech_base64(
        self,
        text: str,
        character_id: str = "default",
        emotion_context: Optional[str] = None,
        scene_phase: Optional[int] = None,
        scene_type: Optional[str] = None,
    ) -> str | None:
        """
        Synthesize speech and return as base64-encoded string.

        This is convenient for sending audio over WebSocket to the browser.

        Returns:
            Base64-encoded audio string or None if TTS is disabled/failed
        """
        audio_bytes = await self.synthesize_speech(
            text,
            character_id,
            emotion_context,
            scene_phase,
            scene_type
        )

        if audio_bytes:
            return base64.b64encode(audio_bytes).decode("utf-8")
        return None


# Global TTS manager instance
_tts_manager: TTSManager | None = None


def get_tts_manager() -> TTSManager:
    """Get the global TTS manager instance."""
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSManager()
    return _tts_manager


async def synthesize_npc_speech(
    text: str,
    character_id: str,
    emotion_context: Optional[str] = None,
    scene_phase: Optional[int] = None,
    scene_type: Optional[str] = None,
) -> str | None:
    """
    Convenience function to synthesize NPC speech.

    Args:
        text: The dialogue text
        character_id: The character speaking
        emotion_context: Optional legacy emotional context
        scene_phase: Optional scene phase (1-4)
        scene_type: Optional scene type identifier

    Returns:
        Base64-encoded audio or None
    """
    manager = get_tts_manager()
    return await manager.synthesize_speech_base64(
        text,
        character_id,
        emotion_context,
        scene_phase,
        scene_type
    )
