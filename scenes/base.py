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
        max_presses: Maximum number of times this control can be activated per session.
            None means unlimited. Used to prevent button-mashing exploits.
        cooldown_seconds: Minimum time between activations. None means no cooldown.
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
    max_presses: Optional[int] = None  # None means unlimited
    cooldown_seconds: Optional[float] = None  # None means no cooldown


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
class VoiceEffect:
    """
    Defines audio processing effects applied to TTS voice output.

    Attributes:
        id: Unique identifier for this effect (e.g., "phone", "radio", "none")
        enabled: Whether this effect is active
        highpass_freq: High-pass filter cutoff frequency in Hz
        lowpass_freq: Low-pass filter cutoff frequency in Hz
        mid_boost_freq: Mid-range boost frequency in Hz (optional)
        mid_boost_gain: Mid-range boost gain in dB (optional)
        mid_boost_q: Mid-range boost Q factor (optional)
        compressor_threshold: Compressor threshold in dB
        compressor_ratio: Compressor ratio (e.g., 4.0 = 4:1)
        compressor_attack: Attack time in seconds
        compressor_release: Release time in seconds
        distortion_amount: Waveshaper distortion amount (0=off, 20-50=mild-heavy)
        noise_level: Background noise level in dB (optional, e.g., -35)
        mono: Force mono output for authenticity
    """
    id: str = "none"
    enabled: bool = False
    highpass_freq: float = 300.0
    lowpass_freq: float = 3200.0
    mid_boost_freq: Optional[float] = None
    mid_boost_gain: Optional[float] = None
    mid_boost_q: Optional[float] = None
    compressor_threshold: float = -24.0
    compressor_ratio: float = 4.0
    compressor_attack: float = 0.003
    compressor_release: float = 0.25
    distortion_amount: int = 0
    noise_level: Optional[float] = None
    mono: bool = True


@dataclass
class AudioAssets:
    """
    Defines audio files and sound effects for the scene.

    Attributes:
        background_music: Path to background music/ambient sound
        sfx_library: Dictionary mapping event names to sound effect file paths
        volume_levels: Dictionary of volume settings for different audio types
        voice_effect: Voice processing effect configuration
    """
    background_music: Optional[str] = None
    sfx_library: Dict[str, str] = field(default_factory=dict)
    volume_levels: Dict[str, float] = field(default_factory=lambda: {
        'music': 0.5,
        'sfx': 0.8,
        'voice': 1.0
    })
    voice_effect: VoiceEffect = field(default_factory=VoiceEffect)


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
class SceneConstants:
    """
    Scene-specific gameplay constants.

    These override global defaults for scene-specific tuning.
    Use None to fall back to global constant values.
    """
    # Penalty values (for interruptions/rapid actions)
    interruption_oxygen_penalty: Optional[int] = None
    interruption_trust_penalty: Optional[int] = None
    rapid_action_oxygen_penalty: Optional[int] = None
    rapid_action_trust_penalty: Optional[int] = None

    # Crisis event values
    crisis_oxygen_penalty: Optional[int] = None
    crisis_trust_penalty: Optional[int] = None
    help_oxygen_bonus: Optional[int] = None
    help_trust_bonus: Optional[int] = None

    # Difficulty adjustments
    easy_oxygen_bonus: Optional[int] = None
    hard_oxygen_penalty: Optional[int] = None

    # Thresholds
    critical_level: Optional[int] = None  # e.g., critical oxygen level
    max_incorrect_actions: Optional[int] = None

    # Director settings
    disable_events: bool = False  # Disable random events (e.g., phone scene)
    director_cooldown_override: Optional[int] = None


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
        scene_constants: Scene-specific constant overrides
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
    scene_constants: SceneConstants = field(default_factory=SceneConstants)

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
                    'voice_effect': {
                        'id': self.art_assets.audio.voice_effect.id,
                        'enabled': self.art_assets.audio.voice_effect.enabled,
                        'highpass_freq': self.art_assets.audio.voice_effect.highpass_freq,
                        'lowpass_freq': self.art_assets.audio.voice_effect.lowpass_freq,
                        'mid_boost_freq': self.art_assets.audio.voice_effect.mid_boost_freq,
                        'mid_boost_gain': self.art_assets.audio.voice_effect.mid_boost_gain,
                        'mid_boost_q': self.art_assets.audio.voice_effect.mid_boost_q,
                        'compressor_threshold': self.art_assets.audio.voice_effect.compressor_threshold,
                        'compressor_ratio': self.art_assets.audio.voice_effect.compressor_ratio,
                        'compressor_attack': self.art_assets.audio.voice_effect.compressor_attack,
                        'compressor_release': self.art_assets.audio.voice_effect.compressor_release,
                        'distortion_amount': self.art_assets.audio.voice_effect.distortion_amount,
                        'noise_level': self.art_assets.audio.voice_effect.noise_level,
                        'mono': self.art_assets.audio.voice_effect.mono,
                    },
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
                    'visible_in_phases': ctrl.visible_in_phases,
                    'max_presses': ctrl.max_presses,
                    'cooldown_seconds': ctrl.cooldown_seconds,
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
            'scene_constants': {
                'interruption_oxygen_penalty': self.scene_constants.interruption_oxygen_penalty,
                'interruption_trust_penalty': self.scene_constants.interruption_trust_penalty,
                'rapid_action_oxygen_penalty': self.scene_constants.rapid_action_oxygen_penalty,
                'rapid_action_trust_penalty': self.scene_constants.rapid_action_trust_penalty,
                'crisis_oxygen_penalty': self.scene_constants.crisis_oxygen_penalty,
                'crisis_trust_penalty': self.scene_constants.crisis_trust_penalty,
                'help_oxygen_bonus': self.scene_constants.help_oxygen_bonus,
                'help_trust_bonus': self.scene_constants.help_trust_bonus,
                'easy_oxygen_bonus': self.scene_constants.easy_oxygen_bonus,
                'hard_oxygen_penalty': self.scene_constants.hard_oxygen_penalty,
                'critical_level': self.scene_constants.critical_level,
                'max_incorrect_actions': self.scene_constants.max_incorrect_actions,
                'disable_events': self.scene_constants.disable_events,
                'director_cooldown_override': self.scene_constants.director_cooldown_override,
            },
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
