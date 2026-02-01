"""
Emotion Detection Engine

Converts extracted emotional cues into voice parameter recommendations for ElevenLabs TTS.
Handles emotion-to-parameter mapping, phase-aware modulation, and character-specific styles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from characters.base import Character


@dataclass
class EmotionProfile:
    """
    Structured representation of emotional state and its effect on voice parameters.

    Attributes:
        primary_emotion: Main emotion detected (e.g., "distress", "calm", "anger")
        intensity: Emotional intensity from 0.0 (subtle) to 1.0 (extreme)
        vocal_quality: Type of vocal expression ("normal", "strained", "whisper", "breaking")
        physical_state: Physical condition affecting speech ("normal", "coughing", "gasping")
        pacing: Speech pacing ("normal", "rushed", "slow", "hesitant")
        stability_modifier: Adjustment to voice stability parameter (-0.5 to +0.5)
        style_modifier: Expressiveness level (0.0 to 1.0)
        similarity_modifier: Adjustment to voice similarity (-0.3 to +0.3)
    """

    primary_emotion: str = "neutral"
    intensity: float = 0.5
    vocal_quality: str = "normal"
    physical_state: str = "normal"
    pacing: str = "normal"
    stability_modifier: float = 0.0
    style_modifier: float = 0.5
    similarity_modifier: float = 0.0


class EmotionEngine:
    """
    Converts emotional cues into voice parameters for ElevenLabs TTS.

    Handles:
    - Emotion-to-parameter mapping
    - Phase-aware voice modulation
    - Character-specific expression styles
    """

    # Emotion-to-parameter mapping rules
    EMOTION_PARAMETERS = {
        # Distress/Panic: High variation, very expressive, allow vocal distortion
        "distress": {
            "stability_modifier": -0.35,
            "style_modifier": 0.8,
            "similarity_modifier": -0.15,
        },
        "panic": {"stability_modifier": -0.4, "style_modifier": 0.9, "similarity_modifier": -0.2},
        "fear": {"stability_modifier": -0.3, "style_modifier": 0.75, "similarity_modifier": -0.1},
        "anxiety": {
            "stability_modifier": -0.25,
            "style_modifier": 0.7,
            "similarity_modifier": -0.05,
        },
        "stress": {"stability_modifier": -0.3, "style_modifier": 0.7, "similarity_modifier": -0.1},
        # Calm/Measured: Consistent, controlled, restrained expressiveness
        "calm": {"stability_modifier": 0.3, "style_modifier": 0.2, "similarity_modifier": 0.1},
        "relief": {"stability_modifier": 0.2, "style_modifier": 0.4, "similarity_modifier": 0.05},
        # Anger/Frustration: Moderate variation, controlled aggression
        "anger": {"stability_modifier": -0.2, "style_modifier": 0.7, "similarity_modifier": 0.0},
        "frustration": {
            "stability_modifier": -0.15,
            "style_modifier": 0.6,
            "similarity_modifier": 0.0,
        },
        # Sadness/Disappointment: Moderate variation, moderate expressiveness
        "sadness": {
            "stability_modifier": -0.2,
            "style_modifier": 0.6,
            "similarity_modifier": -0.05,
        },
        "disappointment": {
            "stability_modifier": -0.1,
            "style_modifier": 0.5,
            "similarity_modifier": 0.0,
        },
        # Joy/Excitement: High variation, high expressiveness
        "joy": {"stability_modifier": -0.1, "style_modifier": 0.8, "similarity_modifier": 0.0},
        "excitement": {
            "stability_modifier": -0.15,
            "style_modifier": 0.85,
            "similarity_modifier": 0.05,
        },
        # Other emotions
        "surprise": {
            "stability_modifier": -0.25,
            "style_modifier": 0.7,
            "similarity_modifier": 0.0,
        },
        "confusion": {
            "stability_modifier": -0.15,
            "style_modifier": 0.5,
            "similarity_modifier": 0.0,
        },
        "determination": {
            "stability_modifier": 0.15,
            "style_modifier": 0.6,
            "similarity_modifier": 0.05,
        },
        "contemplation": {
            "stability_modifier": 0.2,
            "style_modifier": 0.3,
            "similarity_modifier": 0.1,
        },
        "empathy": {"stability_modifier": 0.1, "style_modifier": 0.5, "similarity_modifier": 0.05},
        "warmth": {"stability_modifier": 0.15, "style_modifier": 0.5, "similarity_modifier": 0.1},
        "coldness": {
            "stability_modifier": 0.25,
            "style_modifier": 0.2,
            "similarity_modifier": 0.15,
        },
        "cynicism": {"stability_modifier": 0.2, "style_modifier": 0.4, "similarity_modifier": 0.1},
        "weariness": {"stability_modifier": 0.1, "style_modifier": 0.3, "similarity_modifier": 0.0},
    }

    # Vocal quality modifiers
    VOCAL_QUALITY_PARAMETERS = {
        "whisper": {"stability_modifier": 0.3, "style_modifier": 0.4, "similarity_modifier": -0.2},
        "breaking": {
            "stability_modifier": -0.4,
            "style_modifier": 0.9,
            "similarity_modifier": -0.15,
        },
        "strained": {
            "stability_modifier": -0.3,
            "style_modifier": 0.7,
            "similarity_modifier": -0.2,
        },
        "trembling": {
            "stability_modifier": -0.35,
            "style_modifier": 0.75,
            "similarity_modifier": -0.1,
        },
        "hoarse": {
            "stability_modifier": -0.15,
            "style_modifier": 0.6,
            "similarity_modifier": -0.25,
        },
        "shout": {"stability_modifier": -0.1, "style_modifier": 0.8, "similarity_modifier": 0.1},
    }

    # Physical state modifiers
    PHYSICAL_STATE_PARAMETERS = {
        "coughing": {
            "stability_modifier": -0.35,
            "style_modifier": 0.8,
            "similarity_modifier": -0.25,
        },
        "gasping": {
            "stability_modifier": -0.4,
            "style_modifier": 0.85,
            "similarity_modifier": -0.2,
        },
        "breathing_heavy": {
            "stability_modifier": -0.3,
            "style_modifier": 0.7,
            "similarity_modifier": -0.15,
        },
    }

    # Phase-based configurations for different scene types
    PHASE_CONFIGS = {
        "submarine": {
            1: {"baseline_intensity": 0.5, "stability_modifier": -0.1, "style_modifier": 0.2},
            2: {"baseline_intensity": 0.7, "stability_modifier": -0.2, "style_modifier": 0.3},
            3: {"baseline_intensity": 0.85, "stability_modifier": -0.3, "style_modifier": 0.4},
            4: {"baseline_intensity": 0.95, "stability_modifier": -0.4, "style_modifier": 0.5},
        },
        "crown_court": {
            1: {"baseline_intensity": 0.3, "stability_modifier": 0.2, "style_modifier": 0.0},
            2: {"baseline_intensity": 0.5, "stability_modifier": 0.1, "style_modifier": 0.1},
            3: {"baseline_intensity": 0.7, "stability_modifier": 0.0, "style_modifier": 0.3},
            4: {"baseline_intensity": 0.6, "stability_modifier": 0.15, "style_modifier": 0.2},
        },
        "default": {
            1: {"baseline_intensity": 0.5, "stability_modifier": 0.0, "style_modifier": 0.3},
            2: {"baseline_intensity": 0.6, "stability_modifier": 0.0, "style_modifier": 0.4},
            3: {"baseline_intensity": 0.7, "stability_modifier": 0.0, "style_modifier": 0.5},
            4: {"baseline_intensity": 0.7, "stability_modifier": 0.0, "style_modifier": 0.5},
        },
    }

    def __init__(self):
        """Initialize the emotion engine."""
        pass

    def analyze_cues(self, categorized_cues: list[dict[str, Any]]) -> EmotionProfile:
        """
        Analyze categorized emotional cues and generate an EmotionProfile.

        Args:
            categorized_cues: List of categorized cues from EmotionExtractor

        Returns:
            EmotionProfile with unified emotional state and parameter modifiers

        Example:
            >>> engine = EmotionEngine()
            >>> cues = [
            ...     {'category': 'physical', 'emotion': 'distress', 'intensity': 0.9},
            ...     {'category': 'vocal_quality', 'emotion': 'distress', 'intensity': 0.7}
            ... ]
            >>> profile = engine.analyze_cues(cues)
            >>> print(profile.primary_emotion)
            'distress'
        """
        if not categorized_cues:
            # No cues, return neutral profile
            return EmotionProfile()

        # Collect emotions and their intensities
        emotions: dict[str, list[float]] = {}
        vocal_qualities: list[str] = []
        physical_states: list[str] = []
        intensities: list[float] = []

        for cue in categorized_cues:
            category = cue.get("category", "unknown")
            emotion = cue.get("emotion", "neutral")
            intensity = cue.get("intensity", 0.5)

            intensities.append(intensity)

            if category == "emotion":
                if emotion not in emotions:
                    emotions[emotion] = []
                emotions[emotion].append(intensity)
            elif category == "vocal_quality":
                vocal_qualities.append(emotion)
                # Vocal quality also contributes to emotion
                if emotion not in emotions:
                    emotions[emotion] = []
                emotions[emotion].append(intensity)
            elif category == "physical":
                physical_states.append(emotion)
                # Physical state also contributes to emotion
                if emotion not in emotions:
                    emotions[emotion] = []
                emotions[emotion].append(intensity)

        # Determine primary emotion (most common, weighted by intensity)
        primary_emotion = "neutral"
        max_weight = 0.0
        for emotion, intensity_list in emotions.items():
            weight = sum(intensity_list) * len(intensity_list)
            if weight > max_weight:
                max_weight = weight
                primary_emotion = emotion

        # Calculate average intensity
        avg_intensity = sum(intensities) / len(intensities) if intensities else 0.5

        # Determine vocal quality (check raw cues for specific vocal qualities)
        vocal_quality = "normal"
        for cue in categorized_cues:
            if cue.get("category") == "vocal_quality":
                raw = cue.get("raw", "").lower()
                if "breaking" in raw or "breaks" in raw or "cracks" in raw:
                    vocal_quality = "breaking"
                elif "whisper" in raw:
                    vocal_quality = "whisper"
                elif "strained" in raw or "strain" in raw:
                    vocal_quality = "strained"
                elif "trembling" in raw or "trembl" in raw:
                    vocal_quality = "trembling"
                elif "hoarse" in raw:
                    vocal_quality = "hoarse"
                elif "shout" in raw or "yell" in raw:
                    vocal_quality = "shout"
                # If we found a specific vocal quality, use it
                if vocal_quality != "normal":
                    break

        # Determine physical state
        physical_state = "normal"
        if physical_states:
            physical_map = {"distress": "breathing_heavy", "joy": "normal", "sadness": "normal"}
            if "distress" in physical_states:
                # Check original cues for specific physical actions
                for cue in categorized_cues:
                    if cue.get("category") == "physical":
                        raw = cue.get("raw", "").lower()
                        if "cough" in raw:
                            physical_state = "coughing"
                        elif "gasp" in raw:
                            physical_state = "gasping"
                        elif "breath" in raw:
                            physical_state = "breathing_heavy"

        # Create base profile
        profile = EmotionProfile(
            primary_emotion=primary_emotion,
            intensity=avg_intensity,
            vocal_quality=vocal_quality,
            physical_state=physical_state,
            pacing="normal",
        )

        # Calculate parameter modifiers based on emotion
        if primary_emotion in self.EMOTION_PARAMETERS:
            params = self.EMOTION_PARAMETERS[primary_emotion]
            profile.stability_modifier = params["stability_modifier"]
            profile.style_modifier = params["style_modifier"]
            profile.similarity_modifier = params["similarity_modifier"]

        # Apply vocal quality modifiers
        if vocal_quality in self.VOCAL_QUALITY_PARAMETERS:
            params = self.VOCAL_QUALITY_PARAMETERS[vocal_quality]
            profile.stability_modifier += params["stability_modifier"] * 0.3
            profile.style_modifier = max(profile.style_modifier, params["style_modifier"])
            profile.similarity_modifier += params["similarity_modifier"] * 0.3

        # Apply physical state modifiers
        if physical_state in self.PHYSICAL_STATE_PARAMETERS:
            params = self.PHYSICAL_STATE_PARAMETERS[physical_state]
            profile.stability_modifier += params["stability_modifier"] * 0.3
            profile.style_modifier = max(profile.style_modifier, params["style_modifier"])
            profile.similarity_modifier += params["similarity_modifier"] * 0.3

        # Clamp modifiers to valid ranges
        profile.stability_modifier = max(-0.5, min(0.5, profile.stability_modifier))
        profile.style_modifier = max(0.0, min(1.0, profile.style_modifier))
        profile.similarity_modifier = max(-0.3, min(0.3, profile.similarity_modifier))

        return profile

    def apply_phase_context(
        self, profile: EmotionProfile, phase: int, scene_type: str
    ) -> EmotionProfile:
        """
        Apply phase-based emotional weight to the profile.

        Args:
            profile: Base emotion profile from cues
            phase: Current scene phase (1-4)
            scene_type: Type of scene ('submarine', 'crown_court', etc.)

        Returns:
            New EmotionProfile with phase adjustments (does not modify input)

        Example:
            >>> engine = EmotionEngine()
            >>> profile = EmotionProfile(primary_emotion='distress', intensity=0.6)
            >>> enhanced_profile = engine.apply_phase_context(profile, phase=3, scene_type='submarine')
            >>> # Intensity will be blended with phase 3's high baseline (0.85)
        """
        # Create a copy to avoid modifying the input profile
        from copy import copy

        result = copy(profile)

        phase_config = self.get_phase_config(scene_type, phase)

        # Blend cue-based intensity with phase baseline (70% cues, 30% phase)
        result.intensity = (result.intensity * 0.7) + (phase_config["baseline_intensity"] * 0.3)

        # Add phase modifiers to cue-based modifiers
        result.stability_modifier += phase_config["stability_modifier"]
        result.style_modifier += phase_config["style_modifier"]

        # Clamp values
        result.intensity = max(0.0, min(1.0, result.intensity))
        result.stability_modifier = max(-0.5, min(0.5, result.stability_modifier))
        result.style_modifier = max(0.0, min(1.0, result.style_modifier))

        return result

    def get_phase_config(self, scene_type: str, phase: int) -> dict[str, float]:
        """
        Get phase configuration for a specific scene type and phase.

        Args:
            scene_type: Type of scene
            phase: Phase number (1-4)

        Returns:
            Dictionary with baseline_intensity, stability_modifier, style_modifier
        """
        scene_type = scene_type.lower() if scene_type else "default"

        # Map scene class names to config keys
        scene_map = {
            "crowncourtscene": "crown_court",
            "submarinescene": "submarine",
            "pressurepoint": "submarine",
        }

        config_key = scene_map.get(scene_type, scene_type)

        if config_key not in self.PHASE_CONFIGS:
            config_key = "default"

        phase = max(1, min(4, phase))  # Clamp to 1-4

        return self.PHASE_CONFIGS[config_key].get(phase, self.PHASE_CONFIGS["default"][1])

    def apply_character_style(
        self, profile: EmotionProfile, character: Character
    ) -> EmotionProfile:
        """
        Apply character-specific emotional expression style to the profile.

        Different characters express emotions differently based on personality.

        Args:
            profile: Base emotion profile
            character: Character with emotion_expression_style

        Returns:
            New EmotionProfile with character style applied (does not modify input)

        Example:
            >>> engine = EmotionEngine()
            >>> profile = EmotionProfile(primary_emotion='distress', intensity=0.8)
            >>> # Engineer is restrained, Judge is very restrained, Wizard is theatrical
            >>> styled_profile = engine.apply_character_style(profile, engineer)
        """
        if not hasattr(character, "emotion_expression_style"):
            # Character doesn't have emotion style, return unchanged
            return profile

        # Create a copy to avoid modifying the input profile
        from copy import copy

        result = copy(profile)

        style = character.emotion_expression_style

        # Apply expressiveness scaling to style_modifier
        result.style_modifier *= style.get("expressiveness", 0.7)

        # Apply emotional range scaling to intensity
        result.intensity *= style.get("emotional_range", 0.8)

        # Apply restraint (reduces intensity of emotional expression)
        restraint = style.get("restraint", 0.3)
        result.intensity *= 1.0 - restraint

        # Adjust stability toward character baseline
        baseline_stability = style.get("stability_baseline", 0.5)
        # Blend 70% situation-based, 30% character baseline
        target_modifier = baseline_stability - 0.5  # Convert baseline to modifier
        result.stability_modifier = (result.stability_modifier * 0.7) + (target_modifier * 0.3)

        # Clamp values
        result.intensity = max(0.0, min(1.0, result.intensity))
        result.style_modifier = max(0.0, min(1.0, result.style_modifier))
        result.stability_modifier = max(-0.5, min(0.5, result.stability_modifier))

        return result

    def get_voice_parameters(
        self, profile: EmotionProfile, base_params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generate final ElevenLabs voice parameters from emotion profile.

        Args:
            profile: Emotion profile with modifiers
            base_params: Character's base voice settings

        Returns:
            Dictionary with final voice parameters for ElevenLabs API

        Example:
            >>> engine = EmotionEngine()
            >>> profile = EmotionProfile(stability_modifier=-0.3, style_modifier=0.8)
            >>> base_params = {'stability': 0.5, 'similarity_boost': 0.75, 'style': 0.2}
            >>> final_params = engine.get_voice_parameters(profile, base_params)
            >>> print(final_params['stability'])
            0.2  # 0.5 + (-0.3) = 0.2
        """
        # Calculate final parameters
        final_stability = base_params.get("stability", 0.5) + profile.stability_modifier
        final_stability = max(0.0, min(1.0, final_stability))

        final_similarity = base_params.get("similarity_boost", 0.75) + profile.similarity_modifier
        final_similarity = max(0.0, min(1.0, final_similarity))

        # Style is overridden by profile (not added), but still needs clamping
        final_style = max(0.0, min(1.0, profile.style_modifier))

        return {
            "stability": final_stability,
            "similarity_boost": final_similarity,
            "style": final_style,
            "use_speaker_boost": base_params.get("use_speaker_boost", True),
        }
