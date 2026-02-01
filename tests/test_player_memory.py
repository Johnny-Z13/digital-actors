"""
Unit tests for PlayerMemory

Tests player profile management, interaction recording, personality trait updates,
conversation history storage, and edge cases.
"""

import sys
import os

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from player_memory import PlayerMemory, get_or_create_player_memory
from exceptions import (
    DatabaseError,
    DatabaseIntegrityError,
    DatabaseOperationalError
)
from constants import (
    PERSONALITY_IMPULSIVENESS_INCREMENT,
    PERSONALITY_IMPULSIVENESS_DECREMENT,
    PERSONALITY_PATIENCE_INCREMENT,
    PERSONALITY_PATIENCE_DECREMENT,
    PERSONALITY_COOPERATION_INCREMENT,
    PERSONALITY_COOPERATION_DECREMENT,
    PERSONALITY_PROBLEM_SOLVING_INCREMENT,
    PERSONALITY_PROBLEM_SOLVING_DECREMENT,
    PERSONALITY_HIGH_THRESHOLD,
    PERSONALITY_MID_THRESHOLD,
    TRUST_HIGH_THRESHOLD,
    TRUST_POSITIVE_THRESHOLD,
    TRUST_NEGATIVE_THRESHOLD,
    TRUST_LOW_THRESHOLD,
    FAMILIARITY_NEW,
    FAMILIARITY_MODERATE,
    HINT_SCENE_ATTEMPTS_THRESHOLD,
)


class TestPlayerMemoryInitialization(unittest.TestCase):
    """Test PlayerMemory initialization and database setup."""

    def setUp(self):
        """Set up test fixtures with temporary database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_player_memory.db")

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_new_player_creation(self):
        """Test creating a new player profile."""
        memory = PlayerMemory("player_001", self.db_path)

        self.assertEqual(memory.player_id, "player_001")
        self.assertEqual(memory.total_scenes_played, 0)
        self.assertEqual(memory.total_successes, 0)
        self.assertEqual(memory.total_failures, 0)
        self.assertEqual(memory.personality_profile['impulsiveness'], 50)
        self.assertEqual(memory.personality_profile['cooperation'], 50)
        self.assertEqual(memory.personality_profile['patience'], 50)
        self.assertEqual(memory.personality_profile['problem_solving'], 50)
        self.assertEqual(len(memory.relationships), 0)

    def test_database_tables_created(self):
        """Test that all required database tables are created."""
        memory = PlayerMemory("player_001", self.db_path)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check players table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players'")
            self.assertIsNotNone(cursor.fetchone())

            # Check sessions table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
            self.assertIsNotNone(cursor.fetchone())

            # Check scene_attempts table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scene_attempts'")
            self.assertIsNotNone(cursor.fetchone())

            # Check personality_profiles table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='personality_profiles'")
            self.assertIsNotNone(cursor.fetchone())

            # Check relationships table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='relationships'")
            self.assertIsNotNone(cursor.fetchone())

    def test_existing_player_loaded(self):
        """Test loading an existing player from database."""
        # Create initial player
        memory1 = PlayerMemory("player_002", self.db_path)

        # Modify personality
        memory1.personality_profile['impulsiveness'] = 75
        memory1.personality_profile['cooperation'] = 60

        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE personality_profiles
                SET impulsiveness = ?, cooperation = ?
                WHERE player_id = ?
            ''', (75, 60, "player_002"))
            conn.commit()

        # Load player again
        memory2 = PlayerMemory("player_002", self.db_path)

        # Verify personality was loaded
        self.assertEqual(memory2.personality_profile['impulsiveness'], 75)
        self.assertEqual(memory2.personality_profile['cooperation'], 60)

    def test_player_record_created_in_database(self):
        """Test that player record is created in players table."""
        memory = PlayerMemory("player_003", self.db_path)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT player_id FROM players WHERE player_id = ?", ("player_003",))
            result = cursor.fetchone()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], "player_003")

    def test_personality_profile_created_in_database(self):
        """Test that personality profile is created in database."""
        memory = PlayerMemory("player_004", self.db_path)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT impulsiveness, cooperation, problem_solving, patience
                FROM personality_profiles WHERE player_id = ?
            ''', ("player_004",))
            result = cursor.fetchone()

        self.assertIsNotNone(result)
        # Values are stored as TEXT (string representation) to support encryption
        self.assertEqual(result[0], "50")  # impulsiveness
        self.assertEqual(result[1], "50")  # cooperation
        self.assertEqual(result[2], "50")  # problem_solving
        self.assertEqual(result[3], "50")  # patience


class TestSceneRecording(unittest.TestCase):
    """Test scene attempt recording and tracking."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_player_memory.db")
        self.memory = PlayerMemory("player_scene_test", self.db_path)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_start_scene(self):
        """Test starting a new scene."""
        initial_state = {
            'oxygen': 100,
            'trust': 0,
            'correct_actions': 0,
            'incorrect_actions': 0
        }

        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        self.assertEqual(self.memory.current_scene_data['scene_id'], "scene_airlock")
        self.assertEqual(self.memory.current_scene_data['character_id'], "engineer")
        self.assertEqual(self.memory.current_scene_data['initial_state']['oxygen'], 100)
        self.assertIn('started_at', self.memory.current_scene_data)

    def test_end_scene_success(self):
        """Test ending a scene with success outcome."""
        initial_state = {
            'oxygen': 100,
            'trust': 0,
            'correct_actions': 0,
            'incorrect_actions': 0
        }

        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        final_state = {
            'oxygen': 80,
            'trust': 10,
            'correct_actions': 5,
            'incorrect_actions': 1
        }

        self.memory.end_scene("success", final_state)

        # Verify stats updated
        self.assertEqual(self.memory.total_scenes_played, 1)
        self.assertEqual(self.memory.total_successes, 1)
        self.assertEqual(self.memory.total_failures, 0)
        self.assertEqual(self.memory.scene_attempts.get("scene_airlock"), 1)

        # Verify scene data cleared
        self.assertEqual(self.memory.current_scene_data, {})

    def test_end_scene_failure(self):
        """Test ending a scene with failure outcome."""
        initial_state = {'oxygen': 100, 'trust': 0}

        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        final_state = {
            'oxygen': 0,
            'trust': -20,
            'correct_actions': 1,
            'incorrect_actions': 5
        }

        self.memory.end_scene("failure", final_state)

        # Verify stats updated
        self.assertEqual(self.memory.total_scenes_played, 1)
        self.assertEqual(self.memory.total_successes, 0)
        self.assertEqual(self.memory.total_failures, 1)

    def test_scene_attempt_recorded_in_database(self):
        """Test that scene attempt is recorded in database."""
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        final_state = {
            'oxygen': 80,
            'trust': 10,
            'correct_actions': 5,
            'incorrect_actions': 1
        }

        self.memory.end_scene("success", final_state)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT scene_id, character_id, outcome, final_trust,
                       correct_actions, incorrect_actions
                FROM scene_attempts WHERE player_id = ?
            ''', (self.memory.player_id,))
            result = cursor.fetchone()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], "scene_airlock")
        self.assertEqual(result[1], "engineer")
        self.assertEqual(result[2], "success")
        self.assertEqual(result[3], 10)
        self.assertEqual(result[4], 5)
        self.assertEqual(result[5], 1)

    def test_multiple_scene_attempts(self):
        """Test tracking multiple attempts at same scene."""
        for i in range(3):
            initial_state = {'oxygen': 100, 'trust': 0}
            self.memory.start_scene("scene_airlock", "engineer", initial_state)

            final_state = {
                'oxygen': 80,
                'trust': 5,
                'correct_actions': 3,
                'incorrect_actions': 2
            }

            self.memory.end_scene("success" if i == 2 else "failure", final_state)

        self.assertEqual(self.memory.scene_attempts.get("scene_airlock"), 3)
        self.assertEqual(self.memory.total_scenes_played, 3)

    def test_record_interruption(self):
        """Test recording player interruptions."""
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        self.memory.record_interruption()
        self.memory.record_interruption()

        self.assertEqual(self.memory.current_scene_data['interrupted_count'], 2)

    def test_record_rapid_actions(self):
        """Test recording rapid button mashing."""
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        self.memory.record_rapid_actions()
        self.memory.record_rapid_actions()
        self.memory.record_rapid_actions()

        self.assertEqual(self.memory.current_scene_data['rapid_action_count'], 3)

    def test_record_patient_wait(self):
        """Test recording patient waiting behavior."""
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        initial_patience = self.memory.personality_profile['patience']
        initial_impulsiveness = self.memory.personality_profile['impulsiveness']

        self.memory.record_patient_wait()

        # Patience should increase
        self.assertEqual(
            self.memory.personality_profile['patience'],
            min(100, initial_patience + PERSONALITY_PATIENCE_INCREMENT)
        )

        # Impulsiveness should decrease
        self.assertEqual(
            self.memory.personality_profile['impulsiveness'],
            max(0, initial_impulsiveness - PERSONALITY_IMPULSIVENESS_DECREMENT)
        )


class TestPersonalityUpdates(unittest.TestCase):
    """Test personality profile updates based on behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_player_memory.db")
        self.memory = PlayerMemory("player_personality_test", self.db_path)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_impulsiveness_increases_with_interruptions(self):
        """Test that interruptions increase impulsiveness."""
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_test", "engineer", initial_state)

        # Record multiple interruptions
        self.memory.record_interruption()
        self.memory.record_interruption()
        self.memory.record_interruption()

        initial_impulsiveness = self.memory.personality_profile['impulsiveness']

        final_state = {
            'oxygen': 80,
            'trust': 0,
            'correct_actions': 2,
            'incorrect_actions': 1
        }

        self.memory.end_scene("success", final_state)

        # Impulsiveness should have increased
        expected = min(100, initial_impulsiveness + (3 * PERSONALITY_IMPULSIVENESS_INCREMENT))
        self.assertEqual(self.memory.personality_profile['impulsiveness'], expected)

    def test_impulsiveness_decreases_without_interruptions(self):
        """Test that no interruptions decrease impulsiveness."""
        # Set impulsiveness higher initially
        self.memory.personality_profile['impulsiveness'] = 70

        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_test", "engineer", initial_state)

        final_state = {
            'oxygen': 80,
            'trust': 10,
            'correct_actions': 5,
            'incorrect_actions': 1
        }

        self.memory.end_scene("success", final_state)

        # Impulsiveness should have decreased
        expected = max(0, 70 - PERSONALITY_IMPULSIVENESS_DECREMENT)
        self.assertEqual(self.memory.personality_profile['impulsiveness'], expected)

    def test_patience_decreases_with_rapid_actions(self):
        """Test that rapid actions decrease patience."""
        initial_patience = self.memory.personality_profile['patience']

        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_test", "engineer", initial_state)

        # Record rapid actions
        self.memory.record_rapid_actions()
        self.memory.record_rapid_actions()

        final_state = {
            'oxygen': 80,
            'trust': 0,
            'correct_actions': 2,
            'incorrect_actions': 1
        }

        self.memory.end_scene("success", final_state)

        # Patience should have decreased
        expected = max(0, initial_patience - (2 * PERSONALITY_PATIENCE_DECREMENT))
        self.assertEqual(self.memory.personality_profile['patience'], expected)

    def test_patience_increases_without_interruptions(self):
        """Test that patience increases without interruptions or rapid actions."""
        initial_patience = self.memory.personality_profile['patience']

        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_test", "engineer", initial_state)

        final_state = {
            'oxygen': 80,
            'trust': 10,
            'correct_actions': 5,
            'incorrect_actions': 1
        }

        self.memory.end_scene("success", final_state)

        # Patience should have increased
        expected = min(100, initial_patience + PERSONALITY_PATIENCE_INCREMENT)
        self.assertEqual(self.memory.personality_profile['patience'], expected)

    def test_cooperation_increases_on_success_without_interruptions(self):
        """Test that cooperation increases with success and no interruptions."""
        initial_cooperation = self.memory.personality_profile['cooperation']

        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_test", "engineer", initial_state)

        final_state = {
            'oxygen': 80,
            'trust': 10,
            'correct_actions': 5,
            'incorrect_actions': 1
        }

        self.memory.end_scene("success", final_state)

        # Cooperation should have increased
        expected = min(100, initial_cooperation + PERSONALITY_COOPERATION_INCREMENT)
        self.assertEqual(self.memory.personality_profile['cooperation'], expected)

    def test_cooperation_decreases_with_many_interruptions(self):
        """Test that cooperation decreases with many interruptions."""
        initial_cooperation = self.memory.personality_profile['cooperation']

        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_test", "engineer", initial_state)

        # Record many interruptions
        for _ in range(4):
            self.memory.record_interruption()

        final_state = {
            'oxygen': 80,
            'trust': 0,
            'correct_actions': 2,
            'incorrect_actions': 3
        }

        self.memory.end_scene("failure", final_state)

        # Cooperation should have decreased
        expected = max(0, initial_cooperation - PERSONALITY_COOPERATION_DECREMENT)
        self.assertEqual(self.memory.personality_profile['cooperation'], expected)

    def test_problem_solving_increases_with_correct_actions(self):
        """Test that problem solving increases with more correct than incorrect actions."""
        initial_problem_solving = self.memory.personality_profile['problem_solving']

        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_test", "engineer", initial_state)

        final_state = {
            'oxygen': 80,
            'trust': 10,
            'correct_actions': 8,
            'incorrect_actions': 2
        }

        self.memory.end_scene("success", final_state)

        # Problem solving should have increased
        expected = min(100, initial_problem_solving + PERSONALITY_PROBLEM_SOLVING_INCREMENT)
        self.assertEqual(self.memory.personality_profile['problem_solving'], expected)

    def test_problem_solving_decreases_with_many_incorrect_actions(self):
        """Test that problem solving decreases with many incorrect actions."""
        initial_problem_solving = self.memory.personality_profile['problem_solving']

        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_test", "engineer", initial_state)

        final_state = {
            'oxygen': 40,
            'trust': -10,
            'correct_actions': 1,
            'incorrect_actions': 6
        }

        self.memory.end_scene("failure", final_state)

        # Problem solving should have decreased (incorrect > correct * 2)
        expected = max(0, initial_problem_solving - PERSONALITY_PROBLEM_SOLVING_DECREMENT)
        self.assertEqual(self.memory.personality_profile['problem_solving'], expected)

    def test_personality_clamped_at_boundaries(self):
        """Test that personality values are clamped between 0 and 100."""
        # Set extreme initial values
        self.memory.personality_profile['impulsiveness'] = 95
        self.memory.personality_profile['patience'] = 5

        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_test", "engineer", initial_state)

        # Max interruptions and rapid actions
        for _ in range(10):
            self.memory.record_interruption()
            self.memory.record_rapid_actions()

        final_state = {
            'oxygen': 20,
            'trust': -30,
            'correct_actions': 0,
            'incorrect_actions': 10
        }

        self.memory.end_scene("failure", final_state)

        # Values should be clamped
        self.assertGreaterEqual(self.memory.personality_profile['impulsiveness'], 0)
        self.assertLessEqual(self.memory.personality_profile['impulsiveness'], 100)
        self.assertGreaterEqual(self.memory.personality_profile['patience'], 0)
        self.assertLessEqual(self.memory.personality_profile['patience'], 100)

    def test_personality_updated_in_database(self):
        """Test that personality updates are saved to database."""
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_test", "engineer", initial_state)

        self.memory.record_interruption()

        final_state = {
            'oxygen': 80,
            'trust': 5,
            'correct_actions': 3,
            'incorrect_actions': 1
        }

        self.memory.end_scene("success", final_state)

        # Verify in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT impulsiveness FROM personality_profiles WHERE player_id = ?
            ''', (self.memory.player_id,))
            result = cursor.fetchone()

        # Values stored as TEXT (string), convert for comparison
        self.assertEqual(int(result[0]), self.memory.personality_profile['impulsiveness'])


class TestRelationshipManagement(unittest.TestCase):
    """Test relationship tracking with characters."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_player_memory.db")
        self.memory = PlayerMemory("player_relationship_test", self.db_path)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_new_relationship_created(self):
        """Test creating a new relationship with a character."""
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        final_state = {
            'oxygen': 80,
            'trust': 15,
            'correct_actions': 5,
            'incorrect_actions': 1
        }

        self.memory.end_scene("success", final_state)

        # Verify relationship created
        self.assertIn("engineer", self.memory.relationships)
        self.assertEqual(self.memory.relationships["engineer"]['trust'], 15)
        self.assertEqual(self.memory.relationships["engineer"]['familiarity'], 1)

    def test_relationship_updated(self):
        """Test updating existing relationship."""
        # First interaction
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        final_state = {
            'oxygen': 80,
            'trust': 10,
            'correct_actions': 5,
            'incorrect_actions': 1
        }

        self.memory.end_scene("success", final_state)

        # Second interaction
        self.memory.start_scene("scene_repair", "engineer", initial_state)

        final_state = {
            'oxygen': 70,
            'trust': 15,
            'correct_actions': 6,
            'incorrect_actions': 0
        }

        self.memory.end_scene("success", final_state)

        # Verify relationship updated
        self.assertEqual(self.memory.relationships["engineer"]['trust'], 25)  # 10 + 15
        self.assertEqual(self.memory.relationships["engineer"]['familiarity'], 2)

    def test_negative_trust(self):
        """Test handling negative trust values."""
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        final_state = {
            'oxygen': 20,
            'trust': -30,
            'correct_actions': 1,
            'incorrect_actions': 8
        }

        self.memory.end_scene("failure", final_state)

        self.assertEqual(self.memory.relationships["engineer"]['trust'], -30)

    def test_relationship_saved_to_database(self):
        """Test that relationships are saved to database."""
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        final_state = {
            'oxygen': 80,
            'trust': 10,
            'correct_actions': 5,
            'incorrect_actions': 1
        }

        self.memory.end_scene("success", final_state)

        # Verify in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT character_id, trust, familiarity
                FROM relationships WHERE player_id = ?
            ''', (self.memory.player_id,))
            result = cursor.fetchone()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], "engineer")
        # Values stored as TEXT (string), convert for comparison
        self.assertEqual(int(result[1]), 10)
        self.assertEqual(int(result[2]), 1)

    def test_relationship_loaded_from_database(self):
        """Test loading relationships from database."""
        # Create relationship
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        final_state = {'oxygen': 80, 'trust': 20, 'correct_actions': 5, 'incorrect_actions': 1}
        self.memory.end_scene("success", final_state)

        # Create new memory instance (should load from database)
        memory2 = PlayerMemory("player_relationship_test", self.db_path)

        self.assertIn("engineer", memory2.relationships)
        self.assertEqual(memory2.relationships["engineer"]['trust'], 20)
        self.assertEqual(memory2.relationships["engineer"]['familiarity'], 1)

    def test_multiple_character_relationships(self):
        """Test managing relationships with multiple characters."""
        # Interaction with engineer
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)
        final_state = {'oxygen': 80, 'trust': 10, 'correct_actions': 5, 'incorrect_actions': 1}
        self.memory.end_scene("success", final_state)

        # Interaction with judge
        self.memory.start_scene("scene_trial", "judge", initial_state)
        final_state = {'oxygen': 80, 'trust': -5, 'correct_actions': 2, 'incorrect_actions': 3}
        self.memory.end_scene("failure", final_state)

        # Verify both relationships exist
        self.assertIn("engineer", self.memory.relationships)
        self.assertIn("judge", self.memory.relationships)
        self.assertEqual(self.memory.relationships["engineer"]['trust'], 10)
        self.assertEqual(self.memory.relationships["judge"]['trust'], -5)


class TestContextGeneration(unittest.TestCase):
    """Test context generation for LLM prompts."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_player_memory.db")
        self.memory = PlayerMemory("player_context_test", self.db_path)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_character_context_first_meeting(self):
        """Test context for first meeting with character."""
        context = self.memory.get_character_context("engineer")
        self.assertIn("first time meeting", context.lower())

    def test_character_context_after_one_meeting(self):
        """Test context after one previous meeting."""
        # Create one interaction
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)
        final_state = {'oxygen': 80, 'trust': 10, 'correct_actions': 5, 'incorrect_actions': 1}
        self.memory.end_scene("success", final_state)

        context = self.memory.get_character_context("engineer")
        self.assertIn("once before", context.lower())

    def test_character_context_high_trust(self):
        """Test context with high trust level."""
        # Manually set high trust
        self.memory.relationships["engineer"] = {
            'trust': TRUST_HIGH_THRESHOLD + 10,
            'familiarity': 5
        }

        context = self.memory.get_character_context("engineer")
        self.assertIn("trust", context.lower())

    def test_character_context_low_trust(self):
        """Test context with low trust level."""
        # Manually set low trust
        self.memory.relationships["engineer"] = {
            'trust': TRUST_LOW_THRESHOLD - 10,
            'familiarity': 3
        }

        context = self.memory.get_character_context("engineer")
        self.assertIn("doubt", context.lower())

    def test_personality_summary_impulsive(self):
        """Test personality summary for impulsive player."""
        self.memory.personality_profile['impulsiveness'] = PERSONALITY_HIGH_THRESHOLD + 10

        summary = self.memory.get_personality_summary()
        self.assertIn("IMPULSIVE", summary.upper())

    def test_personality_summary_patient(self):
        """Test personality summary for patient player."""
        self.memory.personality_profile['patience'] = PERSONALITY_HIGH_THRESHOLD + 10

        summary = self.memory.get_personality_summary()
        self.assertIn("PATIENT", summary.upper())

    def test_personality_summary_cooperative(self):
        """Test personality summary for cooperative player."""
        self.memory.personality_profile['cooperation'] = PERSONALITY_HIGH_THRESHOLD + 10

        summary = self.memory.get_personality_summary()
        self.assertIn("COOPERATIVE", summary.upper())

    def test_personality_summary_skilled(self):
        """Test personality summary for skilled player."""
        self.memory.personality_profile['problem_solving'] = PERSONALITY_HIGH_THRESHOLD + 10

        summary = self.memory.get_personality_summary()
        self.assertIn("SKILLED", summary.upper())

    def test_full_context_for_llm(self):
        """Test complete context generation for LLM."""
        # Set up some data
        self.memory.personality_profile['impulsiveness'] = 70
        self.memory.total_scenes_played = 5
        self.memory.total_successes = 3

        # Create relationship
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)
        final_state = {'oxygen': 80, 'trust': 15, 'correct_actions': 5, 'incorrect_actions': 1}
        self.memory.end_scene("success", final_state)

        context = self.memory.get_full_context_for_llm("engineer")

        self.assertIn("PLAYER MEMORY", context)
        self.assertIn("Relationship", context)
        self.assertIn("Statistics", context)
        # end_scene increments total_scenes_played, so 5 + 1 = 6
        self.assertIn("Total scenes played: 6", context)


class TestUtilityMethods(unittest.TestCase):
    """Test utility methods for hints and difficulty."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_player_memory.db")
        self.memory = PlayerMemory("player_utility_test", self.db_path)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_should_give_hint_false_initially(self):
        """Test that hints are not given initially."""
        result = self.memory.should_give_hint("scene_airlock")
        self.assertFalse(result)

    def test_should_give_hint_after_threshold(self):
        """Test that hints are given after threshold attempts."""
        # Play scene multiple times
        for _ in range(HINT_SCENE_ATTEMPTS_THRESHOLD):
            initial_state = {'oxygen': 100, 'trust': 0}
            self.memory.start_scene("scene_airlock", "engineer", initial_state)
            final_state = {'oxygen': 20, 'trust': -10, 'correct_actions': 1, 'incorrect_actions': 5}
            self.memory.end_scene("failure", final_state)

        result = self.memory.should_give_hint("scene_airlock")
        self.assertTrue(result)

    def test_difficulty_recommendation_normal_initially(self):
        """Test that difficulty is normal for new players."""
        result = self.memory.get_difficulty_recommendation()
        self.assertEqual(result, "normal")

    def test_difficulty_recommendation_harder(self):
        """Test difficulty recommendation for skilled players."""
        # Simulate high success rate
        self.memory.total_scenes_played = 10
        self.memory.total_successes = 9

        result = self.memory.get_difficulty_recommendation()
        self.assertEqual(result, "harder")

    def test_difficulty_recommendation_easier(self):
        """Test difficulty recommendation for struggling players."""
        # Simulate low success rate
        self.memory.total_scenes_played = 10
        self.memory.total_successes = 2

        result = self.memory.get_difficulty_recommendation()
        self.assertEqual(result, "easier")

    def test_difficulty_recommendation_normal_moderate(self):
        """Test difficulty recommendation for moderate players."""
        # Simulate moderate success rate
        self.memory.total_scenes_played = 10
        self.memory.total_successes = 5

        result = self.memory.get_difficulty_recommendation()
        self.assertEqual(result, "normal")


class TestErrorHandling(unittest.TestCase):
    """Test error handling for database operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_player_memory.db")

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_database_integrity_error_on_init(self):
        """Test handling of database integrity errors during initialization."""
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.execute.side_effect = sqlite3.IntegrityError("Test integrity error")
            mock_connect.return_value.__enter__.return_value = mock_conn

            with self.assertRaises(DatabaseIntegrityError):
                PlayerMemory("test_player", self.db_path)

    def test_database_operational_error_on_init(self):
        """Test handling of database operational errors during initialization."""
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.execute.side_effect = sqlite3.OperationalError("Database is locked")
            mock_connect.return_value.__enter__.return_value = mock_conn

            with self.assertRaises(DatabaseOperationalError):
                PlayerMemory("test_player", self.db_path)

    def test_generic_database_error_on_init(self):
        """Test handling of generic database errors during initialization."""
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.execute.side_effect = sqlite3.Error("Generic database error")
            mock_connect.return_value.__enter__.return_value = mock_conn

            with self.assertRaises(DatabaseError):
                PlayerMemory("test_player", self.db_path)

    def test_database_error_during_scene_end(self):
        """Test handling database errors when ending scene."""
        memory = PlayerMemory("player_error_test", self.db_path)

        initial_state = {'oxygen': 100, 'trust': 0}
        memory.start_scene("scene_airlock", "engineer", initial_state)

        final_state = {'oxygen': 80, 'trust': 10, 'correct_actions': 5, 'incorrect_actions': 1}

        # Mock database connection to raise error
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.execute.side_effect = sqlite3.Error("Database write error")
            mock_connect.return_value.__enter__.return_value = mock_conn

            with self.assertRaises(DatabaseError):
                memory.end_scene("success", final_state)

    def test_database_error_during_relationship_update(self):
        """Test handling database errors when updating relationships."""
        memory = PlayerMemory("player_error_test", self.db_path)

        # Manually trigger relationship update with database error
        memory.relationships["engineer"] = {'trust': 0, 'familiarity': 0}

        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.execute.side_effect = sqlite3.OperationalError("Database locked")
            mock_connect.return_value.__enter__.return_value = mock_conn

            with self.assertRaises(DatabaseOperationalError):
                memory._update_relationship("engineer", 10)

    def test_end_scene_without_start_scene(self):
        """Test ending scene without starting it first."""
        memory = PlayerMemory("player_error_test", self.db_path)

        final_state = {'oxygen': 80, 'trust': 10, 'correct_actions': 5, 'incorrect_actions': 1}

        # Should handle gracefully (early return)
        memory.end_scene("success", final_state)

        # Stats should not change
        self.assertEqual(memory.total_scenes_played, 0)


class TestFactoryFunction(unittest.TestCase):
    """Test factory function for creating PlayerMemory instances."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_player_memory.db")

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_get_or_create_player_memory(self):
        """Test factory function creates PlayerMemory instance."""
        memory = get_or_create_player_memory("player_factory_test")

        self.assertIsInstance(memory, PlayerMemory)
        self.assertEqual(memory.player_id, "player_factory_test")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_player_memory.db")
        self.memory = PlayerMemory("player_edge_test", self.db_path)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_empty_player_id(self):
        """Test creating player with empty ID."""
        memory = PlayerMemory("", self.db_path)
        self.assertEqual(memory.player_id, "")

    def test_special_characters_in_player_id(self):
        """Test player ID with special characters."""
        special_id = "player@123!#$%"
        memory = PlayerMemory(special_id, self.db_path)
        self.assertEqual(memory.player_id, special_id)

    def test_very_long_player_id(self):
        """Test player ID with very long string."""
        long_id = "player_" + "x" * 1000
        memory = PlayerMemory(long_id, self.db_path)
        self.assertEqual(memory.player_id, long_id)

    def test_zero_trust_change(self):
        """Test relationship update with zero trust change."""
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        final_state = {'oxygen': 80, 'trust': 0, 'correct_actions': 3, 'incorrect_actions': 3}
        self.memory.end_scene("success", final_state)

        self.assertEqual(self.memory.relationships["engineer"]['trust'], 0)
        self.assertEqual(self.memory.relationships["engineer"]['familiarity'], 1)

    def test_missing_final_state_fields(self):
        """Test ending scene with missing final state fields."""
        initial_state = {'oxygen': 100, 'trust': 0}
        self.memory.start_scene("scene_airlock", "engineer", initial_state)

        # Missing some fields
        final_state = {'oxygen': 80}

        # Should handle gracefully with defaults
        self.memory.end_scene("success", final_state)

        self.assertEqual(self.memory.total_scenes_played, 1)

    def test_scene_statistics_with_no_successes(self):
        """Test statistics when all scenes failed."""
        for _ in range(5):
            initial_state = {'oxygen': 100, 'trust': 0}
            self.memory.start_scene("scene_airlock", "engineer", initial_state)
            final_state = {'oxygen': 0, 'trust': -20, 'correct_actions': 0, 'incorrect_actions': 5}
            self.memory.end_scene("failure", final_state)

        self.assertEqual(self.memory.total_scenes_played, 5)
        self.assertEqual(self.memory.total_successes, 0)
        self.assertEqual(self.memory.total_failures, 5)

    def test_loaded_stats_from_database(self):
        """Test that scene statistics are correctly loaded from database."""
        # Play some scenes
        for i in range(3):
            initial_state = {'oxygen': 100, 'trust': 0}
            self.memory.start_scene("scene_airlock", "engineer", initial_state)
            final_state = {
                'oxygen': 80,
                'trust': 10,
                'correct_actions': 5,
                'incorrect_actions': 1
            }
            outcome = "success" if i < 2 else "failure"
            self.memory.end_scene(outcome, final_state)

        # Create new instance (should load from database)
        memory2 = PlayerMemory("player_edge_test", self.db_path)

        self.assertEqual(memory2.total_scenes_played, 3)
        self.assertEqual(memory2.total_successes, 2)
        self.assertEqual(memory2.total_failures, 1)


if __name__ == '__main__':
    unittest.main()
