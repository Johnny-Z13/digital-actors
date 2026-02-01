"""
Emotional Cue Extraction System

Extracts and categorizes emotional cues from LLM responses before text cleaning.
This preserves rich emotional information that would otherwise be lost.
"""

import re
from typing import Any


class EmotionExtractor:
    """Extracts and categorizes emotional cues from bracketed annotations in text."""

    # Emotion category definitions
    VOCAL_QUALITY_KEYWORDS = {
        "whisper",
        "shout",
        "shouting",
        "voice breaking",
        "voice breaks",
        "voice cracks",
        "hoarse",
        "strained",
        "trembling",
        "breathless",
        "breaking",
        "cracking",
        "quiet",
        "quieter",
        "loud",
        "louder",
        "soft",
        "softer",
        "sharp",
        "measured",
        "gentle",
        "firm",
        "steady",
        "unsteady",
        "faltering",
        "clear",
        "muffled",
        "raspy",
        "gravelly",
        "shaky",
        "stable",
        "controlled",
        "tense",
        "tight",
        "relaxed",
        "calm voice",
        "urgent voice",
    }

    EMOTION_KEYWORDS = {
        "panicked",
        "panic",
        "calm",
        "calmer",
        "angry",
        "anger",
        "sad",
        "sadness",
        "hopeful",
        "hope",
        "desperate",
        "desperation",
        "relieved",
        "relief",
        "scared",
        "fear",
        "fearful",
        "terrified",
        "anxious",
        "anxiety",
        "worried",
        "concern",
        "concerned",
        "happy",
        "joy",
        "excited",
        "excitement",
        "frustrated",
        "frustration",
        "annoyed",
        "irritated",
        "pleased",
        "satisfied",
        "disappointed",
        "disappointment",
        "surprised",
        "shock",
        "shocked",
        "confused",
        "confusion",
        "determined",
        "resignation",
        "resigned",
        "nervous",
        "tense",
        "stressed",
        "overwhelmed",
        "vulnerable",
        "honest",
        "amused",
        "cynical",
        "suspicious",
        "weary",
        "distant",
        "impressed",
        "thoughtful",
        "considering",
        "empathetic",
        "sympathetic",
        "cold",
        "warm",
    }

    PHYSICAL_KEYWORDS = {
        "coughing",
        "cough",
        "gasping",
        "gasp",
        "choking",
        "choke",
        "breathing heavily",
        "breathing",
        "breath",
        "sighing",
        "sigh",
        "laughing",
        "laugh",
        "chuckle",
        "crying",
        "sob",
        "sobbing",
        "sniffling",
        "clearing throat",
        "swallowing",
        "gulp",
        "panting",
        "wheezing",
        "groaning",
        "groan",
        "grunting",
        "exhale",
        "inhale",
        "sharp intake",
        "intake of breath",
    }

    INTENSITY_MODIFIERS = {
        "slightly": 0.3,
        "a bit": 0.4,
        "somewhat": 0.5,
        "moderately": 0.6,
        "very": 0.8,
        "extremely": 0.9,
        "intensely": 0.9,
        "barely": 0.2,
        "violently": 0.95,
        "severely": 0.9,
        "heavily": 0.85,
        "deeply": 0.8,
        "mildly": 0.4,
        "lightly": 0.3,
    }

    PACING_KEYWORDS = {
        "pause",
        "long pause",
        "beat",
        "silence",
        "long silence",
        "quick",
        "quickly",
        "fast",
        "rapid",
        "rushed",
        "hurried",
        "slow",
        "slowly",
        "measured",
        "deliberate",
        "hesitant",
        "hesitation",
        "stuttering",
        "stammering",
    }

    def __init__(self):
        """Initialize the emotion extractor."""
        pass

    def extract_cues(self, text: str) -> tuple[str, list[str]]:
        """
        Extract emotional cues from bracketed annotations and return cleaned text.

        Args:
            text: Raw text with [bracketed emotional cues]

        Returns:
            Tuple of (cleaned_text, list_of_cues)

        Example:
            >>> extractor = EmotionExtractor()
            >>> text = "[coughing violently] I can't... [strained] breathe..."
            >>> cleaned, cues = extractor.extract_cues(text)
            >>> print(cleaned)
            "I can't... breathe..."
            >>> print(cues)
            ["coughing violently", "strained"]
        """
        # Extract all bracketed content
        pattern = r"\[([^\]]+)\]"
        cues = re.findall(pattern, text)

        # Remove brackets from text
        cleaned = re.sub(pattern, "", text)

        # Clean up spacing
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.strip()

        return cleaned, cues

    def categorize_cue(self, cue: str) -> dict[str, Any]:
        """
        Categorize a single emotional cue into structured data.

        Args:
            cue: A single emotional cue string (e.g., "voice breaking", "coughing violently")

        Returns:
            Dictionary with categorization:
            {
                'category': str,  # 'vocal_quality', 'emotion', 'physical', 'pacing'
                'emotion': str,   # Primary emotion detected
                'intensity': float,  # 0.0 to 1.0
                'modifiers': List[str],  # Additional descriptors
                'raw': str  # Original cue
            }

        Example:
            >>> extractor = EmotionExtractor()
            >>> result = extractor.categorize_cue("coughing violently")
            >>> print(result)
            {
                'category': 'physical',
                'emotion': 'distress',
                'intensity': 0.95,
                'modifiers': ['violently'],
                'raw': 'coughing violently'
            }
        """
        cue_lower = cue.lower().strip()
        result = {
            "category": "unknown",
            "emotion": "neutral",
            "intensity": 0.5,
            "modifiers": [],
            "raw": cue,
        }

        # Check for intensity modifiers
        intensity_found = False
        for modifier, intensity_value in self.INTENSITY_MODIFIERS.items():
            if modifier in cue_lower:
                result["intensity"] = intensity_value
                result["modifiers"].append(modifier)
                intensity_found = True

        # Check category based on keywords
        # Physical actions (highest priority - most specific)
        for keyword in self.PHYSICAL_KEYWORDS:
            if keyword in cue_lower:
                result["category"] = "physical"
                result["emotion"] = self._map_physical_to_emotion(keyword)
                if not intensity_found:
                    result["intensity"] = 0.7  # Default for physical actions
                return result

        # Vocal quality
        for keyword in self.VOCAL_QUALITY_KEYWORDS:
            if keyword in cue_lower:
                result["category"] = "vocal_quality"
                result["emotion"] = self._map_vocal_to_emotion(keyword)
                if not intensity_found:
                    result["intensity"] = 0.6  # Default for vocal quality
                return result

        # Pacing
        for keyword in self.PACING_KEYWORDS:
            if keyword in cue_lower:
                result["category"] = "pacing"
                result["emotion"] = "neutral"  # Pacing doesn't imply emotion
                if not intensity_found:
                    result["intensity"] = 0.5
                return result

        # Emotions (lowest priority - most general)
        for keyword in self.EMOTION_KEYWORDS:
            if keyword in cue_lower:
                result["category"] = "emotion"
                result["emotion"] = self._normalize_emotion(keyword)
                if not intensity_found:
                    result["intensity"] = 0.7  # Default for direct emotions
                return result

        # If no category matched, return neutral
        return result

    def _map_physical_to_emotion(self, keyword: str) -> str:
        """Map physical actions to emotional states."""
        # Check for phrases that contain distress indicators
        distress_indicators = [
            "coughing",
            "cough",
            "gasping",
            "gasp",
            "choking",
            "choke",
            "breathing heavily",
            "wheezing",
            "groaning",
            "panting",
            "breathing",
        ]
        relief_indicators = ["sighing", "sigh", "exhale"]
        joy_indicators = ["laughing", "laugh", "chuckle"]
        sadness_indicators = ["crying", "sob", "sobbing", "sniffling"]
        surprise_indicators = ["sharp intake", "intake of breath", "inhale"]

        # Check if keyword contains any of the indicators
        for indicator in distress_indicators:
            if indicator in keyword:
                return "distress"

        for indicator in relief_indicators:
            if indicator in keyword:
                return "relief"

        for indicator in joy_indicators:
            if indicator in keyword:
                return "joy"

        for indicator in sadness_indicators:
            if indicator in keyword:
                return "sadness"

        for indicator in surprise_indicators:
            if indicator in keyword:
                return "surprise"

        return "neutral"

    def _map_vocal_to_emotion(self, keyword: str) -> str:
        """Map vocal quality to emotional states."""
        distress_vocals = {
            "voice breaking",
            "voice breaks",
            "voice cracks",
            "breaking",
            "cracking",
            "hoarse",
            "strained",
            "trembling",
            "breathless",
            "unsteady",
            "faltering",
            "shaky",
            "raspy",
            "tense",
            "tight",
        }
        calm_vocals = {
            "measured",
            "steady",
            "controlled",
            "calm voice",
            "clear",
            "stable",
            "relaxed",
        }
        anger_vocals = {"sharp", "shout", "shouting", "loud", "louder", "firm"}
        secretive_vocals = {"whisper", "quiet", "quieter", "soft", "softer", "muffled"}
        gentle_vocals = {"gentle", "soft", "softer", "warm"}

        if keyword in distress_vocals:
            return "distress"
        elif keyword in calm_vocals:
            return "calm"
        elif keyword in anger_vocals:
            return "anger"
        elif keyword in secretive_vocals:
            return "secretive"
        elif keyword in gentle_vocals:
            return "gentle"
        else:
            return "neutral"

    def _normalize_emotion(self, keyword: str) -> str:
        """Normalize emotion keywords to standard emotion names."""
        # Map variations to primary emotions
        emotion_map = {
            "panicked": "panic",
            "scared": "fear",
            "fearful": "fear",
            "terrified": "fear",
            "anxious": "anxiety",
            "worried": "concern",
            "angry": "anger",
            "annoyed": "anger",
            "irritated": "anger",
            "frustrated": "frustration",
            "sad": "sadness",
            "disappointed": "disappointment",
            "happy": "joy",
            "excited": "excitement",
            "pleased": "satisfaction",
            "satisfied": "satisfaction",
            "hopeful": "hope",
            "desperate": "desperation",
            "relieved": "relief",
            "surprised": "surprise",
            "shocked": "shock",
            "confused": "confusion",
            "determined": "determination",
            "resigned": "resignation",
            "nervous": "anxiety",
            "stressed": "stress",
            "overwhelmed": "stress",
            "vulnerable": "vulnerability",
            "amused": "amusement",
            "cynical": "cynicism",
            "suspicious": "suspicion",
            "weary": "weariness",
            "calm": "calm",
            "calmer": "calm",
            "concerned": "concern",
            "honest": "honesty",
            "distant": "detachment",
            "impressed": "admiration",
            "thoughtful": "contemplation",
            "considering": "contemplation",
            "empathetic": "empathy",
            "sympathetic": "empathy",
            "cold": "coldness",
            "warm": "warmth",
        }

        return emotion_map.get(keyword, keyword)
