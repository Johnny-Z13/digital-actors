"""
Unit tests for Database Encryption

Tests encryption/decryption of sensitive player data including:
- Personality profiles
- Relationship data
- Scene attempt data (conversation history)
- Key rotation scenarios
- Error handling
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from encryption_utils import (
    DecryptionError,
    EncryptionError,
    EncryptionKeyError,
    decrypt_data,
    encrypt_data,
    generate_key,
    is_encryption_enabled,
    rotate_key,
)
from player_memory import PlayerMemory


class TestEncryptionUtils(unittest.TestCase):
    """Test encryption utility functions."""

    def test_generate_key(self):
        """Test generating a new encryption key."""
        key = generate_key()
        self.assertIsInstance(key, str)
        self.assertGreater(len(key), 0)

    def test_generate_key_unique(self):
        """Test that generated keys are unique."""
        key1 = generate_key()
        key2 = generate_key()
        self.assertNotEqual(key1, key2)

    def test_encrypt_string(self):
        """Test encrypting a string."""
        key = generate_key()
        data = "sensitive information"
        encrypted = encrypt_data(data, key)

        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, data)
        self.assertGreater(len(encrypted), len(data))

    def test_encrypt_dict(self):
        """Test encrypting a dictionary."""
        key = generate_key()
        data = {"name": "Alice", "age": 30}
        encrypted = encrypt_data(data, key)

        self.assertIsInstance(encrypted, str)
        self.assertNotIn("Alice", encrypted)

    def test_encrypt_list(self):
        """Test encrypting a list."""
        key = generate_key()
        data = ["item1", "item2", "item3"]
        encrypted = encrypt_data(data, key)

        self.assertIsInstance(encrypted, str)
        self.assertNotIn("item1", encrypted)

    def test_encrypt_none(self):
        """Test encrypting None returns None."""
        key = generate_key()
        encrypted = encrypt_data(None, key)
        self.assertIsNone(encrypted)

    def test_encrypt_without_key(self):
        """Test that encryption fails without a key."""
        with self.assertRaises(EncryptionKeyError):
            encrypt_data("data", None)

    def test_encrypt_with_invalid_key(self):
        """Test that encryption fails with invalid key."""
        with self.assertRaises(EncryptionKeyError):
            encrypt_data("data", "invalid-key")

    def test_decrypt_string(self):
        """Test decrypting to string."""
        key = generate_key()
        original = "sensitive data"
        encrypted = encrypt_data(original, key)
        decrypted = decrypt_data(encrypted, key, str)

        self.assertEqual(decrypted, original)

    def test_decrypt_dict(self):
        """Test decrypting to dictionary."""
        key = generate_key()
        original = {"name": "Bob", "score": 100}
        encrypted = encrypt_data(original, key)
        decrypted = decrypt_data(encrypted, key, dict)

        self.assertEqual(decrypted, original)

    def test_decrypt_list(self):
        """Test decrypting to list."""
        key = generate_key()
        original = [1, 2, 3, 4, 5]
        encrypted = encrypt_data(original, key)
        decrypted = decrypt_data(encrypted, key, list)

        self.assertEqual(decrypted, original)

    def test_decrypt_int(self):
        """Test decrypting to integer."""
        key = generate_key()
        original = 42
        encrypted = encrypt_data(original, key)
        decrypted = decrypt_data(encrypted, key, int)

        self.assertEqual(decrypted, original)

    def test_decrypt_none(self):
        """Test decrypting None returns None."""
        key = generate_key()
        decrypted = decrypt_data(None, key, str)
        self.assertIsNone(decrypted)

    def test_decrypt_without_key(self):
        """Test that decryption fails without a key."""
        key = generate_key()
        encrypted = encrypt_data("data", key)

        with self.assertRaises(EncryptionKeyError):
            decrypt_data(encrypted, None, str)

    def test_decrypt_with_wrong_key(self):
        """Test that decryption fails with wrong key."""
        key1 = generate_key()
        key2 = generate_key()
        encrypted = encrypt_data("data", key1)

        with self.assertRaises(DecryptionError):
            decrypt_data(encrypted, key2, str)

    def test_decrypt_corrupted_data(self):
        """Test that decryption fails with corrupted data."""
        key = generate_key()
        corrupted = "corrupted-encrypted-data"

        with self.assertRaises(DecryptionError):
            decrypt_data(corrupted, key, str)

    def test_rotate_key(self):
        """Test key rotation."""
        old_key = generate_key()
        new_key = generate_key()
        original = "sensitive data"

        # Encrypt with old key
        encrypted_old = encrypt_data(original, old_key)

        # Rotate to new key
        encrypted_new = rotate_key(old_key, new_key, encrypted_old)

        # Should decrypt with new key
        decrypted = decrypt_data(encrypted_new, new_key, str)
        self.assertEqual(decrypted, original)

        # Should NOT decrypt with old key
        with self.assertRaises(DecryptionError):
            decrypt_data(encrypted_new, old_key, str)

    def test_rotate_key_without_old_key(self):
        """Test that key rotation fails without old key."""
        new_key = generate_key()
        encrypted = "encrypted-data"

        with self.assertRaises(EncryptionKeyError):
            rotate_key(None, new_key, encrypted)

    def test_rotate_key_without_new_key(self):
        """Test that key rotation fails without new key."""
        old_key = generate_key()
        encrypted = encrypt_data("data", old_key)

        with self.assertRaises(EncryptionKeyError):
            rotate_key(old_key, None, encrypted)

    def test_is_encryption_enabled_with_valid_key(self):
        """Test checking if encryption is enabled with valid key."""
        key = generate_key()
        self.assertTrue(is_encryption_enabled(key))

    def test_is_encryption_enabled_without_key(self):
        """Test checking if encryption is enabled without key."""
        self.assertFalse(is_encryption_enabled(None))
        self.assertFalse(is_encryption_enabled(""))

    def test_is_encryption_enabled_with_invalid_key(self):
        """Test checking if encryption is enabled with invalid key."""
        self.assertFalse(is_encryption_enabled("invalid-key"))


class TestPlayerMemoryEncryption(unittest.TestCase):
    """Test PlayerMemory with encryption enabled."""

    def setUp(self):
        """Set up test fixtures with encryption enabled."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_player_memory.db")
        self.encryption_key = generate_key()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_personality_encrypted_in_database(self):
        """Test that personality data is encrypted in database."""
        with patch("player_memory.DB_ENCRYPTION_KEY", self.encryption_key):
            memory = PlayerMemory("player_encrypted", self.db_path)

            # Modify personality
            memory.personality_profile["impulsiveness"] = 75
            memory.personality_profile["cooperation"] = 60

            # Save to database
            initial_state = {"oxygen": 100, "trust": 0}
            memory.start_scene("scene_test", "engineer", initial_state)

            final_state = {
                "oxygen": 80,
                "trust": 10,
                "correct_actions": 5,
                "incorrect_actions": 1,
            }

            memory.end_scene("success", final_state)

            # Check database directly - values should be encrypted (not plaintext)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT impulsiveness, cooperation
                    FROM personality_profiles WHERE player_id = ?
                """,
                    ("player_encrypted",),
                )
                result = cursor.fetchone()

            # Should not be plaintext integers
            self.assertNotEqual(result[0], "75")
            self.assertNotEqual(result[1], "60")
            # Should be encrypted strings
            self.assertIsInstance(result[0], str)
            self.assertIsInstance(result[1], str)
            # Should be longer than plaintext due to encryption
            self.assertGreater(len(result[0]), 2)

    def test_personality_decrypted_on_load(self):
        """Test that personality data is correctly decrypted when loaded."""
        with patch("player_memory.DB_ENCRYPTION_KEY", self.encryption_key):
            # Create and save player
            memory1 = PlayerMemory("player_decrypt_test", self.db_path)
            memory1.personality_profile["impulsiveness"] = 85
            memory1.personality_profile["cooperation"] = 70

            initial_state = {"oxygen": 100, "trust": 0}
            memory1.start_scene("scene_test", "engineer", initial_state)
            final_state = {
                "oxygen": 80,
                "trust": 10,
                "correct_actions": 5,
                "incorrect_actions": 1,
            }
            memory1.end_scene("success", final_state)

            # Load player again
            memory2 = PlayerMemory("player_decrypt_test", self.db_path)

            # Values should be correctly decrypted
            # Note: impulsiveness may decrease by 1 during end_scene due to no interruptions
            self.assertIn(memory2.personality_profile["impulsiveness"], [85, 84])
            # Cooperation increases by 3 for success with no interruptions
            self.assertEqual(memory2.personality_profile["cooperation"], 73)

    def test_relationships_encrypted_in_database(self):
        """Test that relationship data is encrypted in database."""
        with patch("player_memory.DB_ENCRYPTION_KEY", self.encryption_key):
            memory = PlayerMemory("player_relationship_enc", self.db_path)

            initial_state = {"oxygen": 100, "trust": 0}
            memory.start_scene("scene_test", "engineer", initial_state)

            final_state = {
                "oxygen": 80,
                "trust": 25,
                "correct_actions": 7,
                "incorrect_actions": 1,
            }

            memory.end_scene("success", final_state)

            # Check database directly
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT trust, familiarity
                    FROM relationships WHERE player_id = ? AND character_id = ?
                """,
                    ("player_relationship_enc", "engineer"),
                )
                result = cursor.fetchone()

            # Should be encrypted
            self.assertNotEqual(result[0], "25")
            self.assertNotEqual(result[1], "1")
            self.assertIsInstance(result[0], str)
            self.assertIsInstance(result[1], str)
            self.assertGreater(len(result[0]), 2)

    def test_relationships_decrypted_on_load(self):
        """Test that relationship data is correctly decrypted when loaded."""
        with patch("player_memory.DB_ENCRYPTION_KEY", self.encryption_key):
            # Create and save relationship
            memory1 = PlayerMemory("player_rel_decrypt", self.db_path)

            initial_state = {"oxygen": 100, "trust": 0}
            memory1.start_scene("scene_test", "engineer", initial_state)
            final_state = {
                "oxygen": 80,
                "trust": 35,
                "correct_actions": 8,
                "incorrect_actions": 0,
            }
            memory1.end_scene("success", final_state)

            # Load player again
            memory2 = PlayerMemory("player_rel_decrypt", self.db_path)

            # Relationship should be correctly decrypted
            self.assertIn("engineer", memory2.relationships)
            self.assertEqual(memory2.relationships["engineer"]["trust"], 35)
            self.assertEqual(memory2.relationships["engineer"]["familiarity"], 1)

    def test_scene_data_encrypted_in_database(self):
        """Test that scene attempt data is encrypted in database."""
        with patch("player_memory.DB_ENCRYPTION_KEY", self.encryption_key):
            memory = PlayerMemory("player_scene_enc", self.db_path)

            initial_state = {"oxygen": 100, "trust": 0}
            memory.start_scene("scene_test", "engineer", initial_state)

            final_state = {
                "oxygen": 75,
                "trust": 15,
                "correct_actions": 6,
                "incorrect_actions": 2,
                "custom_data": "sensitive information",
            }

            memory.end_scene("success", final_state)

            # Check database directly
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT data FROM scene_attempts WHERE player_id = ?
                """,
                    ("player_scene_enc",),
                )
                result = cursor.fetchone()

            # Should be encrypted - not plaintext JSON
            self.assertNotIn("sensitive information", result[0])
            self.assertNotIn("custom_data", result[0])
            # Should not start with { (not JSON)
            self.assertNotEqual(result[0][0], "{")

    def test_encryption_disabled_stores_plaintext(self):
        """Test that data is stored as plaintext when encryption is disabled."""
        with patch("player_memory.DB_ENCRYPTION_KEY", None):
            memory = PlayerMemory("player_no_enc", self.db_path)

            memory.personality_profile["impulsiveness"] = 65

            initial_state = {"oxygen": 100, "trust": 0}
            memory.start_scene("scene_test", "engineer", initial_state)
            final_state = {
                "oxygen": 80,
                "trust": 10,
                "correct_actions": 5,
                "incorrect_actions": 1,
            }
            memory.end_scene("success", final_state)

            # Check database - should be plaintext
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT impulsiveness FROM personality_profiles WHERE player_id = ?
                """,
                    ("player_no_enc",),
                )
                result = cursor.fetchone()

            # Should be plaintext string representation
            # Note: impulsiveness may decrease by 1 during end_scene due to no interruptions
            self.assertIn(result[0], ["65", "64"])

    def test_mixed_encrypted_unencrypted_data(self):
        """Test handling data created with and without encryption."""
        # Create data without encryption
        with patch("player_memory.DB_ENCRYPTION_KEY", None):
            memory1 = PlayerMemory("player_mixed", self.db_path)
            memory1.personality_profile["impulsiveness"] = 55

            initial_state = {"oxygen": 100, "trust": 0}
            memory1.start_scene("scene_test", "engineer", initial_state)
            final_state = {
                "oxygen": 80,
                "trust": 10,
                "correct_actions": 5,
                "incorrect_actions": 1,
            }
            memory1.end_scene("success", final_state)

        # Load with encryption enabled - should gracefully handle plaintext
        with patch("player_memory.DB_ENCRYPTION_KEY", self.encryption_key):
            memory2 = PlayerMemory("player_mixed", self.db_path)
            # Should fall back to defaults on decryption error
            self.assertIn(memory2.personality_profile["impulsiveness"], [50, 55])

    def test_decryption_failure_falls_back_to_defaults(self):
        """Test that decryption failure falls back to default values."""
        # Create data with one key
        with patch("player_memory.DB_ENCRYPTION_KEY", self.encryption_key):
            memory1 = PlayerMemory("player_decrypt_fail", self.db_path)
            memory1.personality_profile["impulsiveness"] = 80

            initial_state = {"oxygen": 100, "trust": 0}
            memory1.start_scene("scene_test", "engineer", initial_state)
            final_state = {
                "oxygen": 80,
                "trust": 10,
                "correct_actions": 5,
                "incorrect_actions": 1,
            }
            memory1.end_scene("success", final_state)

        # Try to load with different key - should fall back to defaults
        different_key = generate_key()
        with patch("player_memory.DB_ENCRYPTION_KEY", different_key):
            memory2 = PlayerMemory("player_decrypt_fail", self.db_path)
            # Should fall back to default
            self.assertEqual(memory2.personality_profile["impulsiveness"], 50)
            self.assertEqual(memory2.personality_profile["cooperation"], 50)


class TestEncryptionKeyRotation(unittest.TestCase):
    """Test encryption key rotation scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_player_memory.db")
        self.old_key = generate_key()
        self.new_key = generate_key()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_rotate_encrypted_personality_data(self):
        """Test rotating encryption key for personality data."""
        # Create data with old key
        with patch("player_memory.DB_ENCRYPTION_KEY", self.old_key):
            memory = PlayerMemory("player_rotate", self.db_path)
            memory.personality_profile["impulsiveness"] = 90

            initial_state = {"oxygen": 100, "trust": 0}
            memory.start_scene("scene_test", "engineer", initial_state)
            final_state = {
                "oxygen": 80,
                "trust": 10,
                "correct_actions": 5,
                "incorrect_actions": 1,
            }
            memory.end_scene("success", final_state)

        # Manually rotate the key in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT impulsiveness, cooperation, problem_solving, patience
                FROM personality_profiles WHERE player_id = ?
            """,
                ("player_rotate",),
            )
            result = cursor.fetchone()

            # Rotate each field
            rotated = [rotate_key(self.old_key, self.new_key, field) for field in result]

            cursor.execute(
                """
                UPDATE personality_profiles
                SET impulsiveness = ?, cooperation = ?, problem_solving = ?, patience = ?
                WHERE player_id = ?
            """,
                (*rotated, "player_rotate"),
            )
            conn.commit()

        # Load with new key - should work
        with patch("player_memory.DB_ENCRYPTION_KEY", self.new_key):
            memory2 = PlayerMemory("player_rotate", self.db_path)
            # Note: impulsiveness may have decreased by 1 during end_scene
            self.assertIn(memory2.personality_profile["impulsiveness"], [90, 89])


class TestEncryptionErrorHandling(unittest.TestCase):
    """Test error handling for encryption operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_player_memory.db")
        self.key = generate_key()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_encryption_error_during_save(self):
        """Test handling encryption errors during save operations."""
        with patch("player_memory.DB_ENCRYPTION_KEY", self.key):
            memory = PlayerMemory("player_enc_error", self.db_path)

            initial_state = {"oxygen": 100, "trust": 0}
            memory.start_scene("scene_test", "engineer", initial_state)

            final_state = {
                "oxygen": 80,
                "trust": 10,
                "correct_actions": 5,
                "incorrect_actions": 1,
            }

            # Mock _encrypt_field to fail
            with patch.object(memory, "_encrypt_field", side_effect=EncryptionError("Mock error")):
                # Should raise DatabaseError wrapping EncryptionError
                from exceptions import DatabaseError

                with self.assertRaises(DatabaseError):
                    memory.end_scene("success", final_state)


if __name__ == "__main__":
    unittest.main()
