# LLM Prompt Core

A generic, flexible framework for building interactive NPC dialogue systems using large language models (LLMs). This module provides a provider-agnostic interface that works with Claude (Anthropic), OpenAI, and Google Gemini models.

## Overview

The LLM Prompt Core system enables developers to create sophisticated character dialogue experiences with:

- **Multi-scene narrative progression** - Guide players through a structured story with context-aware dialogue
- **Dynamic query system** - Trigger state changes and scene transitions based on conversation content
- **Dialogue history management** - Maintain context across scenes with intelligent summarization
- **Provider flexibility** - Switch between Claude, OpenAI, and Gemini models seamlessly
- **Clean separation** - Core dialogue logic is independent of game engine implementation

## Architecture

### Module Structure

```
llm_prompt_core/
├── __init__.py              # Public API exports
├── models/
│   ├── __init__.py
│   ├── base.py              # Abstract LLM interface
│   ├── anthropic.py         # Claude model wrappers
│   ├── openai.py            # OpenAI model wrappers
│   └── gemini.py            # Google Gemini wrappers
├── prompts/
│   ├── __init__.py
│   ├── templates.py         # Prompt template strings
│   └── builder.py           # Template composition utilities
├── types.py                 # Data classes (Line, Query, SceneData)
└── utils.py                 # Helper functions
```

### Core Components

1. **Models** - LangChain-compatible wrappers for different LLM providers
2. **Prompts** - Template system for building context-aware prompts
3. **Types** - Data structures for scenes, queries, dialogue lines, and state changes
4. **Utils** - String formatting, file loading, and chain building utilities

## Character Prompt System

### Scene Structure

The system organizes conversations into **scenes** - discrete narrative units with their own context. Each scene contains:

- **Scene description** - What's happening in this moment of the story
- **Back story** - Persistent world context shared across all scenes
- **Previous scenes description** - Summary of events leading to this scene
- **Opening speech** - Lines spoken when the scene begins
- **Queries** - Conditional checks that trigger state changes or scene transitions
- **Dialogue summary** - Accumulated context from previous conversations

### Prompt Components

Every LLM prompt is built from several components:

#### 1. Preamble
Sets up the context for the LLM, including:
- Instruction prefix (what role the LLM should play)
- Back story (persistent world context)
- Scene description (current situation)
- Previous scenes summary (narrative history)
- Steering instructions (guidelines to keep dialogue on track)
- Character list (who's in the conversation)

#### 2. Dialogue History
The conversation so far, formatted as:
```
[Character]: dialogue text
[Player]: player response
[Character]: next dialogue line
```

#### 3. Instruction Suffix
Specific request for the LLM:
- **Dialogue generation**: "Give me the next line in the dialogue..."
- **Query evaluation**: "Is this statement true or false?..."
- **Summary generation**: "Summarize the information revealed..."

### Template Architecture

The system uses several specialized templates:

- `preamble_template` - Basic context setup
- `preamble_plus_template` - Extended context with dialogue summary
- `query_preamble_template` - Minimal context for query evaluation
- `merge_preamble_template` - Context for merging summaries
- `instruction_template` - Combines preamble, dialogue, and instruction
- `speech_template` - Formats individual dialogue lines

### Dialogue History and Context Management

As conversations progress, the system maintains context through:

1. **Full dialogue history** - Complete record of the current scene
2. **Dialogue summaries** - Compressed information from previous scenes
3. **Summary merging** - Combines summaries to avoid context bloat

The summary system extracts:
- Personal information revealed by characters
- Tastes and preferences
- Events that occurred
- How NPCs address the player

## Model Integration

### Installation

```bash
# Install core dependencies
pip install langchain-core pydantic

# Install provider SDKs (install only what you need)
pip install anthropic  # For Claude models
pip install openai     # For OpenAI models
pip install google-genai  # For Gemini models
```

### Configuration

Set environment variables for your chosen provider:

```bash
# For Claude (Anthropic)
export ANTHROPIC_API_KEY="your-api-key-here"

# For OpenAI
export OPENAI_API_KEY="your-api-key-here"

# For Gemini
export GOOGLE_API_KEY="your-api-key-here"
```

### Using Claude Models (Recommended)

```python
from llm_prompt_core.models.anthropic import ClaudeSonnet45Model

# Use Claude Sonnet 4.5 (balanced performance and cost)
dialogue_model = ClaudeSonnet45Model(temperature=0.8, max_tokens=1500)
summary_model = ClaudeSonnet45Model(temperature=0.2, max_tokens=5000)
query_model = ClaudeSonnet45Model(temperature=0.2, max_tokens=300)
```

Available Claude models:
- `ClaudeSonnet45Model` - Balanced, recommended for most use cases
- `ClaudeOpus4Model` - Most capable, for complex tasks
- `ClaudeHaikuModel` - Fast and efficient, for simpler tasks

### Using OpenAI Models

```python
from llm_prompt_core.models.openai import GPT4oModel

dialogue_model = GPT4oModel(temperature=0.8, max_tokens=1500)
summary_model = GPT4oModel(temperature=0.2, max_tokens=5000)
query_model = GPT4oModel(temperature=0.2, max_tokens=300)
```

Available OpenAI models:
- `GPT4oModel` - Fast with multimodal support
- `GPT4TurboModel` - Extended context window
- `GPT35TurboModel` - Cost-effective for simpler tasks

### Using Gemini Models

```python
from llm_prompt_core.models.gemini import GeminiFlash25NoThinking

dialogue_model = GeminiFlash25NoThinking(temperature=0.8, max_tokens=1500)
summary_model = GeminiFlash25NoThinking(temperature=0.2, max_tokens=5000)
query_model = GeminiFlash25NoThinking(temperature=0.2, max_tokens=300)
```

### Model Selection Guidelines

**Temperature settings:**
- **0.2** - Deterministic, focused (good for queries and summaries)
- **0.8** - Creative, varied (good for dialogue generation)

**Max tokens:**
- **300** - Short responses (queries, yes/no answers)
- **1500** - Single dialogue lines
- **5000** - Summaries of long conversations

**Model choice:**
- **Claude Sonnet 4.5** - Best overall balance of quality, speed, and cost
- **Claude Opus 4** - Maximum quality for critical dialogue
- **GPT-4o** - Good alternative with strong performance
- **Gemini Flash 2.5** - Fast and cost-effective

## API Reference

### Data Types

#### `Line`
Represents a single line of dialogue.

```python
@dataclass
class Line:
    text: str       # The dialogue text
    delay: float    # Delay in seconds before displaying
```

#### `StateChange`
Represents a change in application/game state.

```python
@dataclass
class StateChange:
    name: str       # State variable name
    value: str      # New value to set
```

#### `Query`
Conditional check that evaluates against dialogue history.

```python
@dataclass
class Query:
    text: str                           # Statement to evaluate (true/false)
    state_changes: List[StateChange]    # Changes to apply if true
    handled: bool = False               # Whether query has been evaluated
    query_printed: bool = False         # Whether to print a message
    query_printed_text_true: str = ""   # Message if true
    query_printed_text_false: str = ""  # Message if false
```

#### `SceneData`
Container for all scene-related context.

```python
@dataclass
class SceneData:
    scene_name: str
    scene_description: str
    previous_scenes_description: str
    steer_back_instructions: str
    scene_supplement: str
    back_story: str
    dialogue_instruction_prefix: str
    summary_instruction_prefix: str
    merge_instruction_prefix: str
    opening_speech: List[Line]
    queries: List[Query]
    actors: List[str] = ["NPC", "Player"]
    dialogue_summary: str = ""

    # Methods
    def get_initial_dialog(self, print_callback=None) -> str
    def run_queries(self, dialogue: str, query_model, print_callback=None) -> Tuple[List[StateChange], str]
    def all_queries_handled(self) -> bool
```

### PromptBuilder

Static methods for building prompts:

```python
class PromptBuilder:
    @staticmethod
    def build_preamble(...) -> str
        """Build context preamble for dialogue generation."""

    @staticmethod
    def build_query_preamble(...) -> str
        """Build preamble for query evaluation."""

    @staticmethod
    def build_dialogue_prompt(preamble: str, dialogue: str) -> str
        """Build complete prompt for next dialogue line."""

    @staticmethod
    def build_query_prompt(preamble: str, dialogue: str, statement: str) -> str
        """Build prompt for evaluating a true/false statement."""

    @staticmethod
    def build_summary_prompt(preamble: str, dialogue: str) -> str
        """Build prompt for generating dialogue summary."""

    @staticmethod
    def build_merge_prompt(preamble: str, prev_summary: str, new_summary: str) -> str
        """Build prompt for merging two summaries."""
```

### Utilities

```python
# String formatting
def list_to_conjunction(L: List[str]) -> str
    """Join list with commas and 'and': ['A', 'B', 'C'] -> 'A, B, and C'"""

# LangChain integration
def prompt_llm(prompt: str, model)
    """Build a LangChain chain from prompt template and model."""

# File loading
def resource_path(base_path: str = None) -> str
    """Get absolute path to resource directory."""

def load_file(file_path: str) -> str
    """Load text file, return contents or empty string if not found."""
```

## Examples

### Example 1: Simple Dialogue Generation

```python
from llm_prompt_core.types import SceneData, Line, Query
from llm_prompt_core.models.anthropic import ClaudeSonnet45Model
from llm_prompt_core.utils import prompt_llm
from llm_prompt_core.prompts.templates import instruction_template, dialogue_instruction_suffix

# Initialize model
model = ClaudeSonnet45Model(temperature=0.8, max_tokens=1500)

# Create scene data
scene = SceneData(
    scene_name="tavern_meeting",
    scene_description="You meet a mysterious stranger in a dimly lit tavern.",
    previous_scenes_description="",
    steer_back_instructions="Keep the conversation focused on the quest.",
    scene_supplement="",
    back_story="You're a hero seeking the ancient artifact.",
    dialogue_instruction_prefix="You are generating dialogue for a fantasy RPG.",
    summary_instruction_prefix="You are summarizing dialogue.",
    merge_instruction_prefix="You are merging summaries.",
    opening_speech=[Line(text="Greetings, traveler. I hear you seek something...", delay=0)],
    queries=[],
    actors=["Stranger", "Player"]
)

# Get opening dialogue
dialogue = scene.get_initial_dialog(print_callback=print)

# Add player response
dialogue += "[Player]: Yes, I'm looking for the ancient artifact.\n\n"

# Generate NPC response
prompt = instruction_template.format(
    preamble=scene.dialogue_preamble,
    dialogue=dialogue,
    instruction_suffix=dialogue_instruction_suffix
)
chain = prompt_llm(prompt, model)
response = chain.invoke({})
print(response)
```

### Example 2: Query-Based State Changes

```python
from llm_prompt_core.types import SceneData, Line, Query, StateChange

# Create scene with queries
scene = SceneData(
    scene_name="password_gate",
    scene_description="A locked gate blocks your path. A guard asks for the password.",
    # ... other fields ...
    opening_speech=[Line(text="Halt! What's the password?", delay=0)],
    queries=[
        Query(
            text="The player has said the correct password",
            state_changes=[StateChange(name="gate_open", value="true")],
            query_printed_text_true="The gate creaks open.",
            query_printed_text_false=""
        )
    ],
    actors=["Guard", "Player"]
)

# Simulate conversation
dialogue = scene.get_initial_dialog()
dialogue += "[Player]: The password is 'nightingale'.\n"

# Check queries
state_changes, message = scene.run_queries(dialogue, query_model)
if state_changes:
    print(f"State changes: {state_changes}")
    print(f"Message: {message}")
```

### Example 3: Multi-Scene Progression

```python
# Scene 1: Initial meeting
scene1 = load_scene_data("1_meet_the_merchant")
dialogue1 = scene1.get_initial_dialog()
# ... conversation happens ...

# Generate summary of scene 1
summary1 = generate_summary(dialogue1, scene1)

# Scene 2: Continuation with context
scene2 = load_scene_data("2_negotiate_price", dialogue_summary=summary1)
dialogue2 = scene2.get_initial_dialog()
# ... conversation happens ...

# Generate and merge summaries
summary2 = generate_summary(dialogue2, scene2)
merged_summary = merge_summaries(summary1, summary2, scene2)

# Scene 3: Using merged context
scene3 = load_scene_data("3_finalize_deal", dialogue_summary=merged_summary)
```

## Scene Data Format

Scenes are typically loaded from text files with the following structure:

### Directory Structure
```
prompts/
├── back_story.txt
├── dialogue_instruction_prefix.txt
├── summary_instruction_prefix.txt
├── merge_instruction_prefix.txt
├── steer_back_instructions.txt
└── scenes/
    ├── 1_tavern_meeting/
    │   ├── scene_description.txt
    │   ├── prev_scenes_description.txt
    │   ├── scene_supplement.txt
    │   ├── opening_speech.txt
    │   └── queries.txt
    └── 2_forest_path/
        └── ...
```

### File Formats

**opening_speech.txt** - Lines spoken when scene starts:
```
[0] Welcome, traveler!
[2.5] I've been expecting you.
Have you come about the artifact?
```
Format: `[delay] text` or just `text` (delay defaults to 0)

**queries.txt** - Conditional checks:
```
The player has mentioned the artifact
[quest_started=true, artifact_known=true]
(I see you know what you're looking for., Keep searching...)

The player has agreed to help
[quest_accepted=true]
(Excellent! I'll mark it in your quest log., )
```
Format:
- Statement to evaluate (true/false)
- `[state1=value1, state2=value2]` - State changes if true
- `(message_if_true, message_if_false)` - Optional messages

**scene_description.txt** - Current scene context:
```
You stand in a bustling tavern. The mysterious stranger sits in the corner,
watching you carefully. The room smells of ale and woodsmoke.
```

**back_story.txt** - Persistent world context:
```
You are a hero in a fantasy world. Long ago, an ancient artifact was lost.
Now, dark forces are rising, and only the artifact can stop them.
```

## Extending the System

### Adding a New LLM Provider

1. Create a new file in `llm_prompt_core/models/`:

```python
# llm_prompt_core/models/mymodel.py
from llm_prompt_core.models.base import BaseLLMModel

class MyCustomModel(BaseLLMModel):
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize your model client

    def _call(self, prompt: str, stop=None, run_manager=None, **kwargs) -> str:
        # Call your model API
        response = self.client.generate(prompt, **kwargs)
        return response.text

    @property
    def _llm_type(self) -> str:
        return "my-custom-model"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {"model_name": self.model_name, ...}
```

2. Export from `models/__init__.py`:

```python
from llm_prompt_core.models.mymodel import MyCustomModel

__all__ = [..., "MyCustomModel"]
```

3. Use it like any other model:

```python
from llm_prompt_core.models.mymodel import MyCustomModel
model = MyCustomModel(temperature=0.8, max_tokens=1500)
```

### Custom Prompt Templates

Create your own templates:

```python
my_custom_template = """
You are a {character_type} in a {genre} story.
{back_story}
Current situation: {scene_description}
Previous dialogue: {dialogue}
Generate the next line.
"""

# Use with PromptBuilder
prompt = my_custom_template.format(
    character_type="wizard",
    genre="fantasy",
    back_story=scene.back_story,
    scene_description=scene.scene_description,
    dialogue=dialogue_history
)
```

### Custom Scene Loaders

Implement custom loading logic:

```python
def load_scene_from_json(json_path: str) -> SceneData:
    import json
    with open(json_path) as f:
        data = json.load(f)

    return SceneData(
        scene_name=data["name"],
        scene_description=data["description"],
        # ... map JSON fields to SceneData ...
        actors=data.get("characters", ["NPC", "Player"])
    )
```

### Custom Query Evaluators

Implement domain-specific query logic:

```python
class CustomSceneData(SceneData):
    def run_queries(self, dialogue: str, query_model, print_callback=None):
        # Custom query evaluation logic
        for query in self.queries:
            # Use regex, keyword matching, or LLM evaluation
            if self.custom_evaluate(query, dialogue):
                query.handled = True
                # Apply state changes
```

## Best Practices

1. **Model Selection**
   - Use Claude Sonnet 4.5 for production (best balance)
   - Use Haiku/GPT-3.5 Turbo for development/testing (faster/cheaper)
   - Use Opus 4 only for critical narrative moments

2. **Temperature Tuning**
   - 0.2 for factual queries and summaries (deterministic)
   - 0.8 for dialogue (creative but consistent)
   - 1.0+ for highly varied responses (use sparingly)

3. **Context Management**
   - Summarize after each scene (don't let context grow unbounded)
   - Merge summaries rather than concatenating
   - Keep scene descriptions focused (200-300 words max)

4. **Query Design**
   - Make queries specific and testable
   - Use simple, declarative statements
   - Avoid complex compound conditions

5. **Error Handling**
   - Always check if API keys are set
   - Provide fallback responses if LLM calls fail
   - Log errors for debugging

## Troubleshooting

### Import Errors

```python
# Error: ModuleNotFoundError: No module named 'anthropic'
# Solution:
pip install anthropic

# Error: ModuleNotFoundError: No module named 'openai'
# Solution:
pip install openai
```

### API Key Errors

```python
# Error: ANTHROPIC_API_KEY environment variable must be set
# Solution:
export ANTHROPIC_API_KEY="your-key-here"

# Or set in Python:
import os
os.environ["ANTHROPIC_API_KEY"] = "your-key-here"
```

### Model Response Issues

If the model generates unexpected responses:
1. Check your temperature setting (lower = more focused)
2. Review your prompt templates for clarity
3. Add more specific instructions to steering text
4. Verify scene descriptions provide enough context

## License

This module is part of the Digital Actors project.

## Contributing

When contributing:
1. Keep core logic independent of game engines
2. Follow the existing abstractions (BaseLLMModel, PromptBuilder, etc.)
3. Add tests for new model providers
4. Update this README with new features

## Support

For issues and questions:
- Check the examples in this README
- Review the inline documentation in source files
- Examine the `project_one_demo` integration for reference
