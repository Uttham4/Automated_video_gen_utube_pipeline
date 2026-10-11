import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config.settings import settings
from app.database.models import VideoStatus
from app.web.server import app, csrf_token


class WebSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("127.0.0.1", 54321),
        )
        self.form_headers = {
            "Origin": "http://127.0.0.1",
            "X-CSRF-Token": csrf_token,
        }

    def test_media_endpoint_rejects_files_outside_media_roots(self):
        response = self.client.get("/api/media", params={"path": str(settings.BASE_DIR / ".env")})

        self.assertEqual(response.status_code, 404)

    def test_media_endpoint_serves_generated_media(self):
        settings.SCENES_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=settings.SCENES_DIR,
            suffix=".mp4",
            delete=False,
        ) as media_file:
            media_file.write(b"test media")
            media_path = Path(media_file.name)

        try:
            response = self.client.get("/api/media", params={"path": str(media_path)})
        finally:
            media_path.unlink(missing_ok=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"test media")

    def test_non_loopback_clients_are_rejected(self):
        remote_client = TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("192.0.2.25", 54321),
        )

        response = remote_client.get("/api/videos")

        self.assertEqual(response.status_code, 403)

    def test_dashboard_escapes_untrusted_titles_in_preview_controls(self):
        record = SimpleNamespace(
            title="' onmouseover='alert(1)",
            status=VideoStatus.WAITING_APPROVAL,
            thumbnail_path=None,
            topic="test",
            episode_id="episode-123",
            error_message=None,
            video_path=str(settings.RENDERS_DIR / "episode.mp4"),
            youtube_id=None,
        )
        with patch("app.web.server.repo.list_all", return_value=[record]):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("data-video-title=\"' onmouseover=", response.text)
        self.assertIn("data-video-title=\"&#39; onmouseover=&#39;alert(1)\"", response.text)

    def test_approval_requires_valid_csrf_token(self):
        with patch("app.web.server.repo.get_by_episode_id") as get_video:
            response = self.client.post("/api/approve/episode-123")

        self.assertEqual(response.status_code, 403)
        get_video.assert_not_called()

    def test_approval_rejects_episodes_not_waiting_for_approval(self):
        video = SimpleNamespace(status=VideoStatus.FAILED)
        with patch("app.web.server.repo.get_by_episode_id", return_value=video):
            response = self.client.post(
                "/api/approve/episode-123",
                headers=self.form_headers,
            )

        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
