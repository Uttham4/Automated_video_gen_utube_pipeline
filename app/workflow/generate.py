import logging
import traceback
import cv2
from typing import Dict, Any
from app.config.settings import settings
from app.database.models import VideoStatus
from app.database.repository import repo
from app.ai.story_generator import story_generator
from app.ai.safety_checker import safety_checker
from app.ai.image_generator import image_generator
from app.audio.narrator import narrator
from app.video.subtitles import subtitle_renderer
from app.video.thumbnail import thumbnail_generator
from app.video.renderer import video_renderer
from app.email.gmail import gmail_notifier

logger = logging.getLogger(__name__)

class GeneratePipeline:
    def run_generation_workflow(self, topic: str, episode_id: str) -> Dict[str, Any]:
        logger.info(f"=== STARTING AUTOMATED GENERATION PIPELINE FOR '{topic}' ({episode_id}) ===")

        # 1. DB Entry
        video_rec = repo.create_video(episode_id=episode_id, topic=topic)

        try:
            # 2. Story Generation
            story_json = story_generator.generate_story(topic=topic, episode_id=episode_id)
            title = story_json.get("title", f"Story: {topic}")
            story_path = str(settings.STORIES_DIR / f"{episode_id}.json")
            repo.update_status(episode_id, status=VideoStatus.STORY_GENERATED, story_json_path=story_path)

            # 3. Content Safety Check
            is_safe, reasons = safety_checker.check_story_safety(story_json)
            if not is_safe:
                err_msg = f"Safety check failed: {', '.join(reasons)}"
                repo.update_status(episode_id, status=VideoStatus.FAILED, error_message=err_msg)
                raise ValueError(err_msg)
            repo.update_status(episode_id, status=VideoStatus.SAFETY_CHECKED)

            # 4. Generate Scene Images
            scenes = story_json.get("scenes", [])
            style = story_json.get("visual_style", "Vibrant 2D cartoon")
            scenes_dir = settings.SCENES_DIR / episode_id

            if settings.VIDEO_GENERATION_PROVIDER == "comfyui":
                logger.info("Skipping still images; ComfyUI will generate moving scene clips.")
            else:
                for scene in scenes:
                    idx = scene.get("scene_number", 1)
                    image_generator.generate_scene_image(
                        scene,
                        episode_id,
                        idx,
                        visual_style=style,
                    )

            repo.update_status(episode_id, status=VideoStatus.SCENES_GENERATED)

            # 5. Generate Audio Narration
            scenes_audio = narrator.generate_episode_narration(story_json, episode_id)
            
            # Generate SRT Subtitle file
            srt_path = settings.DATA_DIR / "renders" / f"{episode_id}.srt"
            subtitle_renderer.generate_srt(scenes_audio, srt_path)

            first_audio = scenes_audio[0]["audio_path"] if scenes_audio else None
            repo.update_status(episode_id, status=VideoStatus.AUDIO_GENERATED, narration_path=first_audio)

            # 6. Render Video Composite MP4
            final_mp4 = video_renderer.render_episode(story_json, scenes_audio, episode_id)

            # Use an actual generated LTX frame for the thumbnail when available.
            first_scene_img = scenes_dir / "scene_01.png"
            if settings.VIDEO_GENERATION_PROVIDER == "comfyui":
                first_scene_video = scenes_dir / "scene_01.mp4"
                first_scene_img = scenes_dir / "scene_01_thumbnail_frame.png"
                capture = cv2.VideoCapture(str(first_scene_video))
                try:
                    success, frame = capture.read()
                finally:
                    capture.release()
                if not success or not cv2.imwrite(str(first_scene_img), frame):
                    raise RuntimeError(
                        f"Could not extract a thumbnail frame from {first_scene_video}"
                    )
            thumb_path = thumbnail_generator.generate_thumbnail(first_scene_img, title, episode_id)
            
            repo.update_status(
                episode_id,
                status=VideoStatus.WAITING_APPROVAL,
                video_path=str(final_mp4),
                thumbnail_path=str(thumb_path)
            )

            # 8. Send Email Approval Notification
            preview_url = f"{settings.APP_URL}"
            gmail_notifier.send_approval_email(title, episode_id, preview_url)

            logger.info(f"=== WORKFLOW COMPLETED SUCCESSFULLY! EPISODE WAITING FOR APPROVAL: {episode_id} ===")
            return {"status": "success", "episode_id": episode_id, "video_path": str(final_mp4)}

        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Pipeline execution failed for {episode_id}: {error_details}")
            repo.update_status(episode_id, status=VideoStatus.FAILED, error_message=str(e))
            return {"status": "failed", "error": str(e)}

generate_pipeline = GeneratePipeline()
