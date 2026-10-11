import unittest
from pathlib import Path
from unittest.mock import Mock

from app.youtube.uploader import YouTubeUploader


class YouTubeUploaderTests(unittest.TestCase):
    def test_missing_oauth_does_not_claim_a_simulated_upload(self):
        auth = Mock()
        auth.get_authenticated_service.return_value = None
        uploader = YouTubeUploader(auth=auth)

        with self.assertRaisesRegex(RuntimeError, "an API key cannot upload videos"):
            uploader.upload_video(
                video_path=Path("video.mp4"),
                title="Test story",
                description="A test",
                tags=["test"],
            )


if __name__ == "__main__":
    unittest.main()
