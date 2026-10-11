import copy
import hashlib
import json
import logging
import math
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)


class ComfyUIVideoGenerator:
    def generate_scene_video(
        self,
        scene_info: Dict[str, Any],
        episode_id: str,
        scene_number: int,
        visual_style: str,
        characters: List[Dict[str, Any]],
        duration_seconds: float,
    ) -> Path:
        workflow = self._build_workflow(
            scene_info,
            episode_id,
            scene_number,
            visual_style,
            characters,
            duration_seconds,
        )
        output_dir = settings.SCENES_DIR / episode_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"scene_{scene_number:02d}.mp4"
        partial_path = output_path.with_suffix(".mp4.part")
        base_url = settings.COMFYUI_API_URL.rstrip("/") + "/"
        timeout = httpx.Timeout(settings.COMFYUI_TIMEOUT_SECONDS, connect=10.0)

        try:
            with httpx.Client(timeout=timeout) as client:
                prompt_response = client.post(
                    urljoin(base_url, "prompt"),
                    json={"prompt": workflow},
                )
                prompt_response.raise_for_status()
                prompt_result = prompt_response.json()
                if prompt_result.get("error") or prompt_result.get("node_errors"):
                    raise RuntimeError(
                        f"ComfyUI rejected the LTX workflow: "
                        f"{prompt_result.get('error') or prompt_result.get('node_errors')}"
                    )

                prompt_id = prompt_result.get("prompt_id")
                if not prompt_id:
                    raise RuntimeError("ComfyUI did not return a prompt_id")

                video_metadata = self._wait_for_video(
                    client,
                    base_url,
                    str(prompt_id),
                )
                with client.stream(
                    "GET",
                    urljoin(base_url, "view"),
                    params={
                        "filename": video_metadata["filename"],
                        "subfolder": video_metadata.get("subfolder", ""),
                        "type": video_metadata.get("type", "output"),
                    },
                ) as response:
                    response.raise_for_status()
                    with partial_path.open("wb") as output_file:
                        for chunk in response.iter_bytes():
                            output_file.write(chunk)

            if partial_path.stat().st_size < 1024:
                raise RuntimeError("ComfyUI returned an unexpectedly small video file")
            partial_path.replace(output_path)
            logger.info("Generated LTX scene clip with ComfyUI -> %s", output_path)
            return output_path
        except httpx.HTTPError as exc:
            if partial_path.exists():
                partial_path.unlink()
            raise RuntimeError(
                f"ComfyUI request failed at {settings.COMFYUI_API_URL}: {exc}"
            ) from exc
        except Exception:
            if partial_path.exists():
                partial_path.unlink()
            raise

    def _build_workflow(
        self,
        scene_info: Dict[str, Any],
        episode_id: str,
        scene_number: int,
        visual_style: str,
        characters: List[Dict[str, Any]],
        duration_seconds: float,
    ) -> Dict[str, Any]:
        width = settings.COMFYUI_WIDTH
        height = settings.COMFYUI_HEIGHT
        fps = settings.COMFYUI_FPS
        max_frames = settings.COMFYUI_MAX_FRAMES
        if width < 256 or width % 32:
            raise ValueError("COMFYUI_WIDTH must be at least 256 and divisible by 32")
        if height < 256 or height % 32:
            raise ValueError("COMFYUI_HEIGHT must be at least 256 and divisible by 32")
        if fps < 1:
            raise ValueError("COMFYUI_FPS must be at least 1")
        if max_frames < 17 or (max_frames - 1) % 8:
            raise ValueError("COMFYUI_MAX_FRAMES must be at least 17 and equal to 8n + 1")

        workflow_path = Path(settings.COMFYUI_WORKFLOW_PATH)
        with workflow_path.open("r", encoding="utf-8") as workflow_file:
            workflow = copy.deepcopy(json.load(workflow_file))

        prompt = self._build_prompt(scene_info, visual_style, characters)
        requested_frames = max(17, math.ceil(max(0.1, duration_seconds) * fps))
        frame_count = min(
            max_frames,
            ((requested_frames - 1 + 7) // 8) * 8 + 1,
        )
        seed_material = f"{episode_id}:{scene_number}".encode("utf-8")
        seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:4], "big")

        workflow["3"]["inputs"]["text"] = prompt
        workflow["5"]["inputs"].update(
            {"width": width, "height": height, "length": frame_count}
        )
        workflow["6"]["inputs"]["frame_rate"] = fps
        workflow["7"]["inputs"]["latent"] = ["5", 0]
        workflow["9"]["inputs"]["noise_seed"] = seed
        workflow["11"]["inputs"]["fps"] = fps
        workflow["12"]["inputs"]["filename_prefix"] = (
            f"animated_videos/{episode_id}_scene_{scene_number:02d}"
        )
        return workflow

    def _wait_for_video(
        self,
        client: httpx.Client,
        base_url: str,
        prompt_id: str,
    ) -> Dict[str, Any]:
        deadline = time.monotonic() + settings.COMFYUI_TIMEOUT_SECONDS
        history_url = urljoin(base_url, f"history/{prompt_id}")

        while time.monotonic() < deadline:
            response = client.get(history_url)
            response.raise_for_status()
            history = response.json().get(prompt_id, {})
            status = history.get("status", {})
            if status.get("status_str") in {"error", "failed"}:
                raise RuntimeError(
                    f"ComfyUI failed to generate the LTX scene: "
                    f"{status.get('messages', status)}"
                )

            output = history.get("outputs", {}).get("12", {})
            video_files = output.get("videos", []) or output.get("images", [])
            if video_files:
                return video_files[0]

            time.sleep(min(2, max(0, deadline - time.monotonic())))

        raise TimeoutError(
            f"ComfyUI did not finish LTX scene generation within "
            f"{settings.COMFYUI_TIMEOUT_SECONDS:g} seconds"
        )

    def _build_prompt(
        self,
        scene_info: Dict[str, Any],
        visual_style: str,
        characters: List[Dict[str, Any]],
    ) -> str:
        present_names = {
            str(name).lower() for name in scene_info.get("characters_present", [])
        }
        character_details = [
            f"{character.get('name')}: {character.get('visual_description')}"
            for character in characters
            if str(character.get("name", "")).lower() in present_names
            and character.get("visual_description")
        ]
        action = scene_info.get("action_description") or scene_info.get("image_prompt", "")
        location = scene_info.get("location", "")
        parts = [
            f"A polished {visual_style} animation for a gentle children's story.",
            f"One continuous shot: {action}. Setting: {location}.",
        ]
        if character_details:
            parts.append(
                "Keep these character designs consistent: "
                + "; ".join(character_details)
                + "."
            )
        parts.append(
            "Show clear, gentle body movement and natural secondary motion. "
            "Keep the camera steady, use clean detailed backgrounds, and include "
            "no text, captions, logos, or scene cuts."
        )
        return " ".join(parts)


comfyui_video_generator = ComfyUIVideoGenerator()
