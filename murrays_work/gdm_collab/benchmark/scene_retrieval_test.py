import unittest
import iconic_tools.langchain as models
from benchmark.scene_retrieval import get_context_for_scene


class SceneRetrievalTest(unittest.TestCase):

    def test_get_context_for_scene(self):
        model = models.InstructGPT4(temperature=0, max_tokens=4096)
        blob, decomposed = get_context_for_scene(model, "sci-fi", "interstellar", 33)

        self.assertIsInstance(blob, str, "Blob should be a string")
        self.assertIsInstance(decomposed, list, "Decomposed should be a list")
        self.assertEqual(len(decomposed), 3, "Decomposed should have three elements")
        self.assertIsInstance(decomposed[0], str, "First element of decomposed should be a string (history summary)")
        self.assertIsInstance(decomposed[1], list, "Second element of decomposed should be a list (goals)")
        self.assertIsInstance(decomposed[2], dict, "Third element of decomposed should be a dictionary (character descriptions)")


if __name__ == "__main__":
    unittest.main()
