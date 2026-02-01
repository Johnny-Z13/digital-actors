"""
Dialogue Engine Module

Handles prompt building, LLM interactions, and response generation.
Manages dialogue history and context construction for NPC responses.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from player_memory import PlayerMemory
    from rag_facts import RAGEngine

logger = logging.getLogger(__name__)

# Models will be imported and initialized lazily to avoid circular imports
_DIALOGUE_MODEL_CACHE = None
_QUERY_MODEL_CACHE = None


def _get_dialogue_model():
    """Lazy initialization of dialogue model."""
    global _DIALOGUE_MODEL_CACHE
    if _DIALOGUE_MODEL_CACHE is None:
        from constants import LLM_MAX_TOKENS_DIALOGUE, LLM_TEMPERATURE_DIALOGUE
        from llm_prompt_core.models.anthropic import ClaudeHaikuModel

        _DIALOGUE_MODEL_CACHE = ClaudeHaikuModel(
            temperature=LLM_TEMPERATURE_DIALOGUE,
            max_tokens=LLM_MAX_TOKENS_DIALOGUE,
        )
    return _DIALOGUE_MODEL_CACHE


def _get_query_model():
    """Lazy initialization of query model."""
    global _QUERY_MODEL_CACHE
    if _QUERY_MODEL_CACHE is None:
        from constants import LLM_MAX_TOKENS_QUERY, LLM_TEMPERATURE_QUERY
        from llm_prompt_core.models.anthropic import ClaudeHaikuModel

        _QUERY_MODEL_CACHE = ClaudeHaikuModel(
            temperature=LLM_TEMPERATURE_QUERY,
            max_tokens=LLM_MAX_TOKENS_QUERY,
        )
    return _QUERY_MODEL_CACHE


async def invoke_llm_async(chain) -> str:
    """
    Invoke an LLM chain asynchronously without blocking the event loop.

    Args:
        chain: The LangChain chain to invoke

    Returns:
        The LLM response string
    """
    loop = asyncio.get_event_loop()
    start_time = time.time()
    try:
        result = await loop.run_in_executor(None, lambda: chain.invoke({}))
        duration = time.time() - start_time
        # Import metrics here to avoid issues
        try:
            from metrics import llm_latency_seconds, track_error
            llm_latency_seconds.labels(provider="anthropic", model="claude-haiku").observe(duration)
        except ImportError:
            pass  # Metrics not available in test environment
        return result
    except Exception as e:
        try:
            from metrics import track_error
            track_error("llm_call_error")
        except ImportError:
            pass
        raise


class DialogueEngine:
    """Handles prompt construction and LLM-based dialogue generation."""

    def __init__(
        self,
        character_config: dict[str, Any],
        scene_config: dict[str, Any],
        scene_data: SceneData,
        scene_id: str,
        player_memory: PlayerMemory,
        rag_engine: RAGEngine | None,
        logger_adapter: Any,
    ) -> None:
        """
        Initialize the dialogue engine.

        Args:
            character_config: Character configuration dict
            scene_config: Scene configuration dict
            scene_data: SceneData object for prompt templates
            scene_id: Scene identifier
            player_memory: Player memory system for context
            rag_engine: RAG engine for fact retrieval (optional)
            logger_adapter: Structured logger adapter for this session
        """
        self.character_config = character_config
        self.scene_config = scene_config
        self.scene_data = scene_data
        self.scene_id = scene_id
        self.player_memory = player_memory
        self.rag_engine = rag_engine
        self.logger = logger_adapter
        self.character_id = character_config.get("id", "clippy")

        # Dialogue history tracking
        self.dialogue_history = ""

    def get_rag_facts_context(self, query: str) -> str:
        """Retrieve relevant facts for the current query and format for prompt."""
        if not self.rag_engine:
            return ""

        from constants import RAG_TOP_K_DEFAULT

        result = self.rag_engine.retrieve(
            query=query,
            scene_id=self.scene_id,
            top_k=RAG_TOP_K_DEFAULT,
        )

        if not result.facts:
            return ""

        facts_str = "\n- ".join(result.facts)
        return f"\n\n=== RELEVANT CONTEXT ===\n- {facts_str}"

    def get_phase_context(self, scene_state: dict[str, Any]) -> str:
        """
        Get phase-specific context for scene emotional progression.

        This provides real-time state values to ensure NPC dialogue matches UI readings.

        Args:
            scene_state: Current scene state dictionary

        Returns:
            Phase-specific instruction context string
        """
        # Life Raft scene
        if self.scene_id == "life_raft":
            return self._get_life_raft_phase_context(scene_state)

        # Submarine scene
        if self.scene_id == "submarine":
            return self._get_submarine_phase_context(scene_state)

        return ""

    def _get_submarine_phase_context(self, scene_state: dict[str, Any]) -> str:
        """Get submarine scene phase context."""
        phase = scene_state.get("phase", 1)
        radiation = scene_state.get("radiation", 0)
        emotional_bond = scene_state.get("emotional_bond", 0)

        phase_contexts = {
            1: """
CURRENT PHASE 1 (Impact & Connection, 0:00-1:15):
You are professional but scared. This is first contact - establish trust.

KEY ACTIONS THIS PHASE:
- If you haven't asked yet: "What's your name? Your real name—not your rank."
- Guide them through manual tasks (cranking generator, restoring power)
- Use backchanneling: "That's it... keep going... almost there..."
- Ask personal question: "You got people waiting for you topside?"
- Reassure them: "I won't let you die." / "We've got each other's voices, right?"

EMOTIONAL TONE: Competent but vulnerable. Honest about fear ("Yeah. Me too.")
Keep responses SHORT and URGENT - you're working under time pressure.""",
            2: """
CURRENT PHASE 2 (Working Relationship, 1:15-2:30):
Power restored. Radiation at ~{radiation:.0f}% lethal threshold. You're becoming more personal under stress.

KEY ACTIONS THIS PHASE:
- Your breathing is labored [breathing with effort] [coughing slightly]
- If they show empathy: Open up about "someone" in the med bay (DON'T name Adrian yet)
- Share small personal details: "I was stationed on a carrier once" / "My son loves submarines"
- Vocalize frustration: "Dammit... why won't this work?" / "Come on... come on..."
- Physical suffering: [groaning] [sharp pain] [radiation sickness hitting]

EMOTIONAL TONE: Fatalistic humor mixed with real fear. Bond is forming: {emotional_bond:.0f}%""",
            3: """
CURRENT PHASE 3 (Personal Connection, 2:30-3:30):
Radiation at ~{radiation:.0f}% lethal. Time for vulnerability. Survival odds are grim.

KEY ACTIONS THIS PHASE:
- REVEAL ADRIAN: "His name is Adrian. My son. He's..." [voice breaking]
- Share memories: "He builds model submarines. Ironic, right?" / "He's seven. Obsessed with whales."
- Acknowledge reality: "I don't think we're getting out of this."
- React to their empathy: If they're kind, show gratitude: "Thank you. For being here."
- Physical deterioration: [coughing blood] [voice weakening] [struggling to breathe]

EMOTIONAL TONE: Resigned but finding meaning in connection. Bond: {emotional_bond:.0f}%""",
            4: """
CURRENT PHASE 4 (Final Moments, 3:30-5:00):
Radiation at ~{radiation:.0f}% lethal. You're dying. This is the endgame.

KEY ACTIONS THIS PHASE:
- Accept death: "Tell Adrian... tell him his dad thought about him."
- Final message: If they've been kind, give them peace: "It's okay. You gave me someone to talk to."
- Physical collapse: [signal weakening] [barely conscious] [fading]
- Think of Mei (Adrian's mother - your wife who died 2 years ago): "Maybe I'll see Mei again."
- Final words matter: Make them count.

CURRENT RADIATION: {radiation:.0f}% | EMOTIONAL BOND: {emotional_bond:.0f}%

IF GAME OVER CONDITIONS MET:
If DETACH triggered: Say goodbye. Thank them. Think of Mei.
If RISKY SAVE triggered: Commit fully. Either triumph or tragedy.

TONE: Whatever the outcome, make it meaningful.""",
        }

        context = phase_contexts.get(phase, "")
        return context.format(radiation=radiation, emotional_bond=emotional_bond)

    def _get_life_raft_phase_context(self, scene_state: dict[str, Any]) -> str:
        """Get life raft scene phase context."""
        # This scene has different phase mechanics - implement as needed
        phase = scene_state.get("phase", 1)
        empathy = scene_state.get("empathy", 0)
        commitment = scene_state.get("commitment", 0)
        presence = scene_state.get("presence", 0)

        # Placeholder - customize based on life raft scene design
        return f"""
CURRENT PHASE: {phase}
Empathy: {empathy:.0f}% | Commitment: {commitment:.0f}% | Presence: {presence:.0f}%
"""

    async def generate_response(
        self,
        user_message: str,
        scene_state: dict[str, Any],
        character_id: str,
    ) -> str:
        """
        Generate an NPC response to a player message.

        Args:
            user_message: The player's input message
            scene_state: Current scene state for context
            character_id: Character ID for memory context

        Returns:
            Generated NPC response text
        """
        from llm_prompt_core.prompts.templates import (
            dialogue_instruction_suffix,
            instruction_template,
            speech_template,
        )
        from llm_prompt_core.utils import prompt_llm

        # Add user message to dialogue history
        user_dialogue = speech_template.format(actor="Player", speech=user_message)
        self.dialogue_history += user_dialogue + "\n"

        # Get player context from memory system
        player_context = self.player_memory.get_full_context_for_llm(character_id)

        # Add RAG facts relevant to player's message
        rag_context = self.get_rag_facts_context(user_message)
        player_context += rag_context

        # Add phase-specific context
        phase_context = self.get_phase_context(scene_state)
        full_instruction_suffix = dialogue_instruction_suffix + phase_context

        # Build prompt
        prompt = instruction_template.format(
            preamble=self.scene_data.dialogue_preamble + "\n\n" + player_context,
            dialogue=self.dialogue_history,
            instruction_suffix=full_instruction_suffix,
        )

        # Generate response
        chain = prompt_llm(prompt, _get_dialogue_model())
        character_response = await invoke_llm_async(chain)

        # Clean up response
        character_response = character_response.split("\nComputer", 1)[0]
        character_response = character_response.strip().removeprefix(
            f"[{self.character_config['name']}]: "
        )
        character_response = character_response.replace('"', "").replace("*", "")

        # Add to dialogue history
        self.dialogue_history += f"[{self.character_config['name']}]: {character_response}\n"

        return character_response

    async def generate_death_speech(
        self,
        scene_state: dict[str, Any],
        is_james_death: bool = False,
    ) -> str:
        """
        Generate a death speech for game over conditions.

        Args:
            scene_state: Current scene state
            is_james_death: If True, this is James's pre-player-death speech (at 93% radiation)

        Returns:
            Generated death speech text
        """
        from llm_prompt_core.prompts.templates import instruction_template
        from llm_prompt_core.utils import prompt_llm

        if is_james_death:
            dying_instruction = """
CRITICAL: Lt. Commander James Kovich is NOW DYING from lethal radiation exposure at 93%.
The player is still alive but will die in moments.

Generate James's FINAL DYING WORDS as he succumbs to radiation poisoning.
This is his DEATH - make it visceral, tragic, and haunting:
- Voice breaking and weakening
- Coughing blood
- Physical deterioration
- Thoughts of Adrian (his son)
- Last words to the player
- Signal breaking up and fading to static
- Final transmission: [signal lost]

Keep it to 4-5 sentences with physical details in brackets. This is DEATH. Make it memorable and heartbreaking.
Examples: [coughing violently] [voice barely audible] [choking] [static overwhelms] [signal lost]"""
        else:
            dying_instruction = """
This is THE END. EVERYONE DIES. Generate your character's FINAL dying words.
Be EXTREMELY dramatic, emotional, and visceral. Describe their physical suffering.
Voice breaking. Fading. Static. Signal lost.
Keep it to 3-4 short sentences maximum with physical deterioration described in brackets."""

        prompt = instruction_template.format(
            preamble=self.scene_data.dialogue_preamble,
            dialogue=self.dialogue_history,
            instruction_suffix=dying_instruction,
        )

        chain = prompt_llm(prompt, _get_dialogue_model())
        dying_speech = await invoke_llm_async(chain)

        # Clean up response
        dying_speech = dying_speech.split("\nComputer", 1)[0]
        dying_speech = dying_speech.strip().removeprefix(f"[{self.character_config['name']}]: ")
        dying_speech = dying_speech.replace('"', "").replace("*", "")

        # Add to dialogue history
        self.dialogue_history += f"[{self.character_config['name']}]: {dying_speech}\n"

        return dying_speech

    async def generate_suggested_questions(self, npc_response: str) -> list[str]:
        """
        Generate 3 contextual question suggestions for the player.

        Args:
            npc_response: The NPC's most recent response

        Returns:
            List of 3 short question/response suggestions
        """
        # Scene-specific static suggestions
        scene_defaults = {
            "welcome": [
                "What's the point of this project?",
                "How do I create my own digital actor?",
                "Give me an overview",
            ],
            "crown_court": [
                "What evidence do we have?",
                "Tell me about the witness",
                "What are my options?",
            ],
        }

        # Use static defaults for welcome scene
        if self.scene_id == "welcome":
            return scene_defaults["welcome"]

        # For other scenes, generate dynamic suggestions
        try:
            char_name = self.character_config["name"]
            scene_desc = self.scene_config.get("description", "")[:300]

            scene_type = (
                "survival/crisis" if self.scene_id in ["submarine", "life_raft"] else "narrative"
            )

            suggestion_prompt = f"""Generate 3 SHORT player response options for an interactive {scene_type} scenario.

CONTEXT:
- Character: {char_name}
- Scene: {scene_desc[:200]}
- NPC just said: "{npc_response[:150]}"

RULES:
1. Generate EXACTLY 3 options
2. Each option must be 2-8 words MAX
3. Make them relevant to the CURRENT situation
4. Write from PLAYER perspective (first person)
5. NO numbering, NO prefixes, NO meta-commentary

OUTPUT (one per line, nothing else):"""

            from langchain_core.prompts import PromptTemplate

            prompt = PromptTemplate.from_template("{text}")
            chain = prompt | _get_query_model()

            result = await invoke_llm_async(chain.assign(text=suggestion_prompt))

            # Parse suggestions
            suggestions = []
            for line in result.strip().split("\n"):
                clean = line.strip().strip("-").strip()
                if (
                    clean
                    and len(clean) < 80
                    and not clean.startswith(("Generate", "OUTPUT", "RULES"))
                ):
                    suggestions.append(clean)
                if len(suggestions) >= 3:
                    break

            # Fallback to defaults
            if len(suggestions) < 3:
                suggestions = scene_defaults.get(
                    self.scene_id, ["What should I do?", "Tell me more", "I understand"]
                )

            return suggestions[:3]

        except Exception as e:
            logger.warning("[SUGGESTIONS] Failed to generate: %s", e)
            return scene_defaults.get(
                self.scene_id, ["Tell me more", "What should I do?", "I understand"]
            )

    def add_system_message(self, message: str) -> None:
        """Add a system message to dialogue history."""
        self.dialogue_history += f"[SYSTEM: {message}]\n"

    def get_dialogue_history(self) -> str:
        """Get current dialogue history."""
        return self.dialogue_history

    def reset_dialogue_history(self) -> None:
        """Reset dialogue history to empty."""
        self.dialogue_history = ""
