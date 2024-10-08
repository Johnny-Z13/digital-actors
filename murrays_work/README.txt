This repo contains Python notebooks for generating and evaluating dialogues for movie or game scenes using LLMs.

The notebook "generate_dialogues.ipynb" creates a set of dialogues and saves them in the "transcripts" directory. A set of dialogues is generated for each of a given set of scenes within a given set of games (movies). Each scene is specified by a set of prompt text files found in the relevant sub-directory of "prompts" for the game (movie) in question.

Each scene of each game (movie) is specified by a set of four text files that are loaded and assembled in the prompt submitted to the language model:

    prompts/{game_name}/back_story.txt: The backdrop to the whole game.

    prompts/{game_name}/{scene_name}/{scene_name}_scene_description.txt: A description of this particular mini-scene. Should state the goals of the scene.

    prompts/{game_name}/{scene_name}/{scene_name}_opening_speech: The first words spoken in the dialogue (which are hand scripted).

    prompts/{game_name}/{scene_name}/{scene_name}_scene_supplement: Optional extra text describing the scene. Can be used to simulate adversarial players, for example.

Each generated dialogue is saved in a file:

    transcripts/{game_name}/transcript_{model}_{method}_{number}.txt

where {model} is the language model used to generate the dialogue (GPT4, GemeniPr0, etc), {method} is the prompting technique used (e.g. "naive" or "handmade"), and {number} is the run number.

The notebook "evaluate_dialogues.ipynb" carries out a series of tests on each of the saved dialogue transcripts. The tests it carries out, like the scenes themselves, are specified by a set of prompt text files in the relevant sub_directory of "prompts" for the game (movie) in question. Each of these text files contains a sequence of units tests expressed as natural language sentences that can be either true or false for a given dialogue transcript. They are:

    prompts/{game_name}/{scene_name}/{scene_name}_goal_tests.txt: A sequence of sentences specifying what should be true at the end of the dialogue. This contributes to the "precision" metric.

    prompts/{game_name}/{scene_name}/{scene_name}_style_tests.txt: A sequence of sentences describing the communication style of the actors. This contributes to the "impersonation" metric.

The results of the evaluation are saved and are plotted in bar charts.

Additional files in the repo include:

    prompts/synergy_tests.txt: This is a sequence of sentences specifying holistic properties of the dialogue; whether it "hangs together". These tests are incorporated in the "synergy" metric.

    transcripts/ex_machina.txt: This is a fragment of dialogue extracted from the film Ex Machina, which is used to construct baseline dialogues (expeted to have low precision and impersonation scores).

    make_baselines.ipynb: A python notebook for creating baselines from the Ex Machina fragment, by substituting the actual actor names associated with each saved transcript for the original Ex Machina actor names (resulting in something deliberately silly with respect to the relevant game (movie)).

    generate_evaluate_dialogue.txt: This notebook is adapted from Piotr's code for simultaneously generating and evaluating dialogues, but uses my generation method and my prompts.

    results.json: The saved results obtained from running evaluate_dialogues.ipynb.