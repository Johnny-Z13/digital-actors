"""
Unit tests for EmotionExtractor

Tests emotional cue extraction and categorization functionality.
"""

import os
import sys

# Add parent directory to path so we can import emotion_extractor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest

from emotion_extractor import EmotionExtractor


class TestEmotionExtractor(unittest.TestCase):
    """Test cases for EmotionExtractor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.extractor = EmotionExtractor()

    def test_extract_single_cue(self):
        """Test extraction of a single emotional cue."""
        text = "[panicked] Help!"
        cleaned, cues = self.extractor.extract_cues(text)

        self.assertEqual(cleaned, "Help!")
        self.assertEqual(cues, ["panicked"])

    def test_extract_multiple_cues(self):
        """Test extraction of multiple emotional cues."""
        text = "[coughing] I... [strained] can't..."
        cleaned, cues = self.extractor.extract_cues(text)

        self.assertEqual(cleaned, "I... can't...")
        self.assertEqual(cues, ["coughing", "strained"])

    def test_extract_no_cues(self):
        """Test text with no emotional cues."""
        text = "Everything is fine."
        cleaned, cues = self.extractor.extract_cues(text)

        self.assertEqual(cleaned, "Everything is fine.")
        self.assertEqual(cues, [])

    def test_extract_complex_cues(self):
        """Test extraction of complex emotional cues with multiple words."""
        text = "[voice breaking] I... [long pause] can't do this."
        cleaned, cues = self.extractor.extract_cues(text)

        self.assertEqual(cleaned, "I... can't do this.")
        self.assertEqual(cues, ["voice breaking", "long pause"])

    def test_cleaned_text_spacing(self):
        """Test that cleaned text has proper spacing after cue removal."""
        text = "[pause]Hello[whisper]world"
        cleaned, cues = self.extractor.extract_cues(text)

        # Should clean up spacing
        self.assertEqual(cleaned, "Helloworld")

    def test_categorize_vocal_quality(self):
        """Test categorization of vocal quality cues."""
        result = self.extractor.categorize_cue("whisper")

        self.assertEqual(result["category"], "vocal_quality")
        self.assertEqual(result["emotion"], "secretive")
        self.assertGreater(result["intensity"], 0.0)

    def test_categorize_physical(self):
        """Test categorization of physical action cues."""
        result = self.extractor.categorize_cue("coughing violently")

        self.assertEqual(result["category"], "physical")
        self.assertEqual(result["emotion"], "distress")
        self.assertGreaterEqual(result["intensity"], 0.9)  # "violently" should boost intensity
        self.assertIn("violently", result["modifiers"])

    def test_categorize_emotion(self):
        """Test categorization of direct emotion cues."""
        result = self.extractor.categorize_cue("panicked")

        self.assertEqual(result["category"], "emotion")
        self.assertEqual(result["emotion"], "panic")
        self.assertGreater(result["intensity"], 0.0)

    def test_categorize_pacing(self):
        """Test categorization of pacing cues."""
        result = self.extractor.categorize_cue("long pause")

        self.assertEqual(result["category"], "pacing")
        self.assertEqual(result["emotion"], "neutral")  # Pacing doesn't imply emotion

    def test_intensity_modifier_very(self):
        """Test that intensity modifiers work correctly."""
        result = self.extractor.categorize_cue("very scared")

        self.assertEqual(result["category"], "emotion")
        self.assertAlmostEqual(result["intensity"], 0.8)  # "very" = 0.8
        self.assertIn("very", result["modifiers"])

    def test_intensity_modifier_slightly(self):
        """Test slight intensity modifier."""
        result = self.extractor.categorize_cue("slightly worried")

        self.assertEqual(result["category"], "emotion")
        self.assertAlmostEqual(result["intensity"], 0.3)  # "slightly" = 0.3

    def test_voice_breaking_categorization(self):
        """Test that 'voice breaking' is correctly categorized."""
        result = self.extractor.categorize_cue("voice breaking")

        self.assertEqual(result["category"], "vocal_quality")
        self.assertEqual(result["emotion"], "distress")

    def test_breathing_heavily_categorization(self):
        """Test that 'breathing heavily' is correctly categorized."""
        result = self.extractor.categorize_cue("breathing heavily")

        self.assertEqual(result["category"], "physical")
        self.assertEqual(result["emotion"], "distress")

    def test_calm_categorization(self):
        """Test that 'calm' is correctly categorized."""
        result = self.extractor.categorize_cue("calm")

        self.assertEqual(result["category"], "emotion")
        self.assertEqual(result["emotion"], "calm")

    def test_measured_tone_categorization(self):
        """Test that 'measured' is correctly categorized as vocal quality."""
        result = self.extractor.categorize_cue("measured")

        self.assertEqual(result["category"], "vocal_quality")
        self.assertEqual(result["emotion"], "calm")

    def test_unknown_cue_categorization(self):
        """Test that unknown cues are handled gracefully."""
        result = self.extractor.categorize_cue("xyzabc123")

        self.assertEqual(result["category"], "unknown")
        self.assertEqual(result["emotion"], "neutral")
        self.assertEqual(result["raw"], "xyzabc123")

    def test_case_insensitive_extraction(self):
        """Test that cue extraction is case insensitive."""
        result1 = self.extractor.categorize_cue("PANICKED")
        result2 = self.extractor.categorize_cue("panicked")

        self.assertEqual(result1["category"], result2["category"])
        self.assertEqual(result1["emotion"], result2["emotion"])

    def test_real_world_engineer_response(self):
        """Test a realistic response from the Engineer character."""
        text = "[sharp intake of breath] [pause, breathing] The radiation... [voice breaking] it's spreading too fast."
        cleaned, cues = self.extractor.extract_cues(text)

        self.assertEqual(cleaned, "The radiation... it's spreading too fast.")
        self.assertEqual(len(cues), 3)
        self.assertIn("sharp intake of breath", cues)
        self.assertIn("pause, breathing", cues)
        self.assertIn("voice breaking", cues)

    def test_real_world_judge_response(self):
        """Test a realistic response from the Judge character."""
        text = "[pause, considering] [measured tone] Counselor, that is a valid point."
        cleaned, cues = self.extractor.extract_cues(text)

        self.assertEqual(cleaned, "Counselor, that is a valid point.")
        self.assertEqual(len(cues), 2)

    def test_multiple_spaces_cleanup(self):
        """Test that multiple spaces are cleaned up properly."""
        text = "[pause]  I     think   [whisper]  this"
        cleaned, cues = self.extractor.extract_cues(text)

        # Should clean up multiple spaces to single spaces
        self.assertEqual(cleaned, "I think this")


class TestEmotionMapping(unittest.TestCase):
    """Test emotion mapping functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.extractor = EmotionExtractor()

    def test_physical_to_emotion_coughing(self):
        """Test that coughing maps to distress."""
        emotion = self.extractor._map_physical_to_emotion("coughing")
        self.assertEqual(emotion, "distress")

    def test_physical_to_emotion_laughing(self):
        """Test that laughing maps to joy."""
        emotion = self.extractor._map_physical_to_emotion("laughing")
        self.assertEqual(emotion, "joy")

    def test_physical_to_emotion_crying(self):
        """Test that crying maps to sadness."""
        emotion = self.extractor._map_physical_to_emotion("crying")
        self.assertEqual(emotion, "sadness")

    def test_vocal_to_emotion_breaking(self):
        """Test that voice breaking maps to distress."""
        emotion = self.extractor._map_vocal_to_emotion("voice breaking")
        self.assertEqual(emotion, "distress")

    def test_vocal_to_emotion_whisper(self):
        """Test that whisper maps to secretive."""
        emotion = self.extractor._map_vocal_to_emotion("whisper")
        self.assertEqual(emotion, "secretive")

    def test_vocal_to_emotion_shout(self):
        """Test that shout maps to anger."""
        emotion = self.extractor._map_vocal_to_emotion("shout")
        self.assertEqual(emotion, "anger")

    def test_normalize_emotion_panicked(self):
        """Test emotion normalization."""
        emotion = self.extractor._normalize_emotion("panicked")
        self.assertEqual(emotion, "panic")

    def test_normalize_emotion_scared(self):
        """Test that scared normalizes to fear."""
        emotion = self.extractor._normalize_emotion("scared")
        self.assertEqual(emotion, "fear")


if __name__ == "__main__":
    unittest.main()
