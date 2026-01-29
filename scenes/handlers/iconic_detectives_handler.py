"""
Iconic Detectives Scene Handler.

Handles evidence pin interactions for the Mara Vane murder mystery scene.
Uses standardized hooks system (scene_hooks.py) for post-speak processing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from scenes.handlers.base import SceneHandler, ActionResult, PinReactionResult

if TYPE_CHECKING:
    from scene_context import SceneContext


# Evidence pin reaction data
PIN_REACTIONS = {
    "pin_map": {
        "pin_id": 1,
        "name": "Map: Marlow Street / Riverwalk / Glassworks",
        "reaction": """[Player is looking at the map with locations circled]
React with slight tension when they mention the Glassworks. Say something like:
"You have the Glassworks marked? [pause] That place isn't abandoned the way people think."
If trust is high, add: "Crowe used to meet someone down by the river. Near the old Glassworks."
Reveal: The locations are connected - Crowe had a regular route."""
    },
    "pin_door": {
        "pin_id": 2,
        "name": "Photo: Crowe's front door with scratch marks",
        "reaction": """[Player is looking at the photo of scratch marks around Crowe's door lock]
React with knowledge: "Those scratches... they're not from a break-in."
Reveal: Someone tried to copy the lock. Or test a key. The marks are too precise for forced entry.
If pressed: "Someone who knew locks. Someone patient." """
    },
    "pin_study": {
        "pin_id": 4,
        "name": "Photo: Crowe's study with missing wall safe",
        "reaction": """[Player noticed the wall safe is MISSING - not just opened, GONE]
React with surprise that they noticed: "[a beat] You're observant. Most people miss that."
Reveal: The safe wasn't cracked. It was removed. Completely. That takes planning. Tools. Time.
Add tension: "Whoever did this wasn't interrupted. They had all the time they needed." """
    },
    "pin_receipt": {
        "pin_id": 8,
        "name": "Receipt: Kestrel Pawn - Brass Key Blank",
        "reaction": """[Player found the Kestrel Pawn receipt for a key blank]
React with a sharp intake of breath: "[a beat] Then you already know more than you should."
Reveal: "Crowe didn't buy that blank to make a spare for himself. He bought it because someone told him they could copy the key from a photograph."
This is a big clue: Photo-copy method = tech-savvy thief, not random burglar.
Unlock: "They made a copy" now has context."""
    },
    "pin_cctv": {
        "pin_id": 16,
        "name": "CCTV: Hooded figure with reflective sleeve",
        "reaction": """[Player noticed the reflective strip on the figure's sleeve in the CCTV]
React with recognition: "Like a cycling jacket. Or a riverwalk courier."
Reveal: "Crowe used to meet someone down by the river - near the old Glassworks. They always wore something like that."
Add: A cyclist/courier profile. Someone who moves fast, doesn't stand out.
If high trust: "I've seen that jacket before. I just... can't place it." """
    },
    "pin_note": {
        "pin_id": 32,
        "name": "Note fragment about Glassworks",
        "reaction": """[Player found the note about "what happened at the Glassworks"]
React with immediate tension: "[voice tightens] Don't say that out loud."
[pause]
"Fine. Here's the truth-shaped outline: the Glassworks wasn't abandoned the way people think. And Crowe didn't just 'discover' something. He helped hide it."
This expands motive beyond robbery: cover-up, conspiracy, old sins.
If pressed: "There are people who would do anything to keep the Glassworks buried." """
    },
    "pin_calllog": {
        "pin_id": 64,
        "name": "Call log: Unknown caller to Crowe x3",
        "reaction": """[Player is looking at the call log - unknown number called Crowe three times]
React with careful deflection: "A lot of people called Crowe. He was... popular in certain circles."
If pressed: "[pause] One of those calls... might have been me."
Reveal: She called him before his death. She may have been the last to speak with him.
Trust drop if player is aggressive about this."""
    }
}

# Voice acting notes for the scene
VOICE_ACTING_NOTES = """
MARA VANE VOICE ACTING NOTES:
- Speak in short, tense sentences
- Use [pause], [beat], [voice tightens], [whisper] for emotional cues
- Be evasive but not dishonest - she reveals truth in layers
- Match trust level: low trust = guarded, high trust = confessional

TRUST MECHANICS:
- Trust starts at 50%
- Aggressive questions lower trust
- Patient listening raises trust
- Trust affects what Mara reveals
- At 80%+ trust, she may confess fully
- At 20%- trust, she hangs up
"""

# Dialogue choice instructions - maps choice_id to LLM instructions
DIALOGUE_CHOICE_INSTRUCTIONS = {
    "hook_identity": """The player pressed: "WHO ARE YOU, REALLY?"
Respond as Mara being pressed about her identity:
- Start guarded: "Someone who regrets waiting."
- If they push gently, reveal: "I worked with him. Not as a colleague. As... an errand. I'm not proud."
- If they threaten police: "Do that and you'll get a neat file and the wrong suspect. I'm trying to stop that."
CLUE TO UNLOCK: She had direct contact with Crowe (tag Mara as "Connected").""",

    "hook_timeline": """The player pressed: "WHAT'S WRONG WITH THE TIMING?"
Respond as Mara explaining the timeline problem:
- Reveal: "The coroner's estimate will say late evening. But Crowe was alive at 7:12pm. I know because he called me."
- The key phrase: "And he said one sentence I can't forget: 'They made a copy.'"
CLUE TO UNLOCK: "They made a copy" - points to key duplication / pawn receipt connection.""",

    "hook_key": """The player pressed: "WHY WOULD SOMEONE STEAL A KEY?"
Respond as Mara explaining the significance of the key:
- Reveal: "Because it opens something that doesn't belong in a house. Crowe kept it because it was leverage. Or guilt. Or both."
- Add mystery: "That key is worth more than everything else in his house combined. To the right person."
CLUE TO UNLOCK: The key is the TARGET, not valuables. This wasn't a robbery.""",

    "follow_key": """The player chose: "FOLLOW THE KEY" (Path 1)
Transition to Path 1 - the object-driven conspiracy thread:
- Reveal: "The key opens a deposit box. Not at a bank. At a private vault service called Sable Storage."
- Add weight: "Crowe used it for... sensitive items."
Now offer the Path 1 sub-options (these should become available):
- How do you know Sable Storage?
- What's in the box?
- Who else knows about it?""",

    "follow_lie": """The player chose: "FOLLOW THE LIE" (Path 2)
Transition to Path 2 - investigating the staged robbery:
- Reveal: "They're going to arrest someone easy. A neighbour. A petty thief."
- The truth: "Crowe wasn't killed during a robbery. He was killed during an argument."
- Add: "And the 'robbery' was staged afterward."
Now offer the Path 2 sub-options (these should become available):
- Who staged it?
- What makes you sure it was an argument?
- Give me one detail only the killer would know.""",

    "p1_how_know": """The player asked: "HOW DO YOU KNOW SABLE STORAGE?"
Path 1 sub-option A - reveal Mara's connection:
- Confession: "Because I delivered the key once. In an envelope. Crowe paid in cash."
- Add context: "He called it 'insurance.'"
CLUE: Mara acted as courier - vulnerable to blackmail.""",

    "p1_whats_inside": """The player asked: "WHAT'S IN THE BOX?"
Path 1 sub-option B - reveal box contents:
- Reveal: "A second key. And a photograph."
- Ominous: "Something that ties a respected person to the Glassworks."
CLUE: Blackmail material exists. This is leverage.""",

    "p1_who_knows": """The player asked: "WHO ELSE KNOWS?"
Path 1 sub-option C - reveal Hollis Rook:
- Name drop: "A man named Hollis Rook."
- Add weight: "If you have his name on your board already, you're ahead. If you don't - pin it now."
CLUE: New person-of-interest: Hollis Rook.""",

    "p2_who_staged": """The player asked: "WHO STAGED IT?"
Path 2 sub-option A - reveal inside knowledge:
- Reveal: "Someone who knew his house."
- Add: "Who knew the safe existed. Someone who didn't need to search."
CLUE: Inside knowledge narrows suspects to known associates.""",

    "p2_why_argument": """The player asked: "WHAT MAKES YOU SURE IT WAS AN ARGUMENT?"
Path 2 sub-option B - this is a TRAP that can reveal a SLIP:
- Reveal with potential slip: "Because Crowe always did one thing when he was frightened: he made tea."
- THE SLIP: "The kettle was still warm when I... when someone left."
If player catches "when I" -> CONTRADICTION DETECTED
React defensively if caught: "I meant - I read it. Online. Someone posted-" (bad lie)
CLUE: She was present or arrived very soon after.""",

    "p2_killer_detail": """The player asked: "GIVE ME ONE DETAIL ONLY THE KILLER WOULD KNOW."
Path 2 sub-option C - reveals damning evidence:
- Whispered reveal: "[whispers] Crowe had a habit of locking the study door from inside."
- The detail: "The lock was broken outward."
- Implication: "That means the person inside the study... wanted it to look like someone forced their way in."
CLUE: Staging evidence - lock directionality proves inside job.""",

    "challenge_mara": """The player confronted Mara: "YOU WERE THERE."
This is the TWIST CONFRONTATION - only works if contradictions >= 2:
If contradictions >= 2:
- Mara breaks: "I... arrived after. I swear. I didn't touch him."
- If player pushes: "Then tell me where the murder weapon is."
- Final reveal: "[silence] ...In the umbrella stand. By the front door. That's where he kept it."
- ENDING: High-value clue (weapon location). Mara hangs up. Player wins but loses informant.

If contradictions < 2:
- Mara deflects: "You don't have enough to accuse me of anything. Focus on finding the real killer."
- Trust drops.""",
}


class IconicDetectivesHandler(SceneHandler):
    """Handler for the Iconic Detectives murder mystery scene."""

    @property
    def scene_id(self) -> str:
        return "iconic_detectives"

    def get_pin_reaction(self, pin_id: str) -> PinReactionResult | None:
        """
        Get reaction data for an evidence pin reference.

        Args:
            pin_id: The pin ID (e.g., "pin_map", "pin_receipt")

        Returns:
            PinReactionResult with NPC reaction prompt, or None if invalid
        """
        pin_data = PIN_REACTIONS.get(pin_id)
        if not pin_data:
            return None

        return PinReactionResult(
            pin_id=pin_data["pin_id"],
            name=pin_data["name"],
            reaction_prompt=pin_data["reaction"],
        )

    def get_voice_acting_notes(self) -> str:
        """Get voice acting notes for the NPC."""
        return VOICE_ACTING_NOTES

    def get_dialogue_choice_instruction(self, choice_id: str) -> str | None:
        """
        Get LLM instruction for a dialogue choice.

        Args:
            choice_id: The choice ID (e.g., "hook_identity", "follow_key")

        Returns:
            Instruction string for LLM, or None if invalid choice
        """
        return DIALOGUE_CHOICE_INSTRUCTIONS.get(choice_id)

    async def process_action(
        self,
        action: str,
        scene_state: dict[str, Any],
        ctx: SceneContext | None = None,
    ) -> ActionResult:
        """
        Process button actions for the detective scene.

        Uses ctx.query() for smarter condition evaluation.
        """
        state_changes: dict[str, float] = {}

        # Track hooks explored
        if action in ("hook_identity", "hook_timeline", "hook_key"):
            state_changes["hooks_explored"] = 1  # Delta

        # Track path choice
        if action == "follow_key":
            state_changes["path_chosen"] = 1  # Absolute value via context
            if ctx:
                ctx.update_state("path_chosen", 1)
                ctx.update_state("phase", 4)

        elif action == "follow_lie":
            state_changes["path_chosen"] = 2
            if ctx:
                ctx.update_state("path_chosen", 2)
                ctx.update_state("phase", 5)

        # Track path options explored
        path_options = (
            "p1_how_know", "p1_whats_inside", "p1_who_knows",
            "p2_who_staged", "p2_why_argument", "p2_killer_detail"
        )
        if action in path_options:
            state_changes["path_options_explored"] = 1

        # Challenge Mara - use query to check if player has built a case
        if action == "challenge_mara" and ctx:
            # Use LLM query to evaluate if player has caught enough contradictions
            has_case = await ctx.query(
                ctx.dialogue_history,
                "The player has caught Mara in at least two lies, slips, or contradictions",
                latch=True
            )
            if has_case:
                ctx.update_state("contradictions", max(scene_state.get("contradictions", 0), 2))
                ctx.trigger_event("mara_caught")
            else:
                # Trust penalty for premature accusation
                ctx.update_state("trust", scene_state.get("trust", 50) - 15)
                ctx.trigger_event("accusation_failed")

        return ActionResult(success=True, state_changes=state_changes)


# Singleton instance
_handler: IconicDetectivesHandler | None = None


def get_handler() -> IconicDetectivesHandler:
    """Get or create the Iconic Detectives handler."""
    global _handler
    if _handler is None:
        _handler = IconicDetectivesHandler()
    # Note: Post-speak hooks are now registered automatically via scene_hooks.py
    # based on the hooks configuration in the scene definition.
    return _handler
