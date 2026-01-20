"""
Player Memory System

Tracks player behavior, preferences, and progress across sessions.
This allows characters to remember players and adapt to their play style.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class PlayerMemory:
    """Manages persistent player memory across sessions."""

    def __init__(self, player_id: str, db_path: str = "data/player_memory.db"):
        self.player_id = player_id
        self.db_path = db_path

        # Session data
        self.current_session_start = datetime.now()
        self.scenes_completed = []
        self.current_scene_data = {}

        # Behavioral patterns (0-100 scale)
        self.personality_profile = {
            'impulsiveness': 50,      # Button mashing, interrupting
            'cooperation': 50,         # Listening, following instructions
            'problem_solving': 50,     # Correct actions, creative solutions
            'patience': 50,            # Waiting for instructions
        }

        # Story progress
        self.relationships = {}

        # Performance history
        self.total_scenes_played = 0
        self.total_successes = 0
        self.total_failures = 0
        self.achievements = []

        # Scene-specific history
        self.scene_attempts = {}  # {scene_id: count}
        self.scene_best_performance = {}  # {scene_id: score}

        # Initialize database and load existing data
        self._init_database()
        self._load_from_database()

    def _init_database(self):
        """Create database tables if they don't exist."""
        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Players table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_sessions INTEGER DEFAULT 0,
                total_playtime_seconds INTEGER DEFAULT 0
            )
        ''')

        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                scenes_completed INTEGER DEFAULT 0,
                FOREIGN KEY (player_id) REFERENCES players (player_id)
            )
        ''')

        # Scene attempts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scene_attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT,
                scene_id TEXT,
                character_id TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                outcome TEXT,
                final_trust INTEGER,
                correct_actions INTEGER,
                incorrect_actions INTEGER,
                interrupted_npc BOOLEAN,
                data JSON,
                FOREIGN KEY (player_id) REFERENCES players (player_id)
            )
        ''')

        # Personality profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personality_profiles (
                player_id TEXT PRIMARY KEY,
                impulsiveness INTEGER DEFAULT 50,
                cooperation INTEGER DEFAULT 50,
                problem_solving INTEGER DEFAULT 50,
                patience INTEGER DEFAULT 50,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players (player_id)
            )
        ''')

        # Relationships table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationships (
                player_id TEXT,
                character_id TEXT,
                trust INTEGER DEFAULT 0,
                familiarity INTEGER DEFAULT 0,
                last_interaction TIMESTAMP,
                PRIMARY KEY (player_id, character_id),
                FOREIGN KEY (player_id) REFERENCES players (player_id)
            )
        ''')

        conn.commit()
        conn.close()

    def _load_from_database(self):
        """Load existing player data from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if player exists, if not create them
        cursor.execute('SELECT * FROM players WHERE player_id = ?', (self.player_id,))
        player = cursor.fetchone()

        if not player:
            # New player
            cursor.execute('''
                INSERT INTO players (player_id) VALUES (?)
            ''', (self.player_id,))

            cursor.execute('''
                INSERT INTO personality_profiles (player_id) VALUES (?)
            ''', (self.player_id,))

            conn.commit()
        else:
            # Load personality profile
            cursor.execute('''
                SELECT impulsiveness, cooperation, problem_solving, patience
                FROM personality_profiles WHERE player_id = ?
            ''', (self.player_id,))
            profile = cursor.fetchone()
            if profile:
                self.personality_profile = {
                    'impulsiveness': profile[0],
                    'cooperation': profile[1],
                    'problem_solving': profile[2],
                    'patience': profile[3]
                }

            # Load relationships
            cursor.execute('''
                SELECT character_id, trust, familiarity
                FROM relationships WHERE player_id = ?
            ''', (self.player_id,))
            for row in cursor.fetchall():
                self.relationships[row[0]] = {
                    'trust': row[1],
                    'familiarity': row[2]
                }

            # Load scene statistics
            cursor.execute('''
                SELECT COUNT(*), SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END)
                FROM scene_attempts WHERE player_id = ?
            ''', (self.player_id,))
            stats = cursor.fetchone()
            if stats[0]:
                self.total_scenes_played = stats[0]
                self.total_successes = stats[1] or 0
                self.total_failures = stats[0] - (stats[1] or 0)

            # Load scene attempt counts
            cursor.execute('''
                SELECT scene_id, COUNT(*) FROM scene_attempts
                WHERE player_id = ? GROUP BY scene_id
            ''', (self.player_id,))
            for row in cursor.fetchall():
                self.scene_attempts[row[0]] = row[1]

        # Update last seen
        cursor.execute('''
            UPDATE players SET last_seen = CURRENT_TIMESTAMP
            WHERE player_id = ?
        ''', (self.player_id,))

        conn.commit()
        conn.close()

    def start_scene(self, scene_id: str, character_id: str, initial_state: Dict):
        """Record the start of a new scene attempt."""
        self.current_scene_data = {
            'scene_id': scene_id,
            'character_id': character_id,
            'started_at': datetime.now(),
            'initial_state': initial_state.copy(),
            'interrupted_count': 0,
            'rapid_action_count': 0
        }

    def record_interruption(self):
        """Record that player interrupted the NPC."""
        self.current_scene_data['interrupted_count'] = \
            self.current_scene_data.get('interrupted_count', 0) + 1

    def record_rapid_actions(self):
        """Record that player performed rapid button mashing."""
        self.current_scene_data['rapid_action_count'] = \
            self.current_scene_data.get('rapid_action_count', 0) + 1

    def end_scene(self, outcome: str, final_state: Dict):
        """Record the end of a scene attempt and update personality."""
        if not self.current_scene_data:
            return

        scene_id = self.current_scene_data['scene_id']
        character_id = self.current_scene_data['character_id']

        # Calculate metrics
        interrupted = self.current_scene_data.get('interrupted_count', 0) > 0
        correct_actions = final_state.get('correct_actions', 0)
        incorrect_actions = final_state.get('incorrect_actions', 0)
        final_trust = final_state.get('trust', 0)

        # Update personality based on behavior
        self._update_personality(
            interrupted=self.current_scene_data.get('interrupted_count', 0),
            rapid_actions=self.current_scene_data.get('rapid_action_count', 0),
            correct_actions=correct_actions,
            incorrect_actions=incorrect_actions,
            outcome=outcome
        )

        # Update relationship with character
        self._update_relationship(character_id, final_trust)

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO scene_attempts
            (player_id, scene_id, character_id, ended_at, outcome,
             final_trust, correct_actions, incorrect_actions, interrupted_npc, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.player_id,
            scene_id,
            character_id,
            datetime.now(),
            outcome,
            final_trust,
            correct_actions,
            incorrect_actions,
            interrupted,
            json.dumps(final_state)
        ))

        # Update personality in database
        cursor.execute('''
            UPDATE personality_profiles
            SET impulsiveness = ?, cooperation = ?, problem_solving = ?,
                patience = ?, updated_at = CURRENT_TIMESTAMP
            WHERE player_id = ?
        ''', (
            self.personality_profile['impulsiveness'],
            self.personality_profile['cooperation'],
            self.personality_profile['problem_solving'],
            self.personality_profile['patience'],
            self.player_id
        ))

        conn.commit()
        conn.close()

        # Update scene attempt count
        self.scene_attempts[scene_id] = self.scene_attempts.get(scene_id, 0) + 1
        self.total_scenes_played += 1
        if outcome == 'success':
            self.total_successes += 1
        else:
            self.total_failures += 1

        # Clear current scene data
        self.current_scene_data = {}

    def _update_personality(self, interrupted: int, rapid_actions: int,
                           correct_actions: int, incorrect_actions: int, outcome: str):
        """Update personality profile based on scene behavior."""
        # Impulsiveness (increases with interruptions and rapid actions)
        if interrupted > 0:
            self.personality_profile['impulsiveness'] = min(100,
                self.personality_profile['impulsiveness'] + (interrupted * 3))
        else:
            # Slowly decrease if no interruptions
            self.personality_profile['impulsiveness'] = max(0,
                self.personality_profile['impulsiveness'] - 1)

        # Patience (decreases with rapid actions)
        if rapid_actions > 0:
            self.personality_profile['patience'] = max(0,
                self.personality_profile['patience'] - (rapid_actions * 3))
        elif interrupted == 0:
            # Increase if patient
            self.personality_profile['patience'] = min(100,
                self.personality_profile['patience'] + 2)

        # Cooperation (increases if low interruptions and good outcome)
        if interrupted == 0 and outcome == 'success':
            self.personality_profile['cooperation'] = min(100,
                self.personality_profile['cooperation'] + 3)
        elif interrupted > 2:
            self.personality_profile['cooperation'] = max(0,
                self.personality_profile['cooperation'] - 2)

        # Problem solving (increases with correct actions)
        if correct_actions > incorrect_actions:
            self.personality_profile['problem_solving'] = min(100,
                self.personality_profile['problem_solving'] + 2)
        elif incorrect_actions > correct_actions * 2:
            self.personality_profile['problem_solving'] = max(0,
                self.personality_profile['problem_solving'] - 1)

    def _update_relationship(self, character_id: str, trust_change: int):
        """Update relationship with a character."""
        if character_id not in self.relationships:
            self.relationships[character_id] = {'trust': 0, 'familiarity': 0}

        self.relationships[character_id]['trust'] += trust_change
        self.relationships[character_id]['familiarity'] += 1

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO relationships
            (player_id, character_id, trust, familiarity, last_interaction)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            self.player_id,
            character_id,
            self.relationships[character_id]['trust'],
            self.relationships[character_id]['familiarity']
        ))

        conn.commit()
        conn.close()

    def get_character_context(self, character_id: str) -> str:
        """Get context about player's history with this character for LLM."""
        if character_id not in self.relationships:
            return "This is your first time meeting this player."

        rel = self.relationships[character_id]
        familiarity = rel['familiarity']
        trust = rel['trust']

        if familiarity == 1:
            context = "You've met this player once before. "
        elif familiarity < 5:
            context = f"You've worked with this player {familiarity} times before. "
        else:
            context = f"You and this player have a long history ({familiarity} encounters). "

        if trust > 50:
            context += "They've earned your trust through good cooperation."
        elif trust > 20:
            context += "You have a decent working relationship."
        elif trust > -20:
            context += "Your relationship is neutral."
        elif trust > -50:
            context += "You're somewhat frustrated with their past behavior."
        else:
            context += "You have serious doubts about their ability to cooperate."

        return context

    def get_personality_summary(self) -> str:
        """Get summary of player personality for LLM context."""
        p = self.personality_profile

        summary = "Player behavioral profile:\n"

        # Impulsiveness
        if p['impulsiveness'] > 70:
            summary += "- VERY IMPULSIVE: Acts without thinking, interrupts frequently\n"
        elif p['impulsiveness'] > 50:
            summary += "- Somewhat impulsive: Tends to act quickly\n"
        else:
            summary += "- Thoughtful: Takes time to consider actions\n"

        # Patience
        if p['patience'] > 70:
            summary += "- VERY PATIENT: Waits for instructions, listens carefully\n"
        elif p['patience'] > 50:
            summary += "- Patient: Generally waits for guidance\n"
        else:
            summary += "- IMPATIENT: Button mashes, doesn't wait for instructions\n"

        # Cooperation
        if p['cooperation'] > 70:
            summary += "- HIGHLY COOPERATIVE: Follows instructions well\n"
        elif p['cooperation'] > 50:
            summary += "- Cooperative: Usually follows guidance\n"
        else:
            summary += "- UNCOOPERATIVE: Ignores instructions, acts independently\n"

        # Problem solving
        if p['problem_solving'] > 70:
            summary += "- SKILLED: Makes mostly correct decisions\n"
        elif p['problem_solving'] > 50:
            summary += "- Competent: Decent decision-making\n"
        else:
            summary += "- STRUGGLES: Often makes incorrect choices\n"

        return summary

    def get_full_context_for_llm(self, character_id: str) -> str:
        """Get complete context for LLM prompt."""
        context = f"""
=== PLAYER MEMORY ===
{self.get_personality_summary()}

Relationship with you ({character_id}):
{self.get_character_context(character_id)}

Statistics:
- Total scenes played: {self.total_scenes_played}
- Success rate: {int((self.total_successes / max(1, self.total_scenes_played)) * 100)}%
- This scene attempts: {self.scene_attempts.get(self.current_scene_data.get('scene_id', ''), 0)}

INSTRUCTION: Adapt your dialogue to match this player's history and personality.
"""
        return context

    def should_give_hint(self, scene_id: str) -> bool:
        """Check if player might need a hint based on history."""
        attempts = self.scene_attempts.get(scene_id, 0)
        return attempts >= 2  # Failed this scene twice before

    def get_difficulty_recommendation(self) -> str:
        """Recommend difficulty adjustment based on player performance."""
        if self.total_scenes_played < 3:
            return "normal"

        success_rate = self.total_successes / self.total_scenes_played

        if success_rate > 0.8:
            return "harder"
        elif success_rate < 0.3:
            return "easier"
        else:
            return "normal"


def get_or_create_player_memory(player_id: str) -> PlayerMemory:
    """Factory function to get or create player memory."""
    return PlayerMemory(player_id)
