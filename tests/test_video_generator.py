import unittest
from pathlib import Path
from unittest.mock import patch

from app.ai.video_generator import PixazoVideoGenerator, scene_video_generator
from app.config.settings import settings


class VideoGeneratorProviderTests(unittest.TestCase):
    def test_local_provider_does_not_call_pixazo(self):
        generator = PixazoVideoGenerator()
        with patch.object(settings, "VIDEO_GENERATION_PROVIDER", "local"), patch(
            "app.ai.video_generator.httpx.Client"
        ) as http_client:
            result = generator.generate_scene_video(
                scene_info={"action_description": "A rabbit finds a star"},
                episode_id="test-episode",
                scene_number=1,
                visual_style="storybook illustration",
                characters=[],
                duration_seconds=5,
            )

        self.assertIsNone(result)
        http_client.assert_not_called()

    def test_comfyui_provider_routes_to_comfyui_generator(self):
        expected_path = Path("scene.mp4")
        with patch.object(settings, "VIDEO_GENERATION_PROVIDER", "comfyui"), patch(
            "app.ai.video_generator.comfyui_video_generator.generate_scene_video",
            return_value=expected_path,
        ) as generate_scene_video:
            result = scene_video_generator.generate_scene_video(
                scene_info={"action_description": "A rabbit finds a star"},
                episode_id="test-episode",
                scene_number=1,
                visual_style="storybook illustration",
                characters=[],
                duration_seconds=5,
            )

        self.assertEqual(result, expected_path)
        generate_scene_video.assert_called_once()


if __name__ == "__main__":
    unittest.main()
