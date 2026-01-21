"""
Base Scene class.

All scenes inherit from this class and override the configuration properties.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from llm_prompt_core.types import Line


@dataclass
class SceneControl:
    """
    Represents a user control in a scene (button, lever, valve, etc.)

    Attributes:
        id: Unique identifier for this control
        label: Display text on the control
        type: Type of control ("button", "lever", "dial", "switch")
        color: Hex color code (e.g., 0xff3333)
        position: 3D position {x, y, z} relative to scene
        description: What this control does (for tooltips/context)
        action_type: Semantic action type (e.g., "critical", "dangerous", "safe")
        npc_aware: Whether the NPC can see/hear/sense this action
            True: NPC is notified and can react (e.g., Casey hears button press in sub)
            False: Action is hidden from NPC (e.g., player secretly examining evidence)
        visible_in_phases: List of phase numbers when this control should be visible
            If None, control is always visible. If specified, only visible in those phases.
    """
    id: str
    label: str
    type: str = "button"
    color: int = 0xffffff
    position: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    action_type: str = "normal"
    npc_aware: bool = True  # Default: NPC is aware of actions
    visible_in_phases: Optional[List[int]] = None  # None means always visible


@dataclass
class StateVariable:
    """
    Tracks a scene state variable.

    Attributes:
        name: Variable name
        initial_value: Starting value
        min_value: Minimum allowed value (optional)
        max_value: Maximum allowed value (optional)
        update_rate: How much it changes per second (optional, for auto-updating values)
    """
    name: str
    initial_value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    update_rate: Optional[float] = None


@dataclass
class SuccessCriterion:
    """
    Defines a condition that must be met to succeed in the scene.

    Attributes:
        id: Unique identifier
        description: Human-readable description
        condition: Lambda or callable that evaluates state and returns bool
        message: Message to display when this criterion is met
        required: Whether this criterion must be met (vs optional objective)
    """
    id: str
    description: str
    condition: str  # Expression string like "state['oxygen'] > 0 and state['trust'] >= 80"
    message: str
    required: bool = True


@dataclass
class FailureCriterion:
    """
    Defines a condition that causes scene failure.

    Attributes:
        id: Unique identifier
        description: Human-readable description
        condition: Expression string to evaluate
        message: Message to display when player fails this way
        ending_type: Type of ending (for different failure states)
    """
    id: str
    description: str
    condition: str  # Expression string like "state['oxygen'] <= 0"
    message: str
    ending_type: str = "failure"


@dataclass
class CharacterRequirement:
    """
    Defines skills/knowledge a character should have for this scene.

    Attributes:
        skill: Name of the skill/knowledge area
        importance: How critical this is ("required", "recommended", "helpful")
        impact_without: What happens if character lacks this skill
        alternative_path: Whether there's an alternative way to succeed without this skill
    """
    skill: str
    importance: str = "recommended"
    impact_without: str = "Increased difficulty"
    alternative_path: bool = True


@dataclass
class AudioAssets:
    """
    Defines audio files and sound effects for the scene.

    Attributes:
        background_music: Path to background music/ambient sound
        sfx_library: Dictionary mapping event names to sound effect file paths
        volume_levels: Dictionary of volume settings for different audio types
    """
    background_music: Optional[str] = None
    sfx_library: Dict[str, str] = field(default_factory=dict)
    volume_levels: Dict[str, float] = field(default_factory=lambda: {
        'music': 0.5,
        'sfx': 0.8,
        'voice': 1.0
    })


@dataclass
class SceneArtAssets:
    """
    Defines art files and visual assets for the scene.

    Attributes:
        scene_type: Type of 3D scene to use ("character", "submarine", "custom")
        background_image: Path to background image (optional)
        environment_model: Path to 3D environment model (optional)
        ui_elements: Dictionary of UI element paths
        custom_scene_file: Path to custom scene JavaScript file
        audio: Audio assets for this scene
    """
    scene_type: str = "character"
    background_image: Optional[str] = None
    environment_model: Optional[str] = None
    ui_elements: Dict[str, str] = field(default_factory=dict)
    custom_scene_file: Optional[str] = None
    audio: AudioAssets = field(default_factory=AudioAssets)


@dataclass
class Scene:
    """
    Base class for all scenes.

    Attributes:
        id: Unique identifier (lowercase, no spaces)
        name: Display name shown in UI
        description: Context about this scene for the LLM
        opening_speech: List of lines the character says when scene starts

        # New enhanced attributes:
        art_assets: Visual assets and scene type
        controls: List of user controls available in this scene
        state_variables: Variables tracking scene state (oxygen, trust, etc.)
        success_criteria: Conditions for winning/completing the scene
        failure_criteria: Conditions that cause scene failure
        character_requirements: Skills/knowledge needed for optimal performance
        time_limit: Time limit in seconds (optional)
        allow_freeform_dialogue: Whether player can chat freely or only use controls
    """

    id: str = "default"
    name: str = "Default Scene"
    description: str = "A default scene."
    opening_speech: List[Line] = field(default_factory=list)

    # Enhanced scene properties
    art_assets: SceneArtAssets = field(default_factory=SceneArtAssets)
    controls: List[SceneControl] = field(default_factory=list)
    state_variables: List[StateVariable] = field(default_factory=list)
    success_criteria: List[SuccessCriterion] = field(default_factory=list)
    failure_criteria: List[FailureCriterion] = field(default_factory=list)
    character_requirements: List[CharacterRequirement] = field(default_factory=list)
    time_limit: Optional[float] = None
    allow_freeform_dialogue: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert scene to dictionary format for web_server.py compatibility."""
        return {
            'name': self.name,
            'description': self.description,
            'opening_speech': self.opening_speech,
            'art_assets': {
                'scene_type': self.art_assets.scene_type,
                'background_image': self.art_assets.background_image,
                'environment_model': self.art_assets.environment_model,
                'ui_elements': self.art_assets.ui_elements,
                'custom_scene_file': self.art_assets.custom_scene_file,
                'audio': {
                    'background_music': self.art_assets.audio.background_music,
                    'sfx_library': self.art_assets.audio.sfx_library,
                    'volume_levels': self.art_assets.audio.volume_levels,
                },
            },
            'controls': [
                {
                    'id': ctrl.id,
                    'label': ctrl.label,
                    'type': ctrl.type,
                    'color': ctrl.color,
                    'position': ctrl.position,
                    'description': ctrl.description,
                    'action_type': ctrl.action_type,
                    'npc_aware': ctrl.npc_aware,
                }
                for ctrl in self.controls
            ],
            'state_variables': [
                {
                    'name': var.name,
                    'initial_value': var.initial_value,
                    'min_value': var.min_value,
                    'max_value': var.max_value,
                    'update_rate': var.update_rate,
                }
                for var in self.state_variables
            ],
            'success_criteria': [
                {
                    'id': crit.id,
                    'description': crit.description,
                    'condition': crit.condition,
                    'message': crit.message,
                    'required': crit.required,
                }
                for crit in self.success_criteria
            ],
            'failure_criteria': [
                {
                    'id': crit.id,
                    'description': crit.description,
                    'condition': crit.condition,
                    'message': crit.message,
                    'ending_type': crit.ending_type,
                }
                for crit in self.failure_criteria
            ],
            'character_requirements': [
                {
                    'skill': req.skill,
                    'importance': req.importance,
                    'impact_without': req.impact_without,
                    'alternative_path': req.alternative_path,
                }
                for req in self.character_requirements
            ],
            'time_limit': self.time_limit,
            'allow_freeform_dialogue': self.allow_freeform_dialogue,
        }

    def evaluate_condition(self, condition: str, state: Dict[str, Any]) -> bool:
        """
        Safely evaluate a condition string with the current state.

        Args:
            condition: Expression string to evaluate
            state: Current scene state variables

        Returns:
            Boolean result of the condition
        """
        try:
            # Create a safe evaluation environment
            safe_dict = {'state': state}
            return eval(condition, {"__builtins__": {}}, safe_dict)
        except Exception as e:
            print(f"Error evaluating condition '{condition}': {e}")
            return False

    def check_success(self, state: Dict[str, Any]) -> Optional[SuccessCriterion]:
        """Check if any success criteria are met."""
        for criterion in self.success_criteria:
            if self.evaluate_condition(criterion.condition, state):
                return criterion
        return None

    def check_failure(self, state: Dict[str, Any]) -> Optional[FailureCriterion]:
        """Check if any failure criteria are met."""
        for criterion in self.failure_criteria:
            if self.evaluate_condition(criterion.condition, state):
                return criterion
        return None

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"
