import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.database.models import VideoStatus
from app.workflow.publish import PublishPipeline


class PublishPipelineTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = PublishPipeline()
        self.record = SimpleNamespace(
            episode_id="episode-123",
            title="Test Story",
            story_json_path=None,
            video_path=Path("video.mp4"),
            thumbnail_path=None,
        )

    def test_rejects_publish_when_status_transition_fails(self):
        with (
            patch("app.workflow.publish.repo.get_by_episode_id", return_value=self.record),
            patch(
                "app.workflow.publish.repo.transition_status",
                return_value=False,
            ) as transition,
            patch("app.workflow.publish.youtube_uploader.upload_video") as upload,
        ):
            result = self.pipeline.publish_video("episode-123")

        self.assertFalse(result)
        transition.assert_called_once_with(
            "episode-123",
            expected_statuses=[VideoStatus.WAITING_APPROVAL],
            status=VideoStatus.APPROVED,
        )
        upload.assert_not_called()

    def test_failed_episode_requires_explicit_retry_flag(self):
        with (
            patch("app.workflow.publish.repo.get_by_episode_id", return_value=self.record),
            patch(
                "app.workflow.publish.repo.transition_status",
                return_value=False,
            ) as transition,
            patch("app.workflow.publish.youtube_uploader.upload_video") as upload,
        ):
            result = self.pipeline.publish_video("episode-123", retry_failed=True)

        self.assertFalse(result)
        transition.assert_called_once_with(
            "episode-123",
            expected_statuses=[VideoStatus.WAITING_APPROVAL, VideoStatus.FAILED],
            status=VideoStatus.APPROVED,
        )
        upload.assert_not_called()

    def test_successful_upload_uses_real_youtube_id(self):
        with (
            patch("app.workflow.publish.repo.get_by_episode_id", return_value=self.record),
            patch(
                "app.workflow.publish.repo.transition_status",
                return_value=True,
            ),
            patch("app.workflow.publish.repo.update_status") as update_status,
            patch(
                "app.workflow.publish.youtube_uploader.upload_video",
                return_value="youtube-video-id",
            ),
        ):
            result = self.pipeline.publish_video("episode-123")

        self.assertTrue(result)
        update_status.assert_any_call("episode-123", status=VideoStatus.UPLOADING)
        update_status.assert_any_call(
            "episode-123",
            status=VideoStatus.PUBLISHED,
            youtube_id="youtube-video-id",
        )


if __name__ == "__main__":
    unittest.main()
