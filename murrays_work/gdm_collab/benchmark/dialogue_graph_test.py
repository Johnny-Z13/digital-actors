import unittest

from benchmark import dialogue_graph


class DialogueSerializationTest(unittest.TestCase):

    def test_serialize_dialogue(self):
        scene = dialogue_graph.Dialogue(
            facts=["fact 1", "fact 2"],
            comm_style = ["cs 1", "cs 2"],
            goals=["goal 1", "goal 2"]
        )

        serialized_scene = scene.serialize()
        deserialized_scene = dialogue_graph.Dialogue.deserialize(serialized_scene)
        self.assertEqual(scene, deserialized_scene)

    def test_serialize_dialogue_state(self):
        state = dialogue_graph.DialogueState(
            chat_history=[
                "Alice: Hey Bob",
                "Bob: Hey Alice",
            ]
        )

        serialized_state = state.serialize()
        deserialized_state = dialogue_graph.DialogueState.deserialize(serialized_state)
        self.assertEqual(state, deserialized_state)


if __name__ == "__main__":
    unittest.main()
