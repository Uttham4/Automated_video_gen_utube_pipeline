import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from app.config.settings import settings

logger = logging.getLogger(__name__)

class ThumbnailGenerator:
    """
    Renders striking 1280x720 YouTube thumbnails optimized for kids clicks:
    - High-contrast background scene image
    - Bold colorful text badge
    - Bright border frame
    """
    def generate_thumbnail(
        self,
        scene_image_path: Path,
        title: str,
        episode_id: str
    ) -> Path:
        output_dir = settings.THUMBNAILS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{episode_id}_thumbnail.png"

        logger.info(f"Generating YouTube thumbnail for '{title}' -> {output_path}")

        if scene_image_path.exists():
            bg = Image.open(scene_image_path).convert("RGB")
            bg = bg.resize((1280, 720), Image.Resampling.LANCZOS)
        else:
            bg = Image.new("RGB", (1280, 720), color=(255, 165, 0))

        # Add slight saturation/brightness contrast
        draw = ImageDraw.Draw(bg)

        # Draw framing border
        draw.rectangle([0, 0, 1279, 719], outline=(255, 215, 0), width=12)

        # Add text background banner (Left top corner badge)
        banner_x1, banner_y1 = 60, 60
        banner_x2, banner_y2 = 1200, 220

        # Semi-transparent dark blue badge with gold border
        overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle([banner_x1, banner_y1, banner_x2, banner_y2], radius=20, fill=(25, 25, 112, 220), outline=(255, 223, 0), width=6)

        bg = Image.alpha_composite(bg.convert("RGBA"), overlay)
        draw_final = ImageDraw.Draw(bg)

        # Render Title text with shadow
        words = title.upper().split()
        line1 = " ".join(words[:4]) if len(words) >= 4 else title.upper()
        line2 = " ".join(words[4:]) if len(words) >= 4 else ""

        # Use larger font size or load default Truetype font
        try:
            font = ImageFont.truetype("arial.ttf", 52)
        except Exception:
            font = ImageFont.load_default()

        # Draw line 1
        x, y = 90, 80
        for dx in [-4, 0, 4]:
            for dy in [-4, 0, 4]:
                draw_final.text((x + dx, y + dy), line1, fill=(0, 0, 0), font=font)
        draw_final.text((x, y), line1, fill=(255, 235, 59), font=font)

        # Draw line 2 if present
        if line2:
            y += 65
            for dx in [-4, 0, 4]:
                for dy in [-4, 0, 4]:
                    draw_final.text((x + dx, y + dy), line2, fill=(0, 0, 0), font=font)
            draw_final.text((x, y), line2, fill=(255, 255, 255), font=font)

        bg_rgb = bg.convert("RGB")
        bg_rgb.save(output_path, "PNG")
        logger.info(f"Thumbnail created successfully: {output_path}")
        return output_path

thumbnail_generator = ThumbnailGenerator()
