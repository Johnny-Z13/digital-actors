"""
Unit tests for EmotionEngine

Tests emotion-to-parameter mapping, phase context, and character style application.
"""

import os
import sys

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest

from characters.base import Character
from characters.engineer import Engineer
from characters.judge import Judge
from characters.wizard import Wizard
from emotion_engine import EmotionEngine, EmotionProfile


class TestEmotionProfile(unittest.TestCase):
    """Test EmotionProfile dataclass."""

    def test_default_profile(self):
        """Test default EmotionProfile values."""
        profile = EmotionProfile()

        self.assertEqual(profile.primary_emotion, "neutral")
        self.assertEqual(profile.intensity, 0.5)
        self.assertEqual(profile.vocal_quality, "normal")
        self.assertEqual(profile.physical_state, "normal")
        self.assertEqual(profile.pacing, "normal")
        self.assertEqual(profile.stability_modifier, 0.0)
        self.assertEqual(profile.style_modifier, 0.5)
        self.assertEqual(profile.similarity_modifier, 0.0)

    def test_custom_profile(self):
        """Test creating a custom EmotionProfile."""
        profile = EmotionProfile(primary_emotion="distress", intensity=0.8, stability_modifier=-0.3)

        self.assertEqual(profile.primary_emotion, "distress")
        self.assertEqual(profile.intensity, 0.8)
        self.assertEqual(profile.stability_modifier, -0.3)


class TestEmotionEngine(unittest.TestCase):
    """Test EmotionEngine class."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = EmotionEngine()

    def test_analyze_cues_empty(self):
        """Test analyzing empty cue list."""
        profile = self.engine.analyze_cues([])

        self.assertEqual(profile.primary_emotion, "neutral")
        self.assertEqual(profile.intensity, 0.5)

    def test_analyze_cues_distress(self):
        """Test analyzing distress cues."""
        cues = [
            {"category": "emotion", "emotion": "distress", "intensity": 0.8},
            {"category": "physical", "emotion": "distress", "intensity": 0.9},
        ]

        profile = self.engine.analyze_cues(cues)

        self.assertEqual(profile.primary_emotion, "distress")
        self.assertGreater(profile.intensity, 0.7)
        self.assertLess(profile.stability_modifier, 0.0)  # Distress reduces stability
        self.assertGreater(profile.style_modifier, 0.6)  # Distress is expressive

    def test_analyze_cues_calm(self):
        """Test analyzing calm cues."""
        cues = [{"category": "emotion", "emotion": "calm", "intensity": 0.6}]

        profile = self.engine.analyze_cues(cues)

        self.assertEqual(profile.primary_emotion, "calm")
        self.assertGreater(profile.stability_modifier, 0.0)  # Calm increases stability
        self.assertLess(profile.style_modifier, 0.4)  # Calm is less expressive

    def test_analyze_cues_voice_breaking(self):
        """Test analyzing voice breaking (vocal quality)."""
        cues = [
            {
                "category": "vocal_quality",
                "emotion": "distress",
                "intensity": 0.8,
                "raw": "voice breaking",
            }
        ]

        profile = self.engine.analyze_cues(cues)

        self.assertEqual(profile.vocal_quality, "breaking")
        self.assertLess(profile.stability_modifier, 0.0)
        self.assertGreater(profile.style_modifier, 0.7)

    def test_analyze_cues_whisper(self):
        """Test analyzing whisper cues."""
        cues = [
            {
                "category": "vocal_quality",
                "emotion": "secretive",
                "intensity": 0.6,
                "raw": "whisper",
            }
        ]

        profile = self.engine.analyze_cues(cues)

        self.assertEqual(profile.vocal_quality, "whisper")
        self.assertGreater(profile.stability_modifier, 0.0)  # Whisper is controlled

    def test_analyze_cues_coughing(self):
        """Test analyzing coughing (physical state)."""
        cues = [
            {
                "category": "physical",
                "emotion": "distress",
                "intensity": 0.9,
                "raw": "coughing violently",
            }
        ]

        profile = self.engine.analyze_cues(cues)

        self.assertEqual(profile.physical_state, "coughing")
        self.assertLess(profile.stability_modifier, 0.0)
        self.assertGreater(profile.style_modifier, 0.7)

    def test_analyze_cues_multiple_emotions(self):
        """Test analyzing multiple different emotions (most common wins)."""
        cues = [
            {"category": "emotion", "emotion": "distress", "intensity": 0.8},
            {"category": "emotion", "emotion": "distress", "intensity": 0.9},
            {"category": "emotion", "emotion": "calm", "intensity": 0.5},
        ]

        profile = self.engine.analyze_cues(cues)

        # Distress appears twice with high intensity, should be primary
        self.assertEqual(profile.primary_emotion, "distress")

    def test_stability_modifier_clamping(self):
        """Test that stability modifier is clamped to valid range."""
        # Create extreme cues that would exceed limits
        cues = [
            {"category": "emotion", "emotion": "panic", "intensity": 1.0},
            {"category": "physical", "emotion": "distress", "intensity": 1.0},
            {
                "category": "vocal_quality",
                "emotion": "distress",
                "intensity": 1.0,
                "raw": "breaking",
            },
        ]

        profile = self.engine.analyze_cues(cues)

        # Should be clamped to -0.5 minimum
        self.assertGreaterEqual(profile.stability_modifier, -0.5)
        self.assertLessEqual(profile.stability_modifier, 0.5)

    def test_style_modifier_clamping(self):
        """Test that style modifier is clamped to valid range."""
        cues = [{"category": "emotion", "emotion": "panic", "intensity": 1.0}]

        profile = self.engine.analyze_cues(cues)

        self.assertGreaterEqual(profile.style_modifier, 0.0)
        self.assertLessEqual(profile.style_modifier, 1.0)


class TestPhaseContext(unittest.TestCase):
    """Test phase-aware voice modulation."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = EmotionEngine()

    def test_get_phase_config_submarine(self):
        """Test getting submarine phase configuration."""
        config = self.engine.get_phase_config("submarine", 1)

        self.assertIn("baseline_intensity", config)
        self.assertIn("stability_modifier", config)
        self.assertIn("style_modifier", config)

    def test_get_phase_config_crown_court(self):
        """Test getting crown court phase configuration."""
        config = self.engine.get_phase_config("crown_court", 1)

        self.assertIn("baseline_intensity", config)
        # Crown court phase 1 should have higher stability (formal setting)
        self.assertGreater(config["stability_modifier"], 0.0)

    def test_phase_progression_submarine(self):
        """Test that submarine phases increase in intensity."""
        phase1_config = self.engine.get_phase_config("submarine", 1)
        phase2_config = self.engine.get_phase_config("submarine", 2)
        phase3_config = self.engine.get_phase_config("submarine", 3)
        phase4_config = self.engine.get_phase_config("submarine", 4)

        # Intensity should increase with each phase
        self.assertLess(phase1_config["baseline_intensity"], phase2_config["baseline_intensity"])
        self.assertLess(phase2_config["baseline_intensity"], phase3_config["baseline_intensity"])
        self.assertLess(phase3_config["baseline_intensity"], phase4_config["baseline_intensity"])

    def test_apply_phase_context(self):
        """Test applying phase context to emotion profile."""
        base_profile = EmotionProfile(
            primary_emotion="distress",
            intensity=0.6,
            stability_modifier=-0.1,  # Changed from -0.2 to avoid clamping
            style_modifier=0.5,  # Changed from 0.7 to see increase
        )

        # Apply submarine phase 3 (high stress)
        enhanced_profile = self.engine.apply_phase_context(base_profile, 3, "submarine")

        # Intensity should be blended with phase baseline (0.85 for phase 3)
        # 0.6 * 0.7 + 0.85 * 0.3 = 0.42 + 0.255 = 0.675
        self.assertAlmostEqual(enhanced_profile.intensity, 0.675, places=2)

        # Phase modifiers should be added
        # -0.1 + -0.3 = -0.4 (more negative)
        self.assertLess(enhanced_profile.stability_modifier, base_profile.stability_modifier)
        # 0.5 + 0.4 = 0.9 (more positive)
        self.assertGreater(enhanced_profile.style_modifier, base_profile.style_modifier)

    def test_phase_clamping(self):
        """Test that phase numbers are clamped to valid range."""
        # Test with out-of-range phase
        config = self.engine.get_phase_config("submarine", 99)

        # Should default to phase 4 (clamped)
        self.assertIsNotNone(config)


class TestCharacterStyle(unittest.TestCase):
    """Test character-specific emotion expression."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = EmotionEngine()
        self.engineer = Engineer()
        self.judge = Judge()
        self.wizard = Wizard()

    def test_engineer_restraint(self):
        """Test that Engineer shows military restraint."""
        base_profile = EmotionProfile(primary_emotion="distress", intensity=0.8, style_modifier=0.8)

        styled_profile = self.engine.apply_character_style(base_profile, self.engineer)

        # Engineer has restraint=0.4, so intensity should be reduced
        # 0.8 * 0.7 (emotional_range) * 0.6 (1-restraint) = 0.336
        self.assertLess(styled_profile.intensity, base_profile.intensity)

        # Engineer has expressiveness=0.6, so style should be reduced
        # 0.8 * 0.6 = 0.48
        self.assertAlmostEqual(styled_profile.style_modifier, 0.48, places=2)

    def test_judge_high_restraint(self):
        """Test that Judge shows high judicial restraint."""
        base_profile = EmotionProfile(primary_emotion="anger", intensity=0.8, style_modifier=0.7)

        styled_profile = self.engine.apply_character_style(base_profile, self.judge)

        # Judge has restraint=0.7, so intensity should be significantly reduced
        # 0.8 * 0.5 (emotional_range) * 0.3 (1-restraint) = 0.12
        self.assertLess(styled_profile.intensity, 0.3)

        # Judge has expressiveness=0.4, so style should be reduced
        self.assertLess(styled_profile.style_modifier, 0.5)

    def test_wizard_theatrical(self):
        """Test that Wizard is highly theatrical."""
        base_profile = EmotionProfile(
            primary_emotion="excitement", intensity=0.7, style_modifier=0.7
        )

        styled_profile = self.engine.apply_character_style(base_profile, self.wizard)

        # Wizard has restraint=0.1 and emotional_range=1.0, so intensity should remain high
        # 0.7 * 1.0 * 0.9 = 0.63
        self.assertGreater(styled_profile.intensity, 0.6)

        # Wizard has expressiveness=0.9, so style should be amplified
        # 0.7 * 0.9 = 0.63
        self.assertGreater(styled_profile.style_modifier, 0.6)

    def test_character_without_emotion_style(self):
        """Test handling of character without emotion_expression_style."""
        # Create a basic character without emotion style
        basic_character = Character(id="test", name="Test Character")

        base_profile = EmotionProfile(primary_emotion="neutral", intensity=0.5)

        # Should handle gracefully and return unchanged (except for default style)
        styled_profile = self.engine.apply_character_style(base_profile, basic_character)

        # With default emotion style, intensity should be affected
        # 0.5 * 0.8 (emotional_range) * 0.7 (1-restraint) = 0.28
        self.assertIsNotNone(styled_profile)

    def test_stability_baseline_blending(self):
        """Test that character stability baseline affects final stability."""
        # Judge has high stability_baseline (0.7)
        base_profile = EmotionProfile(
            primary_emotion="distress",
            stability_modifier=-0.3,  # Distress normally reduces stability
        )

        styled_profile = self.engine.apply_character_style(base_profile, self.judge)

        # Judge's high baseline (0.7) should pull stability modifier up
        # Blend: -0.3 * 0.7 + (0.7 - 0.5) * 0.3 = -0.21 + 0.06 = -0.15
        self.assertGreater(styled_profile.stability_modifier, base_profile.stability_modifier)


class TestVoiceParameters(unittest.TestCase):
    """Test voice parameter generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = EmotionEngine()

    def test_get_voice_parameters_basic(self):
        """Test basic voice parameter generation."""
        profile = EmotionProfile(
            stability_modifier=-0.3, style_modifier=0.8, similarity_modifier=-0.1
        )

        base_params = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.2,
            "use_speaker_boost": True,
        }

        final_params = self.engine.get_voice_parameters(profile, base_params)

        # stability: 0.5 + (-0.3) = 0.2
        self.assertAlmostEqual(final_params["stability"], 0.2, places=2)

        # similarity: 0.75 + (-0.1) = 0.65
        self.assertAlmostEqual(final_params["similarity_boost"], 0.65, places=2)

        # style: overridden by profile
        self.assertEqual(final_params["style"], 0.8)

        # use_speaker_boost: preserved
        self.assertTrue(final_params["use_speaker_boost"])

    def test_voice_parameters_clamping(self):
        """Test that voice parameters are clamped to valid ranges."""
        profile = EmotionProfile(
            stability_modifier=-0.8,  # Would result in negative stability
            style_modifier=1.2,  # Would exceed 1.0
            similarity_modifier=0.5,  # Would exceed 1.0
        )

        base_params = {
            "stability": 0.3,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True,
        }

        final_params = self.engine.get_voice_parameters(profile, base_params)

        # All values should be clamped to [0.0, 1.0]
        self.assertGreaterEqual(final_params["stability"], 0.0)
        self.assertLessEqual(final_params["stability"], 1.0)

        self.assertGreaterEqual(final_params["similarity_boost"], 0.0)
        self.assertLessEqual(final_params["similarity_boost"], 1.0)

        self.assertGreaterEqual(final_params["style"], 0.0)
        self.assertLessEqual(final_params["style"], 1.0)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple components."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = EmotionEngine()
        self.engineer = Engineer()

    def test_full_pipeline_distress(self):
        """Test full pipeline: cues -> profile -> phase -> character -> parameters."""
        # Simulate Engineer in submarine phase 3 with distress cues
        cues = [
            {"category": "physical", "emotion": "distress", "intensity": 0.9, "raw": "coughing"},
            {
                "category": "vocal_quality",
                "emotion": "distress",
                "intensity": 0.8,
                "raw": "strained",
            },
        ]

        # Analyze cues
        profile = self.engine.analyze_cues(cues)

        # Apply phase context (submarine phase 3)
        profile = self.engine.apply_phase_context(profile, 3, "submarine")

        # Apply character style (Engineer)
        profile = self.engine.apply_character_style(profile, self.engineer)

        # Generate final parameters
        base_params = {
            "stability": 0.4,
            "similarity_boost": 0.8,
            "style": 0.2,
            "use_speaker_boost": True,
        }

        final_params = self.engine.get_voice_parameters(profile, base_params)

        # Verify final parameters are in valid ranges
        self.assertGreaterEqual(final_params["stability"], 0.0)
        self.assertLessEqual(final_params["stability"], 1.0)

        # Distress should result in low stability
        self.assertLess(final_params["stability"], 0.4)

        # Distress should result in high style (expressiveness)
        self.assertGreater(final_params["style"], 0.5)


if __name__ == "__main__":
    unittest.main()
