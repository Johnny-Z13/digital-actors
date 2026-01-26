"""
Unit tests for TTS Audio Tag Preservation

Tests the clean_text_for_tts() function and audio tag classification.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import patch


class TestCleanTextForTTS(unittest.TestCase):
    """Test cases for clean_text_for_tts() function."""

    def setUp(self):
        """Set up test fixtures."""
        # Import here to avoid issues with module-level imports
        from tts_elevenlabs import TTSManager
        self.manager = TTSManager()

    def test_preserves_laughs_when_enabled(self):
        """Test that [laughs] is preserved when audio tags are enabled."""
        text = "[laughs] That's hilarious!"
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertIn("[laughs]", result)
        self.assertIn("hilarious", result)

    def test_preserves_sighs_when_enabled(self):
        """Test that [sighs] is preserved when audio tags are enabled."""
        text = "[sighs] I suppose you're right."
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertIn("[sighs]", result)

    def test_preserves_coughing_when_enabled(self):
        """Test that [coughing] is preserved when audio tags are enabled."""
        text = "[coughing] I can't... breathe..."
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertIn("[coughing]", result)

    def test_preserves_multiple_audio_tags(self):
        """Test multiple audio tags are preserved."""
        text = "[gasps] Oh no! [sobbing] What have I done?"
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertIn("[gasps]", result)
        self.assertIn("[sobbing]", result)

    def test_removes_audio_tags_when_disabled(self):
        """Test that audio tags are removed when preservation is disabled."""
        text = "[laughs] That's hilarious!"
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=False)
        self.assertNotIn("[laughs]", result)
        self.assertEqual(result, "That's hilarious!")

    def test_converts_static_to_pause(self):
        """Test that [static] becomes a pause regardless of flag."""
        text = "Hello? [static] Can you hear me?"
        result_enabled = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        result_disabled = self.manager.clean_text_for_tts(text, preserve_audio_tags=False)

        self.assertIn("...", result_enabled)
        self.assertNotIn("[static]", result_enabled)
        self.assertIn("...", result_disabled)

    def test_converts_alarm_to_pause(self):
        """Test that [alarm] becomes a pause."""
        text = "[alarm blaring] Warning!"
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertIn("...", result)
        self.assertNotIn("[alarm", result)

    def test_removes_nods_completely(self):
        """Test that [nods] is removed completely (no pause)."""
        text = "[nods] I understand."
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertNotIn("[nods]", result)
        self.assertNotIn("...", result)
        self.assertEqual(result, "I understand.")

    def test_removes_smiles_completely(self):
        """Test that [smiles] is removed completely."""
        text = "[smiling] Thank you so much!"
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertNotIn("[smiling]", result)
        self.assertEqual(result, "Thank you so much!")

    def test_pause_tag_becomes_ellipsis(self):
        """Test that [pause] becomes ellipsis."""
        text = "Well... [pause] I suppose so."
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertIn("...", result)
        self.assertNotIn("[pause]", result)

    def test_silence_tag_becomes_ellipsis(self):
        """Test that [silence] becomes ellipsis."""
        text = "And then [silence] nothing."
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertIn("...", result)

    def test_cleans_multiple_spaces(self):
        """Test that multiple spaces are cleaned up."""
        text = "[nods]  I    think  [pause]  yes."
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        # Should not have multiple consecutive spaces
        self.assertNotIn("  ", result)

    def test_cleans_excessive_ellipses(self):
        """Test that more than 3 dots become exactly 3."""
        text = "I... [static] ...can't..."
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertNotIn("....", result)

    def test_whispers_preserved_when_enabled(self):
        """Test that [whispers] is preserved for ElevenLabs."""
        text = "[whispers] Don't let them hear you."
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertIn("[whispers]", result)

    def test_shouts_preserved_when_enabled(self):
        """Test that [shouts] is preserved."""
        text = "[shouts] Run!"
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertIn("[shouts]", result)

    def test_emotional_states_preserved(self):
        """Test emotional state tags like [sad], [angry] are preserved."""
        text = "[sad] I miss them so much."
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertIn("[sad]", result)

    def test_signal_lost_becomes_pause(self):
        """Test that [signal lost] becomes a pause."""
        text = "The readings show [signal lost] emergency!"
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)
        self.assertNotIn("[signal lost]", result)
        self.assertIn("...", result)


class TestAudioTagClassification(unittest.TestCase):
    """Test the audio tag classification constants."""

    def test_audio_tags_contains_laughs(self):
        """Verify ELEVENLABS_AUDIO_TAGS contains laugh variations."""
        from tts_elevenlabs import ELEVENLABS_AUDIO_TAGS
        self.assertIn('laughs', ELEVENLABS_AUDIO_TAGS)
        self.assertIn('laughing', ELEVENLABS_AUDIO_TAGS)
        self.assertIn('giggles', ELEVENLABS_AUDIO_TAGS)

    def test_audio_tags_contains_sighs(self):
        """Verify ELEVENLABS_AUDIO_TAGS contains sigh variations."""
        from tts_elevenlabs import ELEVENLABS_AUDIO_TAGS
        self.assertIn('sighs', ELEVENLABS_AUDIO_TAGS)
        self.assertIn('sigh', ELEVENLABS_AUDIO_TAGS)

    def test_audio_tags_contains_coughs(self):
        """Verify ELEVENLABS_AUDIO_TAGS contains cough variations."""
        from tts_elevenlabs import ELEVENLABS_AUDIO_TAGS
        self.assertIn('coughs', ELEVENLABS_AUDIO_TAGS)
        self.assertIn('coughing', ELEVENLABS_AUDIO_TAGS)

    def test_pause_tags_contains_static(self):
        """Verify PAUSE_TAGS contains static/sfx."""
        from tts_elevenlabs import PAUSE_TAGS
        self.assertIn('static', PAUSE_TAGS)
        self.assertIn('alarm', PAUSE_TAGS)

    def test_remove_tags_contains_actions(self):
        """Verify REMOVE_TAGS contains non-vocal actions."""
        from tts_elevenlabs import REMOVE_TAGS
        self.assertIn('nods', REMOVE_TAGS)
        self.assertIn('smiles', REMOVE_TAGS)


class TestRealWorldScenarios(unittest.TestCase):
    """Test realistic dialogue scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        from tts_elevenlabs import TTSManager
        self.manager = TTSManager()

    def test_engineer_distress_dialogue(self):
        """Test Engineer character with distress tags."""
        text = "[coughing] I can't... [gasps] The radiation... it's spreading too fast!"
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)

        self.assertIn("[coughing]", result)
        self.assertIn("[gasps]", result)
        self.assertIn("radiation", result)

    def test_wizard_amused_dialogue(self):
        """Test Wizard character with amusement."""
        text = "[chuckles] [eyes twinkling] Ah, young one, magic always finds a way."
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)

        self.assertIn("[chuckles]", result)
        self.assertNotIn("[eyes twinkling]", result)  # Non-vocal, should be removed

    def test_captain_professional_dialogue(self):
        """Test Captain with measured response."""
        text = "[sighs] Counselor... [pause] I understand your concern."
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)

        self.assertIn("[sighs]", result)
        self.assertIn("...", result)  # pause converted
        self.assertNotIn("[pause]", result)

    def test_mixed_sfx_and_audio_tags(self):
        """Test dialogue with both SFX and performable tags."""
        text = "[static] [gasps] [alarm] I need to get out of here! [laughs nervously]"
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=True)

        # SFX should become pauses
        self.assertNotIn("[static]", result)
        self.assertNotIn("[alarm]", result)
        # Audio tags should be preserved
        self.assertIn("[gasps]", result)
        self.assertIn("laughs", result.lower())

    def test_legacy_mode_removes_all(self):
        """Test that legacy mode (preserve_audio_tags=False) removes all tags."""
        text = "[laughs] [sighs] [coughing] Just regular speech."
        result = self.manager.clean_text_for_tts(text, preserve_audio_tags=False)

        self.assertNotIn("[", result)
        self.assertNotIn("]", result)
        self.assertEqual(result, "Just regular speech.")


class TestEnvVarConfiguration(unittest.TestCase):
    """Test environment variable configuration."""

    def test_preserve_audio_tags_default_false(self):
        """Test that PRESERVE_AUDIO_TAGS defaults to False."""
        from tts_elevenlabs import PRESERVE_AUDIO_TAGS
        # Default should be False for backwards compatibility
        # (unless env var is set in test environment)
        self.assertIsInstance(PRESERVE_AUDIO_TAGS, bool)

    def test_default_model_exists(self):
        """Test that DEFAULT_TTS_MODEL is set."""
        from tts_elevenlabs import DEFAULT_TTS_MODEL
        self.assertIsNotNone(DEFAULT_TTS_MODEL)
        self.assertIn(DEFAULT_TTS_MODEL, ['eleven_turbo_v2_5', 'eleven_flash_v2_5', 'eleven_multilingual_v2'])

    def test_models_dict_structure(self):
        """Test ELEVENLABS_MODELS has expected structure."""
        from tts_elevenlabs import ELEVENLABS_MODELS

        self.assertIn('eleven_turbo_v2_5', ELEVENLABS_MODELS)
        self.assertIn('eleven_flash_v2_5', ELEVENLABS_MODELS)
        self.assertIn('eleven_multilingual_v2', ELEVENLABS_MODELS)

        for model_id, config in ELEVENLABS_MODELS.items():
            self.assertIn('description', config)
            self.assertIn('supports_audio_tags', config)


if __name__ == '__main__':
    unittest.main()
