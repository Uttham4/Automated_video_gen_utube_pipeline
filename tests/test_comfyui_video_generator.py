import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from app.ai.comfyui_video_generator import ComfyUIVideoGenerator
from app.config.settings import settings


class ComfyUIVideoGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.generator = ComfyUIVideoGenerator()

    def test_build_workflow_sets_prompt_and_low_memory_video_parameters(self):
        workflow = self.generator._build_workflow(
            scene_info={
                "action_description": "A rabbit hops over a log",
                "location": "a sunny forest",
                "characters_present": ["milo"],
            },
            episode_id="episode-1",
            scene_number=2,
            visual_style="storybook cartoon",
            characters=[
                {
                    "name": "Milo",
                    "visual_description": "a small orange rabbit with a blue backpack",
                }
            ],
            duration_seconds=3.5,
        )

        self.assertIn("A rabbit hops over a log", workflow["3"]["inputs"]["text"])
        self.assertIn("Milo", workflow["3"]["inputs"]["text"])
        self.assertEqual(workflow["5"]["inputs"]["width"], settings.COMFYUI_WIDTH)
        self.assertEqual(workflow["5"]["inputs"]["height"], settings.COMFYUI_HEIGHT)
        self.assertEqual(workflow["5"]["inputs"]["length"], 49)
        self.assertEqual(workflow["6"]["inputs"]["frame_rate"], 12)
        self.assertEqual(workflow["11"]["inputs"]["fps"], 12)
        self.assertEqual(workflow["8"]["inputs"]["sampler_name"], "euler_ancestral")
        self.assertEqual(workflow["12"]["inputs"]["format"], "mp4")
        self.assertEqual(workflow["12"]["inputs"]["format.codec"], "h264")
        self.assertTrue(0 <= workflow["9"]["inputs"]["noise_seed"] <= 0xFFFFFFFF)

    def test_generate_scene_video_submits_workflow_and_saves_video(self):
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            client = MagicMock()
            client_context = MagicMock()
            client_context.__enter__.return_value = client
            client.post.return_value.json.return_value = {"prompt_id": "job-1"}
            client.get.return_value.json.return_value = {
                "job-1": {
                    "outputs": {
                        "12": {
                            "images": [
                                {
                                    "filename": "generated.mp4",
                                    "subfolder": "",
                                    "type": "output",
                                }
                            ]
                        }
                    }
                }
            }
            download = client.stream.return_value.__enter__.return_value
            download.iter_bytes.return_value = iter([b"x" * 2048])

            with (
                patch.object(settings, "SCENES_DIR", output_dir),
                patch("app.ai.comfyui_video_generator.httpx.Client", return_value=client_context),
                patch("app.ai.comfyui_video_generator.time.sleep"),
            ):
                result = self.generator.generate_scene_video(
                    scene_info={"action_description": "A rabbit hops over a log"},
                    episode_id="episode-1",
                    scene_number=1,
                    visual_style="storybook cartoon",
                    characters=[],
                    duration_seconds=3,
                )
                result_size = result.stat().st_size

        self.assertEqual(result, output_dir / "episode-1" / "scene_01.mp4")
        self.assertEqual(result_size, 2048)
        client.post.assert_called_once()
        submitted_workflow = client.post.call_args.kwargs["json"]["prompt"]
        self.assertEqual(submitted_workflow["12"]["class_type"], "SaveVideo")
        self.assertEqual(submitted_workflow["5"]["inputs"]["length"], 41)
        client.stream.assert_called_once()

    def test_wait_for_video_supports_legacy_video_output_field(self):
        client = MagicMock()
        client.get.return_value.json.return_value = {
            "job-1": {
                "outputs": {
                    "12": {
                        "videos": [
                            {
                                "filename": "generated.mp4",
                                "subfolder": "",
                                "type": "output",
                            }
                        ]
                    }
                }
            }
        }

        result = self.generator._wait_for_video(
            client,
            "http://127.0.0.1:8188/",
            "job-1",
        )

        self.assertEqual(result["filename"], "generated.mp4")


if __name__ == "__main__":
    unittest.main()
