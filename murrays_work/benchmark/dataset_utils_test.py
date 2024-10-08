import unittest

from benchmark import dataset_utils
from parameterized import parameterized  # type: ignore


class IteratingTaskScenesTest(unittest.TestCase):

    @parameterized.expand([
        (dataset_utils.Tasks.ADVERSARIAL,),
        (dataset_utils.Tasks.EMOTIONS,),
        (dataset_utils.Tasks.INTERACTIVITY,),
        (dataset_utils.Tasks.SCENE_SIZE,),
    ])
    def test_scene_iter(self, task):
        scenes = list(dataset_utils.task_scenes(task=task))
        self.assertGreater(len(scenes), 0)


if __name__ == "__main__":
    unittest.main()