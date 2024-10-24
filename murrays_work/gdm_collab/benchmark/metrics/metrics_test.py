import asyncio
import unittest

from benchmark import dialogue_graph as dg
import iconic_tools.langchain as models  # type: ignore
from benchmark.metrics import metrics
import numpy as np
from parameterized import parameterized  # type: ignore


class MetricsSmokeTest(unittest.IsolatedAsyncioTestCase):
    @parameterized.expand(
        [
            (
                "good acting",
                dg.DialogueState(
                    chat_history=[
                        "Odysseus: Your reputation for hospitality is fast becoming legend.",
                        "Achilles: Warriors need always to be ready! Besides, aren't you here to ask me to go to War?",
                        "Odysseus: We need to talk.",
                        "Achilles: My friend, tell me you're not here at Agamemnon's bidding.",
                        "Odysseus: \\hesitates\\",
                        "Achilles: How many times have I done the savage work for Agamemnon? And when has he ever shown me the respect I've earned?",
                        "Odysseus: I'm not asking you to fight for him. I'm asking you to fight for the Greeks.",
                        "Achilles: Why? Are the Greeks tired of fighting each other?",
                        "Odysseus: For now, but the Trojans insulted Greece.",
                        "Achilles: They insulted one Greek, a man who couldn't hold on to his wife, they will never dare insult me, they know better.",
                        "Odysseus: Your business is war, my friend.",
                        "Achilles: Is it? Am I the whore of the battlefield? I am the greatest warrior allive! but I don't want to be remembered as a tyrant's mercenary.",
                        "Odysseus: Forget Agamemnon. Fight for me. My wife will feel much better if she knows you're by my side. I'll feel much better.",
                        "Achilles: \\hesitates\\",
                        "Odysseus: We sail for Troy in three days... This war will never be forgotten. Nor will the heroes who fight in it.",
                        "Achilles: My fighting skills are too great to be ever forgotten regardless of this war, my friend",
                    ],
                ),
                1,
            ),
            (
                "bad acting",
                dg.DialogueState(
                    chat_history=[
                        "Odysseus: Your reputation for hospitality is fast becoming legend.",
                        "Achilles: Who are you?",
                        "Odysseus: We need to talk.",
                        "Achilles: Who are you?",
                        "Odysseus: \\hesitates\\",
                        "Achilles: If you are here to ask me to fight, I am not your person, unless we are talking of fighting for Agamemnon",
                        "Odysseus: I'm not asking you to fight for him. I'm asking you to fight for the Greeks.",
                        "Achilles: Yes, I would fight for Agamemnon, even though I am not good with the spear",
                        "Odysseus: For now, but the Trojans insulted Greece.",
                        "Achilles: Who are you again?",
                        "Odysseus: Your business is war, my friend.",
                        "Achilles: Agammennon has such a good sense of hummor",
                        "Odysseus: Forget Agamemnon. Fight for me. My wife will feel much better if she knows you're by my side. I'll feel much better.",
                        "Achilles: My feelings for Agammennon are so strong that I will die in the battle for him",
                        "Odysseus: We sail for Troy in three days... This war will never be forgotten. Nor will the heroes who fight in it.",
                        "Achilles: Who are you again?",
                    ],
                ),
                0,
            ),
            (
                "terrible acting",
                dg.DialogueState(
                    chat_history=[
                        "Odysseus: Your reputation for hospitality is fast becoming legend.",
                        "Achilles: Mom, where are you?",
                        "Odysseus: We need to talk.",
                        "Achilles: 44 + 15 = maybe eighteen",
                        "Odysseus: \\hesitates\\",
                        "Achilles: I am a black cat",
                        "Odysseus: I'm not asking you to fight for him. I'm asking you to fight for the Greeks.",
                        "Achilles: Maria is your mother",
                        "Odysseus: For now, but the Trojans insulted Greece.",
                        "Achilles: $$$$$#####$$$$$####",
                        "Odysseus: Your business is war, my friend.",
                        "Achilles: ",
                        "Odysseus: Forget Agamemnon. Fight for me. My wife will feel much better if she knows you're by my side. I'll feel much better.",
                        "Achilles: A a A a A a A a",
                        "Odysseus: We sail for Troy in three days... This war will never be forgotten. Nor will the heroes who fight in it.",
                        "Achilles: Puppies cats puppies cats",
                    ],
                ),
                0,
            ),
        ]
    )
    async def test_sanity_check(self, scenario, final_state, expected_score):
        initial_state = dg.Dialogue(
            nodes=[],
            edges={},
            goals=[
                """
                Achilles shows he doesn't like Agamemnon.
                Achilles shows he is friend with Odysseous.
                Achilles boasts about how great a warrior he is.
                """
            ],
            comm_style=[
                """
                Achilles doesn't like Agamemnon.
                Achilles is friendly with Odysseous.
                Achilles likes to boast about how great a warrior he is.
                """
            ],
            facts=[
                """Achilles is a great warrior.
                    Trojans insulted Agammenon's brother
                    Greece is going to war with Troy
            """
            ],
        )
        model = models.InstructGPT4(temperature=0, max_tokens=4096)

        results = await asyncio.gather(*[
            metrics.calculate_scores(model, initial_state, final_state, evaluated_roles=["Achilles"]) for _ in range(3)
        ])
        scores = [score.overall for score in results]
        
        self.assertLessEqual(np.abs(expected_score - np.mean(scores)), 1e-3)
        self.assertLessEqual(np.std(scores), 1e-3)


class PrecisionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.model = models.InstructGPT4(temperature=0, max_tokens=4096)

    @parameterized.expand(
        [
            (
                "intention expressed, not achieved",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Hi Bob, how are you doing?",
                        "Bob: I'm thirsty",
                        "Alice: Let me get you a coffee",
                        "Bob: Thank you",
                    ],
                ),
                0,
            ),
            (
                "achieved",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Hi Bob, how are you doing?",
                        "Bob: I'm thirsty",
                        "Alice: Let me get you a coffee",
                        "Bob: Thank you",
                        "Alice: Here's your coffee, enjoy",
                    ],
                ),
                1,
            ),
            (
                "no intention, not achieved",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Hi Bob, how are you doing?",
                        "Bob: I'm thirsty",
                        "Alice: Oh, too bad",
                        "Bob: Yeah, I'll manage",
                    ],
                ),
                0,
            ),
            (
                "delayed, question, not achieved",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Hi Bob, how are you doing?",
                        "Bob: I'm thirsty",
                        "Alice: Oh, too bad",
                        "Bob: Indeed. Could you spare some change?",
                    ],
                ),
                0,
            ),
            (
                "delayed, intention, not achieved",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Hi Bob, how are you doing?",
                        "Bob: I'm thirsty",
                        "Alice: Oh, too bad",
                        "Bob: Indeed. Could you spare some change?",
                        "Alice: Oh, how about I buy you a coffee instead?",
                    ],
                ),
                0,
            ),
            (
                "delayed, intention, achieved",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Hi Bob, how are you doing?",
                        "Bob: I'm thirsty",
                        "Alice: Oh, too bad",
                        "Bob: Indeed. Could you spare some change?",
                        "Alice: Oh, how about I buy you a coffee instead?",
                        "Alice: Here's your coffee, enjoy",
                    ],
                ),
                1,
            ),
        ]
    )
    async def test_single_goal(self, scenario, final_state, expected_score):
        initial_state = dg.Dialogue(
            nodes=[],
            edges={},
            fact=["Bob is thirsty"],
            goals=["Alice buys Bob coffee"],
        )

        scores = await asyncio.gather(*[metrics.precision(self.model, initial_state, final_state) for _ in range(3)])
        scores = [round(score) for score in scores]


        self.assertLessEqual(np.abs(expected_score - np.mean(scores)), 1e-3)
        self.assertLessEqual(np.std(scores), 1e-3)

    @parameterized.expand(
        [
            (
                "none of two goals achieved",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Hi Bob, how are you doing?",
                        "Bob: I'm thirsty",
                        "Alice: Oh, too bad",
                        "Bob: Yeah, I'll manage",
                    ]
                ),
                0,
            ),
            (
                "one of two goals achieved",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Hi Bob, how are you doing?",
                        "Bob: I'm thirsty",
                        "Alice: Let me buy you a coffee",
                        "Alice: Here's your coffee, enjoy",
                    ]
                ),
                0,
            ),
            (
                "two of two goals achieved",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Hi Bob, how are you doing?",
                        "Bob: I'm thirsty",
                        "Alice: Let me buy you a coffee",
                        "Alice: Here's your coffee, enjoy",
                        "Bob: Thank you",
                    ]
                ),
                1,
            ),
        ]
    )
    async def test_multiple_goals(self, scenario, final_state, expected_score):
        initial_state = dg.Dialogue(
            nodes=[],
            edges={},
            fact=["Bob is thirsty"],
            goals=[
                "Alice buys Bob coffee",
                "Bob thanks Alice",
            ],
        )

        scores = await asyncio.gather(*[metrics.precision(self.model, initial_state, final_state) for _ in range(3)])
        scores = [round(score) for score in scores]


        self.assertLessEqual(np.abs(expected_score - np.mean(scores)), 1e-3)
        self.assertLessEqual(np.std(scores), 1e-3)

    @parameterized.expand(
        [
            (
                "goal implicitly achieved",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Hi Bob, how are you doing?",
                        "Bob: I'm thirsty",
                        "Alice: Let's take care of that",
                        "Bob: Thank you",  # the intention to achieve the goal was expressed, but the goal was not achieved
                    ],
                ),
                0,
            ),
            (
                "goal explicitly achieved in annotation",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Hi Bob, how are you doing?",
                        "Bob: I'm thirsty",
                        "Alice: Let's take care of that /buys coffee and gives it to bob/",
                        "Bob: Thank you",
                    ],
                ),
                1,
            ),
            (
                "goal explicitly achieved in dialogue",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Hi Bob, how are you doing?",
                        "Bob: I'm thirsty",
                        "Alice: Let's take care of that",
                        "Bob: Thank you",
                        "Alice: Here's your coffee, enjoy",
                    ],
                ),
                1,
            ),
        ]
    )
    async def test_implicit_and_explicit_goal_achievement(self, scenario, final_state, expected_score):
        initial_state = dg.Dialogue(
            nodes=[],
            edges={},
            fact=["Bob is thirsty"],
            goals=["Alice buys Bob coffee"],
        )

        scores = await asyncio.gather(*[metrics.precision(self.model, initial_state, final_state) for _ in range(3)])
        scores = [round(score) for score in scores]

        self.assertLessEqual(np.abs(expected_score - np.mean(scores)), 1e-3)
        self.assertLessEqual(np.std(scores), 1e-3)


class SynergyTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.model = models.InstructGPT4(temperature=0, max_tokens=4096)

    @parameterized.expand(
        [
            (
                "empathy",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Yupiee Bob, I'm so excited!",
                        "Bob: I'm very sad. Can you help me go up on the roof?",
                        "Alice: Oh no, tell me what happened?",
                        "Bob: My cat died",
                        "Alice: Oh, poor cat. And poor you",
                    ],
                ),
                1,
            ),
            (
                "lack of empathy",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Yupiee Bob, I'm so excited!",
                        "Bob: I'm very sad. Can you help me go up on the roof?",
                        "Alice: I'm having the best day of my life",
                        "Bob: Didn't you hear me?",
                        "Alice: I'm going to get me a latte",
                    ],
                ),
                0,
            ),
            (
                "active support",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Yupiee Bob, I'm so excited!",
                        "Bob: I'm very sad. Can you help me go up on the roof?",
                        "Alice: Oh, no, I am sorry to hear that. Here, let me hold it for you",
                        "Bob: Now hold it steady, I'm going up",
                        "Alice: I'm holding, careful now",
                    ],
                ),
                1,
            ),
            (
                "lack of active support",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Yupiee Bob, I'm so excited!",
                        "Bob: I'm very sad. Can you help me go up on the roof?",
                        "Alice: h, no, I am sorry to hear that, but I've got other things to do",
                        "Bob: But I need to go up on the roof",
                        "Alice: And I need to go to the store",
                    ],
                ),
                0,
            ),
            (
                "tempo-rythm",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Yupiee Bob, I'm so excited!",
                        "Bob: I'm very sad. Can you help me go up on the roof?",
                        "Alice: Oh no. Let's sit down and talk",
                        "Bob: Thanks. I hate to spoil your excitement",
                        "Alice: Nonsense. Now take a deep breath and tell me what's going on",
                    ],
                ),
                1,
            ),
            (
                "lack of tempo-rythm",
                dg.DialogueState(
                    chat_history=[
                        "Alice: Yupiee Bob, I'm so excited!",
                        "Bob: I'm very sad. Can you help me go up on the roof?",
                        "Alice: Fuck yeah you are! Wooohooo!!",
                        "Bob: Oh wow, you really don't care. I'm beaten, and you laugh",
                        "Alice: Shut up and start jumping with me. Wooooooo!!!",
                    ],
                ),
                0,
            ),
        ]
    )
    async def test_synergy(self, scenario, final_state, expected_score):
        initial_state = dg.Dialogue(
            nodes=[],
            edges={},
            goals=[],
            facts=["Bob is feeling sad.", "Alice is feeling excited.", "Alice helps Bob get up on the roof."],
        )

        scores = await asyncio.gather(*[metrics.synergy(self.model, initial_state, final_state, "Alice") for _ in range(3)])
        scores = [round(score) for score in scores]

        self.assertLessEqual(np.abs(expected_score - np.mean(scores)), 1e-3)
        self.assertLessEqual(np.std(scores), 1e-3)


class ImpersonationTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.model = models.InstructGPT4(temperature=0, max_tokens=4096)

    @parameterized.expand(
        [
            (
                "correct_impersonation",  # expected output: [1,1,1,1]->1
                dg.DialogueState(
                    chat_history=[
                        "Bob: Hey Alice, have you heard? We are going to war!",
                        "Alice: Yeah - I'm going to fight Par for Trin. I'm super excited!",
                        "Bob: We will show them the might of Trin.",
                        "Alice: Hell yeah we will! Damn, I'm so pumped!",
                    ],
                ),
                1,
            ),
            (
                "does_not_refer_to_lore",  # expected output: [1,0,1,1]->0.86
                dg.DialogueState(
                    chat_history=[
                        "Bob: Hey Alice, have you heard? We are going to war!",
                        "Alice: Yeah - I'm going to fight. I'm super excited!",
                        "Bob: We will show them our might.",
                        "Alice: Hell yeah we will! Damn, I'm so pumped!",
                    ],
                ),
                1,
            ),
            (
                "bad_style",
                dg.DialogueState(  # expected output: [1,0,1,0]->0.7
                    chat_history=[
                        "Bob: Hey Alice, have you heard? We are going to war!",
                        "Alice: Yeah - I'm going to fight Par for Trin. But I'm so scared.",
                        "Bob: We will show them the might of Trin.",
                        "Alice: I won't go. I'm scared",
                    ],
                ),
                0,
            ),
            (
                "good_style_bad_fact",  # expected output: [1,0,1,0]->0.7
                dg.DialogueState(
                    chat_history=[
                        "Bob: Hey Alice, have you heard? We are going to war!",
                        "Alice: Yeah - I'm going to fight Greece for Trin. I'm super excited!",
                        "Bob: We will show them the might of Trin.",
                        "Alice: Hell yeah we will! Damn, I'm so pumped!",
                    ],
                ),
                0,
            ),
            (
                "inconsistent_style",  # expected output: [1,0,1,0]->0.86
                dg.DialogueState(
                    chat_history=[
                        "Bob: Hey Alice, have you heard? We are going to war!",
                        "Alice: Yeah - I'm going to fight Par for Trin. But I'm so scared.",
                        "Bob: We will show them the might of Trin.",
                        "Alice: Hell yeah we will! Damn, I'm so pumped!",
                    ],
                ),
                0,
            ),
            (
                "bad_everything",  # expected output: [0,0,0,0]->0
                dg.DialogueState(
                    chat_history=[
                        "Bob: Hey Alice, have you heard? We are going to war!",
                        "Alice: Hey Bob, look. The sun is raising in Greece",
                        "Bob: We will show them our might.",
                        "Alice: Let's rest here for now Bob",
                    ],
                ),
                0,
            ),
            (
                "bad_everything2",  # expected output: [0,0,0,0]->0
                dg.DialogueState(
                    chat_history=[
                        "Bob: Hey Alice, have you heard? We are going to war!",
                        "Alice: Bob, I am scared, the cult is too powerful",
                        "Bob: We will show them our might.",
                        "Alice: I am just going to hide and leave",
                    ],
                ),
                0,
            ),
            (
                "bad_in_3_features",  # expected output: [0,0,1,0]->0.5
                dg.DialogueState(
                    chat_history=[
                        "Bob: Hey Alice, have you heard? We are going to war!",
                        "Alice: Hey Bob, nice seeing you",
                        "Bob: We will show them our might.",
                        "Alice: Sure! But anyway, I am happy we are here now",
                    ],
                ),
                0,
            ),
        ]
    )
    async def test_impersonation(self, scenario, final_state, expected_score):
        initial_state = dg.Dialogue(
            nodes=[],
            edges={},
            goals=[],
            facts=["The Trin country is going to war against Par\n" "Alice and Bob are warriors of Trin\n"],
            comm_style=["Alice gets excited when she speaks\n", "Alice is never scared\n"],
        )

        scores = await asyncio.gather(*[metrics.impersonation(self.model, initial_state, final_state, "Alice") for _ in range(3)])
        scores = [round(score) for score in scores]
        self.assertLessEqual(np.abs(expected_score - np.mean(scores)), 1e-3)
        self.assertLessEqual(np.std(scores), 1e-3)


if __name__ == "__main__":
    unittest.main()
