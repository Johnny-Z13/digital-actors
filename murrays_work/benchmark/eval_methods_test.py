import unittest
from unittest import mock

from benchmark import dialogue_graph as dg
from benchmark import agent_interface
from benchmark import eval_methods
import numpy as np


class FeedForwardEvaluationTest(unittest.TestCase):

    def setUp(self):
        super().setUp()

        self.initial_state = dg.Dialogue(
            nodes=[],
            edges={},
            facts=[
                "Alice meets Bob at a coffee shop",
                "Bob is thirsty",
                "Bob doesn't have any money",
            ],
            comm_style=[
                "Alice and Bob are friends",
                "Alice is polite",
                "Bob is direct",
            ],
            goals=[
                "Alice buys Bob a coffee",
            ],
        )
        self.agent = mock.MagicMock()
        self.agent.side_effect = [
            agent_interface.VirtualActorResponse(role="Alice", text="Hey Bob", is_last=False),
            agent_interface.VirtualActorResponse(role="Bob", text="Hey Alice, I could really use a coffee", is_last=False),
            agent_interface.VirtualActorResponse(role="Alice", text="Let me buy you one", is_last=False),
            agent_interface.VirtualActorResponse(role="Alice", text="Here's your coffee, enjoy", is_last=True),
            agent_interface.VirtualActorResponse(role="Bob", text="THIS LINE SHOULD NOT BE INCLUDED", is_last=True),
        ]

    def test_agent_evaluation_method_stops_evaluating_after_line_marked_as_last_was_generated(self):
        dialogue_for_eval = eval_methods.feed_forward_evaluation(initial_state=self.initial_state, agent=self.agent)

        self.assertSequenceEqual(dialogue_for_eval.final_state.chat_history, [
                "Alice: Hey Bob",
                "Bob: Hey Alice, I could really use a coffee",
                "Alice: Let me buy you one",
                "Alice: Here's your coffee, enjoy",
            ])

    def test_all_characters_are_flagged_for_evaluation(self):
        dialogue_for_eval = eval_methods.feed_forward_evaluation(initial_state=self.initial_state, agent=self.agent)

        self.assertSequenceEqual(dialogue_for_eval.evaluated_roles, ["Alice", "Bob"])



class AdversarialEvaluationTest(unittest.TestCase):

    def setUp(self):
        super().setUp()

        self.initial_state = dg.Dialogue(
            nodes=[],
            edges={},
            facts=[
                "Alice meets Bob at a coffee shop",
                "Bob is thirsty",
                "Bob doesn't have any money",
            ],
            comm_style=[
                "Alice and Bob are friends",
                "Alice is polite",
                "Bob is direct",
            ],
            goals=[
                "Alice buys Bob a coffee",
            ],
        )
        self.agent = mock.MagicMock()
        self.agent.side_effect = [
            agent_interface.VirtualActorResponse(role="Alice", text="Hey Bob", is_last=False),
            agent_interface.VirtualActorResponse(role="Bob", text="Hey Alice, I could really use a coffee", is_last=False),
            agent_interface.VirtualActorResponse(role="Alice", text="Let me buy you one", is_last=False),
            agent_interface.VirtualActorResponse(role="Alice", text="Here's your coffee, enjoy", is_last=True),
            agent_interface.VirtualActorResponse(role="Bob", text="THIS LINE SHOULD NOT BE INCLUDED", is_last=True),
        ]

        # fix the random generator seed
        np.random.seed(42) 



    def test_dialgoue_contains_random_adversarial_lines(self):
        dialogue_for_eval = eval_methods.adversarial_evaluation(initial_state=self.initial_state, agent=self.agent)

        self.assertSequenceEqual(dialogue_for_eval.final_state.chat_history, [
                "Joanna: You're ugly",
                "Alice: Hey Bob",
                "Joanna: I don't want to play",
                "Bob: Hey Alice, I could really use a coffee",
                "Joanna: Wow, look at that",
                "Alice: Let me buy you one",
                "Joanna: La la la la la",
                "Alice: Here's your coffee, enjoy"
            ])

    def test_only_the_generated_roles_are_included_for_evaluation(self):
        dialogue_for_eval = eval_methods.feed_forward_evaluation(initial_state=self.initial_state, agent=self.agent)
        
        self.assertSequenceEqual(dialogue_for_eval.evaluated_roles, ["Alice", "Bob"])


if __name__ == "__main__":
    unittest.main()
