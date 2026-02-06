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
from typing import Any

from dotenv import load_dotenv

from emotion_engine import EmotionEngine

# Import emotion processing modules
from emotion_extractor import EmotionExtractor

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
    # Harry - British male, older, measured (perfect for Captain Hale)
    "captain_hale": os.getenv("ELEVENLABS_VOICE_CAPTAIN_HALE", "SOYHLrjzK2X1ezoPC6cr"),
    # Rachel - friendly, helpful (good for Clippy assistant)
    "clippy": os.getenv("ELEVENLABS_VOICE_CLIPPY", "21m00Tcm4TlvDq8ikWAM"),
    # Adam - same as engineer (Kovich is also submarine officer)
    "kovich": os.getenv("ELEVENLABS_VOICE_KOVICH", "pNInz6obpgDQGcFmaJgB"),
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
    "captain_hale": {
        "stability": 0.65,  # Calm, measured British captain
        "similarity_boost": 0.75,
        "style": 0.1,  # Slight style for character
        "use_speaker_boost": True,
    },
    "clippy": {
        "stability": 0.4,  # More animated, helpful assistant
        "similarity_boost": 0.8,
        "style": 0.3,  # More expressive style
        "use_speaker_boost": True,
    },
    "kovich": {
        "stability": 0.6,  # Controlled, deliberate British restraint
        "similarity_boost": 0.8,
        "style": 0.15,  # Subtle style for dry wit
        "use_speaker_boost": True,
    },
    "default": {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True,
    },
}

# ElevenLabs model configuration
# NOTE: Audio tags like [laughs], [sighs] ONLY work with v3 models!
ELEVENLABS_MODELS = {
    "eleven_v3": {
        "description": "V3 - Most expressive, supports audio tags",
        "supports_audio_tags": True,
    },
    "eleven_turbo_v2_5": {
        "description": "Fast, good quality, NO audio tag support",
        "supports_audio_tags": False,
    },
    "eleven_flash_v2_5": {
        "description": "Fastest, lower latency, NO audio tag support",
        "supports_audio_tags": False,
    },
    "eleven_multilingual_v2": {
        "description": "Multilingual, NO audio tag support",
        "supports_audio_tags": False,
    },
}
# Smart model selection: use v3 for audio tags, turbo for speed
DEFAULT_TTS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2_5")
AUDIO_TAG_MODEL = "eleven_v3"  # Use v3 when audio tags are present

# Feature flag for audio tag preservation (enabled by default)
PRESERVE_AUDIO_TAGS = os.getenv("ELEVENLABS_PRESERVE_AUDIO_TAGS", "true").lower() == "true"

# Audio tags that ElevenLabs can vocalize natively
# These will be preserved in the text sent to the API
# IMPORTANT: Include both singular and plural forms for flexibility
ELEVENLABS_AUDIO_TAGS = {
    # Laughter variations
    "laugh",
    "laughs",
    "laughing",
    "giggle",
    "giggles",
    "giggling",
    "chuckle",
    "chuckles",
    "chuckling",
    # Sighing
    "sigh",
    "sighs",
    "sighing",
    # Coughing/clearing (singular AND plural)
    "cough",
    "coughs",
    "coughing",
    "clears throat",
    "clearing throat",
    # Gasping/breathing
    "gasp",
    "gasps",
    "gasping",
    "exhale",
    "exhales",
    "inhale",
    "inhales",
    # Crying/emotion
    "cry",
    "crying",
    "sob",
    "sobbing",
    "sniffle",
    "sniffling",
    "sobs",
    # Speech style modifiers
    "whisper",
    "whispers",
    "whispering",
    "shout",
    "shouts",
    "shouting",
    "yell",
    "yells",
    "yelling",
    # Emotional states (ElevenLabs can interpret these)
    "sad",
    "angry",
    "excited",
    "happy",
    "nervous",
    "scared",
    # Groans/grunts (singular AND plural)
    "groan",
    "groans",
    "groaning",
    "grunt",
    "grunts",
    "grunting",
    # Death sounds (for all actors)
    "ugh",
    "argh",
    "gagging",
    "choking",
    "wheeze",
    "wheezing",
    "death rattle",
    "final breath",
    "dying breath",
}

# Tags that should become pauses (SFX, environmental, non-vocal)
PAUSE_TAGS = {
    "static",
    "crackle",
    "crackling",
    "alarm",
    "warning",
    "pause",
    "silence",
    "long pause",
    "beat",
    "signal lost",
    "signal",
    "radio static",
}

# Tags that should be removed entirely (non-vocal actions, stage directions)
REMOVE_TAGS = {
    "nods",
    "nodding",
    "shakes head",
    "looks away",
    "looks up",
    "looks down",
    "eyes twinkling",
    "smiles",
    "smiling",
    "frowns",
    "frowning",
    "gestures",
    "points",
    "waves",
    "turns",
    "stands",
    "sits",
    "walks",
    "steps",
    "moves",
    "reaches",
    "grabs",
    "holds",
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

    def _text_has_audio_tags(self, text: str) -> bool:
        """Check if text contains ElevenLabs-performable audio tags."""
        text_lower = text.lower()
        for tag in ELEVENLABS_AUDIO_TAGS:
            if f"[{tag}]" in text_lower or f"[{tag} " in text_lower:
                return True
        return False

    def _select_model_for_text(self, text: str) -> str:
        """Select the best model based on text content.

        Uses v3 when audio tags are present (for vocalization),
        otherwise uses the faster turbo model.
        """
        if PRESERVE_AUDIO_TAGS and self._text_has_audio_tags(text):
            logger.debug("Audio tags detected, using v3 model")
            return AUDIO_TAG_MODEL
        return DEFAULT_TTS_MODEL

    def clean_text_for_tts(self, text: str, preserve_audio_tags: bool = None) -> str:
        """
        Clean text for TTS, handling voice annotations.

        Converts annotations like [static] into pauses, removes non-vocal actions,
        and optionally preserves ElevenLabs-performable audio tags.

        Args:
            text: Raw text with bracketed annotations
            preserve_audio_tags: If True, keep ElevenLabs-vocalizeable tags like [laughs], [sighs].
                                If None, uses PRESERVE_AUDIO_TAGS env var setting.

        Returns:
            Cleaned text ready for TTS synthesis
        """
        if preserve_audio_tags is None:
            preserve_audio_tags = PRESERVE_AUDIO_TAGS

        def process_bracket(match: re.Match) -> str:
            """Process a single bracketed annotation."""
            content = match.group(1).lower().strip()

            # Check if this is a pause/SFX tag
            for pause_tag in PAUSE_TAGS:
                if pause_tag in content:
                    return "..."

            # Check if this is a removable action tag
            for remove_tag in REMOVE_TAGS:
                if remove_tag in content:
                    return ""

            # Check if this is a performable audio tag (and we want to preserve them)
            if preserve_audio_tags:
                for audio_tag in ELEVENLABS_AUDIO_TAGS:
                    if audio_tag in content:
                        # Return the tag as-is for ElevenLabs to vocalize
                        return match.group(0)

            # Default: remove unrecognized brackets
            return ""

        # Process all bracketed content
        text = re.sub(r"\[([^\]]+)\]", process_bracket, text)

        # Clean up multiple spaces and ellipses
        text = re.sub(r"\.{4,}", "...", text)
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text

    async def synthesize_speech(
        self,
        text: str,
        character_id: str = "default",
        emotion_context: str | None = None,
        scene_phase: int | None = None,
        scene_type: str | None = None,
        tts_mode: str = "expressive",
    ) -> bytes | None:
        """
        Synthesize speech for the given text with emotional expression.

        Args:
            text: The text to convert to speech
            character_id: Character ID for voice selection
            emotion_context: Optional legacy emotional context (e.g., "panicked", "calm")
            scene_phase: Current scene phase (1-4) for phase-aware modulation
            scene_type: Scene type identifier for phase configuration
            tts_mode: 'expressive' (v3 + audio tags) or 'fast' (turbo)

        Returns:
            Audio bytes (MP3 format) or None if TTS is disabled/failed
        """
        if not self.is_enabled():
            return None

        # Extract emotional cues for emotion analysis (used for voice params)
        _, emotional_cues = self.emotion_extractor.extract_cues(text)

        # Clean text for TTS (preserves performable audio tags if enabled)
        tts_text = self.clean_text_for_tts(text)

        # If no extracted cues, fall back to emotion_context (backward compatible)
        if not emotional_cues and emotion_context:
            emotional_cues = [emotion_context]

        if not tts_text or len(tts_text) < 2:
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
                    self.emotion_extractor.categorize_cue(cue) for cue in emotional_cues
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
                settings = self.emotion_engine.get_voice_parameters(emotion_profile, base_settings)

                logger.debug(
                    "Emotion processing: %s (intensity %.2f) -> stability=%.2f, style=%.2f",
                    emotion_profile.primary_emotion,
                    emotion_profile.intensity,
                    settings["stability"],
                    settings["style"],
                )

            except Exception as e:
                logger.warning("Emotion processing failed, using base settings: %s", e)
                settings = base_settings

        # Select model based on tts_mode setting
        if tts_mode == "fast":
            # Fast mode: always use turbo, strip audio tags
            settings["model_id"] = DEFAULT_TTS_MODEL
            # Re-clean text without preserving audio tags for fast mode
            tts_text = self.clean_text_for_tts(text, preserve_audio_tags=False)
        else:
            # Expressive mode: use v3 for audio tags, turbo otherwise
            settings["model_id"] = self._select_model_for_text(tts_text)

        try:
            # Run synthesis in thread pool to avoid blocking
            import time
            from metrics import tts_latency_seconds, track_error

            start_time = time.time()
            loop = asyncio.get_event_loop()
            audio_bytes = await loop.run_in_executor(
                None,
                self._sync_synthesize,
                tts_text,
                voice_id,
                settings,
            )

            # Track TTS latency
            duration = time.time() - start_time
            tts_latency_seconds.observe(duration)

            return audio_bytes

        except Exception as e:
            logger.error("TTS synthesis failed: %s", e)
            # Track TTS error
            from metrics import track_error
            track_error("tts_synthesis_error")
            return None

    def _sync_synthesize(
        self,
        text: str,
        voice_id: str,
        settings: dict[str, Any],
    ) -> bytes:
        """Synchronous synthesis (run in thread pool)."""
        from elevenlabs import VoiceSettings

        # Use model from settings or default
        model_id = settings.get("model_id", DEFAULT_TTS_MODEL)

        # Get stability value
        stability = settings.get("stability", 0.5)

        # V3 models only accept specific stability values: 0.0, 0.5, 1.0
        if model_id.startswith("eleven_v3") or model_id == "eleven_v3":
            # Snap to nearest valid v3 stability value
            if stability <= 0.25:
                stability = 0.0  # Creative
            elif stability <= 0.75:
                stability = 0.5  # Natural
            else:
                stability = 1.0  # Robust

        voice_settings = VoiceSettings(
            stability=stability,
            similarity_boost=settings.get("similarity_boost", 0.75),
            style=settings.get("style", 0.0),
            use_speaker_boost=settings.get("use_speaker_boost", True),
        )

        # Use streaming to get audio chunks
        response = self.client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
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
        emotion_context: str | None = None,
        scene_phase: int | None = None,
        scene_type: str | None = None,
        tts_mode: str = "expressive",
    ) -> str | None:
        """
        Synthesize speech and return as base64-encoded string.

        This is convenient for sending audio over WebSocket to the browser.

        Returns:
            Base64-encoded audio string or None if TTS is disabled/failed
        """
        audio_bytes = await self.synthesize_speech(
            text, character_id, emotion_context, scene_phase, scene_type, tts_mode
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
    emotion_context: str | None = None,
    scene_phase: int | None = None,
    scene_type: str | None = None,
    tts_mode: str = "expressive",
) -> str | None:
    """
    Convenience function to synthesize NPC speech.

    Args:
        text: The dialogue text
        character_id: The character speaking
        emotion_context: Optional legacy emotional context
        scene_phase: Optional scene phase (1-4)
        scene_type: Optional scene type identifier
        tts_mode: 'expressive' (v3 + audio tags) or 'fast' (turbo)

    Returns:
        Base64-encoded audio or None
    """
    manager = get_tts_manager()
    return await manager.synthesize_speech_base64(
        text, character_id, emotion_context, scene_phase, scene_type, tts_mode
    )
