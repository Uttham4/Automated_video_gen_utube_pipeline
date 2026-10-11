import json
import logging
from pathlib import Path
from app.database.models import VideoStatus
from app.database.repository import repo
from app.youtube.uploader import youtube_uploader

logger = logging.getLogger(__name__)

class PublishPipeline:
    def publish_video(self, episode_id: str, retry_failed: bool = False) -> bool:
        logger.info(f"Publishing episode {episode_id} to YouTube...")
        video_rec = repo.get_by_episode_id(episode_id)

        if not video_rec:
            logger.error(f"Episode {episode_id} not found in database.")
            return False

        allowed_statuses = [VideoStatus.WAITING_APPROVAL]
        if retry_failed:
            allowed_statuses.append(VideoStatus.FAILED)
        if not repo.transition_status(
            episode_id,
            expected_statuses=allowed_statuses,
            status=VideoStatus.APPROVED,
        ):
            logger.warning(
                "Episode %s is not awaiting approval or an explicitly requested retry",
                episode_id,
            )
            return False
        repo.update_status(episode_id, status=VideoStatus.UPLOADING)

        try:
            # Load story JSON metadata
            story_path = video_rec.story_json_path
            story_data = {}
            if story_path and Path(story_path).exists():
                with open(story_path, "r", encoding="utf-8") as f:
                    story_data = json.load(f)

            yt_meta = story_data.get("youtube", {})
            title = yt_meta.get("title") or video_rec.title
            description = yt_meta.get("description") or f"Kids animated episode: {title}"
            tags = yt_meta.get("tags") or ["kids story", "animated cartoon"]

            video_path = Path(video_rec.video_path)
            thumb_path = Path(video_rec.thumbnail_path) if video_rec.thumbnail_path else None

            # Upload to YouTube
            yt_id = youtube_uploader.upload_video(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                thumbnail_path=thumb_path
            )

            repo.update_status(episode_id, status=VideoStatus.PUBLISHED, youtube_id=yt_id)
            logger.info(f"Episode {episode_id} PUBLISHED to YouTube! Video ID: {yt_id}")
            return True

        except Exception as e:
            logger.error(f"Publishing failed for {episode_id}: {e}")
            repo.update_status(episode_id, status=VideoStatus.FAILED, error_message=str(e))
            return False

publish_pipeline = PublishPipeline()
