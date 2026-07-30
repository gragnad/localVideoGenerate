import json
import unittest

from workflow_builder import SegmentSpec, build_workflow


class DirectorWorkflowBuilderTests(unittest.TestCase):
    def test_uses_soft_visual_relay_and_tighter_audio_boundaries(self):
        template = {
            "director": {
                "class_type": "LTXDirector",
                "inputs": {
                    "timeline_data": json.dumps(
                        {
                            "global_prompt": "",
                            "segments": [],
                            "motionSegments": [],
                            "audioSegments": [],
                        }
                    ),
                    "epsilon": 0.001,
                },
            },
            "noise": {"class_type": "RandomNoise", "inputs": {}},
            "save": {"class_type": "SaveVideo", "inputs": {}},
        }
        segments = [
            SegmentSpec("01.png", "scene", "first action", 5, 1),
            SegmentSpec("02.png", "scene", "second action", 5, 2),
        ]

        workflow, summary = build_workflow(
            template,
            segments,
            global_prompt="same continuous shot",
            fps=24,
            seed=1,
            filename_prefix="test/director",
        )

        inputs = workflow["director"]["inputs"]
        timeline = json.loads(inputs["timeline_data"])
        self.assertEqual(inputs["epsilon"], 0.5)
        self.assertEqual(timeline["relayOptions"]["audioEpsilon"], 0.01)
        self.assertEqual(inputs["guide_strength"], "0.75,0.75")
        self.assertEqual(summary["prompt_relay_epsilon"], 0.5)
        self.assertEqual(summary["audio_prompt_relay_epsilon"], 0.01)
        self.assertEqual(summary["image_guide_strength"], 0.75)


if __name__ == "__main__":
    unittest.main()
