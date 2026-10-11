import logging
from pathlib import Path
from typing import Optional
from googleapiclient.http import MediaFileUpload
from app.config.settings import settings
from app.youtube.auth import youtube_auth

logger = logging.getLogger(__name__)

class YouTubeUploader:
    def __init__(self, auth=None):
        self.auth = auth or youtube_auth

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list,
        thumbnail_path: Optional[Path] = None,
        privacy_status: Optional[str] = None
    ) -> str:
        privacy = privacy_status or settings.YOUTUBE_PRIVACY_STATUS
        logger.info(f"Preparing YouTube upload for: '{title}' ({video_path}) - Privacy: {privacy}")

        service = self.auth.get_authenticated_service()

        if not service:
            raise RuntimeError(
                "YouTube upload requires OAuth authorization. Configure "
                "credentials/google_client_secret.json for a Desktop OAuth client "
                "and authorize the channel; an API key cannot upload videos."
            )

        body = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags,
                "categoryId": settings.YOUTUBE_CATEGORY_ID
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": True
            }
        }

        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")

        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Uploaded {int(status.progress() * 100)}%")

        video_id = response.get("id")
        logger.info(f"Video uploaded successfully! YouTube Video ID: {video_id}")

        # Set custom thumbnail if provided
        if thumbnail_path and thumbnail_path.exists() and video_id:
            try:
                service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(str(thumbnail_path))
                ).execute()
                logger.info("Custom thumbnail uploaded successfully!")
            except Exception as e:
                logger.warning(f"Could not upload custom thumbnail: {e}")

        return video_id

youtube_uploader = YouTubeUploader()
