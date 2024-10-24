import unittest

from benchmark import dialogue_graph_utils as dgu
from benchmark import dialogue_graph as dg


class DialogueStateDumpTest(unittest.TestCase):

    def test_state_dump(self):
        dialogue = dg.Dialogue(
            facts=["Fact1", "Fact2"],
            comm_style=["Style1", "Style2"],
            goals=["Goal1", "Goal2"],
        )
        state = dg.DialogueState(
            chat_history = [
                "Alice: Hey Bob",
                "Bob: Hey Alice",
                "Bob: I'm great, how are you?",
                "Alice: Lousy"
            ],
        )

        state_str = dgu.dumps_full_state(dialogue, state)

        self.assertEqual(state_str, """<dialogue_state_start>
<facts_start>
Fact1
Fact2
<facts_end>

<style_start>
Style1
Style2
<style_end>

<goals_start>
Goal1
Goal2
<goals_end>

<chat_history_start>
Alice: Hey Bob
Bob: Hey Alice
Bob: I'm great, how are you?
Alice: Lousy
<chat_history_end>
<dialogue_state_end>""")


if __name__ == "__main__":
    unittest.main()
