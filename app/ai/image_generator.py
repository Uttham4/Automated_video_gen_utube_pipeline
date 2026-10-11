import os
import logging
import urllib.parse
import httpx
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.config.settings import settings
from app.ai.nvidia_client import nvidia_client

logger = logging.getLogger(__name__)

class ImageGenerator:
    def __init__(self, client=None):
        self.client = client or nvidia_client

    def generate_scene_image(
        self,
        scene_info: Dict[str, Any],
        episode_id: str,
        scene_number: int,
        visual_style: str = "Vibrant 2D cartoon"
    ) -> Path:
        output_dir = settings.SCENES_DIR / episode_id
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"scene_{scene_number:02d}.png"

        prompt = scene_info.get("image_prompt") or f"{scene_info.get('location', '')}, {scene_info.get('action_description', '')}, {visual_style}"
        logger.info(f"Generating image for scene {scene_number} ({episode_id})... Prompt: {prompt[:80]}")

        # 1. Try Pollinations Free Endpoint (Immediate high-quality SD/FLUX AI image generator without API key needed!)
        if self._try_pollinations_generation(prompt, file_path):
            return file_path

        # 2. Fallback: Local Pillow Stylized Cartoon Canvas Generator
        self._generate_local_fallback_image(scene_info, prompt, file_path, scene_number)
        return file_path

    def _try_pollinations_generation(self, prompt: str, file_path: Path) -> bool:
        encoded_prompt = urllib.parse.quote(f"{prompt}, high quality 2D cartoon illustration, vibrant colors, storybook style")
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true&seed=42"
        
        try:
            with httpx.Client(timeout=25.0) as client:
                resp = client.get(url)
                if resp.status_code == 200 and len(resp.content) > 5000:
                    with open(file_path, "wb") as f:
                        f.write(resp.content)
                    logger.info(f"Successfully fetched AI image from Pollinations endpoint -> {file_path}")
                    return True
        except Exception as e:
            logger.warning(f"Pollinations AI image generation call timed out or failed: {e}")
        return False

    def _generate_local_fallback_image(self, scene_info: Dict[str, Any], prompt: str, file_path: Path, scene_number: int):
        logger.info(f"Rendering local cartoon scene canvas for scene {scene_number} -> {file_path}")
        width, height = 1280, 720
        img = Image.new("RGB", (width, height), color=(135, 206, 235)) # Sky blue background
        draw = ImageDraw.Draw(img)

        # Draw vibrant landscape background (hills, sun, clouds)
        # Sun
        draw.ellipse([1000, 60, 1150, 210], fill=(255, 223, 0), outline=(255, 180, 0), width=4)
        
        # Soft clouds
        draw.ellipse([200, 100, 380, 170], fill=(255, 255, 255))
        draw.ellipse([260, 80, 420, 160], fill=(255, 255, 255))
        draw.ellipse([600, 120, 780, 190], fill=(255, 255, 255))

        # Green rolling hills
        draw.chord([-200, 400, 1000, 1100], start=180, end=0, fill=(124, 252, 0)) # Foreground hill
        draw.chord([400, 350, 1600, 1100], start=180, end=0, fill=(50, 205, 50))   # Back hill

        # Character placeholder / graphic element
        # Milo the Orange Rabbit
        rabbit_box = [540, 360, 740, 580]
        # Body
        draw.ellipse([570, 420, 710, 580], fill=(255, 140, 0), outline=(230, 100, 0), width=3) # Orange body
        # Head
        draw.ellipse([580, 340, 700, 450], fill=(255, 140, 0), outline=(230, 100, 0), width=3)
        # Ears
        draw.ellipse([590, 240, 630, 360], fill=(255, 140, 0), outline=(230, 100, 0), width=3)
        draw.ellipse([650, 240, 690, 360], fill=(255, 140, 0), outline=(230, 100, 0), width=3)
        # Eyes
        draw.ellipse([605, 375, 625, 405], fill=(30, 144, 255)) # Big blue eyes
        draw.ellipse([655, 375, 675, 405], fill=(30, 144, 255))
        # Nose & smile
        draw.polygon([(635, 410), (645, 410), (640, 418)], fill=(255, 105, 180))

        # Location title banner
        location = scene_info.get("location", f"Scene {scene_number}")
        draw.rectangle([50, 50, 650, 110], fill=(0, 0, 0, 160))
        draw.text((70, 65), f"Scene {scene_number}: {location}", fill=(255, 255, 255))

        img.save(file_path, "PNG")

image_generator = ImageGenerator()
