import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.config.settings import settings
from app.ai.comfyui_video_generator import comfyui_video_generator

logger = logging.getLogger(__name__)


class PixazoVideoGenerator:
    def generate_scene_video(
        self,
        scene_info: Dict[str, Any],
        episode_id: str,
        scene_number: int,
        visual_style: str,
        characters: List[Dict[str, Any]],
        duration_seconds: float,
    ) -> Optional[Path]:
        if settings.VIDEO_GENERATION_PROVIDER != "pixazo":
            return None
        if not settings.PIXAZO_API_KEY:
            logger.warning("Pixazo video generation is enabled but PIXAZO_API_KEY is not set")
            return None

        output_dir = settings.SCENES_DIR / episode_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"scene_{scene_number:02d}.mp4"
        partial_path = output_path.with_suffix(".mp4.part")

        prompt = self._build_prompt(scene_info, visual_style, characters)
        clip_duration = min(5, max(2, round(duration_seconds)))
        payload = {
            "prompt": prompt,
            "duration": clip_duration,
            "aspect_ratio": "16:9",
            "resolution": settings.PIXAZO_VIDEO_RESOLUTION,
            "style": visual_style,
        }
        headers = {"Authorization": f"Bearer {settings.PIXAZO_API_KEY}"}

        try:
            with httpx.Client(timeout=httpx.Timeout(120.0, connect=20.0)) as client:
                response = client.post(settings.PIXAZO_VIDEO_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                job = response.json()

                output_url = self._get_output_url(client, job, headers)
                parsed_output_url = urlparse(output_url)
                if parsed_output_url.scheme != "https" or not parsed_output_url.netloc:
                    raise ValueError("Pixazo returned an invalid video URL")

                with client.stream("GET", output_url) as download:
                    download.raise_for_status()
                    with partial_path.open("wb") as output_file:
                        for chunk in download.iter_bytes():
                            output_file.write(chunk)

            if partial_path.stat().st_size < 1024:
                raise ValueError("Pixazo returned an unexpectedly small video file")
            partial_path.replace(output_path)
            logger.info("Generated Pixazo scene clip -> %s", output_path)
            return output_path
        except Exception as exc:
            logger.warning("Pixazo scene generation failed for scene %s: %s", scene_number, exc)
            if partial_path.exists():
                partial_path.unlink()
            return None

    def _get_output_url(
        self,
        client: httpx.Client,
        job: Dict[str, Any],
        headers: Dict[str, str],
    ) -> str:
        status = str(job.get("status", "")).lower()
        deadline = time.monotonic() + 600

        while status not in {"completed", "complete", "done", "succeeded"}:
            if status in {"failed", "error", "cancelled"}:
                raise RuntimeError(job.get("error") or "Pixazo video generation failed")

            poll_url = job.get("poll_url")
            if not poll_url:
                raise ValueError("Pixazo response did not include a poll_url")

            api_host = urlparse(settings.PIXAZO_VIDEO_API_URL).hostname
            poll_location = urlparse(poll_url)
            if poll_location.scheme != "https" or poll_location.hostname != api_host:
                raise ValueError("Pixazo returned an unexpected polling URL")

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Timed out waiting for Pixazo video generation")
            time.sleep(min(5, remaining))

            response = client.get(poll_url, headers=headers)
            response.raise_for_status()
            job = response.json()
            status = str(job.get("status", "")).lower()

        output_url = job.get("output_url") or job.get("url")
        if not output_url:
            raise ValueError("Completed Pixazo job did not include an output URL")
        return str(output_url)

    def _build_prompt(
        self,
        scene_info: Dict[str, Any],
        visual_style: str,
        characters: List[Dict[str, Any]],
    ) -> str:
        present_names = {str(name).lower() for name in scene_info.get("characters_present", [])}
        character_details = [
            f"{character.get('name')}: {character.get('visual_description')}"
            for character in characters
            if str(character.get("name", "")).lower() in present_names
            and character.get("visual_description")
        ]
        cast_description = "; ".join(character_details)
        action = scene_info.get("action_description") or scene_info.get("image_prompt", "")
        location = scene_info.get("location", "")

        prompt_parts = [
            f"A {visual_style} animation for a gentle children's story.",
            f"Scene: {action}. Location: {location}.",
        ]
        if cast_description:
            prompt_parts.append(f"Character designs to preserve: {cast_description}.")
        prompt_parts.append(
            "Animate the described action with clear, gentle motion and a steady camera. "
            "Keep the same character colors, clothing, and proportions throughout the clip. "
            "No written words, captions, logos, or scene cuts."
        )
        return " ".join(prompt_parts)


pixazo_video_generator = PixazoVideoGenerator()


class SceneVideoGenerator:
    def generate_scene_video(
        self,
        scene_info: Dict[str, Any],
        episode_id: str,
        scene_number: int,
        visual_style: str,
        characters: List[Dict[str, Any]],
        duration_seconds: float,
    ) -> Optional[Path]:
        if settings.VIDEO_GENERATION_PROVIDER == "comfyui":
            return comfyui_video_generator.generate_scene_video(
                scene_info,
                episode_id,
                scene_number,
                visual_style,
                characters,
                duration_seconds,
            )
        return pixazo_video_generator.generate_scene_video(
            scene_info,
            episode_id,
            scene_number,
            visual_style,
            characters,
            duration_seconds,
        )


scene_video_generator = SceneVideoGenerator()