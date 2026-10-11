import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple
from pathlib import Path

class SubtitleRenderer:
    """
    Overlay high-visibility stylized subtitles for children's reading engagement.
    """
    def overlay_subtitle(
        self,
        frame_bgr: np.ndarray,
        text: str,
        font_size: int = 34
    ) -> np.ndarray:
        if not text:
            return frame_bgr

        # Convert BGR (OpenCV) to RGB (Pillow)
        img_pil = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        w, h = img_pil.size

        # Simple text wrapping
        max_chars = 40
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars:
                current_line = f"{current_line} {word}".strip()
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        # Draw semi-transparent black banner at bottom
        banner_h = (len(lines) * 45) + 30
        banner_y1 = h - banner_h - 30
        banner_y2 = h - 30

        # Create overlay rectangle for subtitle text
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Banner with rounded look
        overlay_draw.rectangle([60, banner_y1, w - 60, banner_y2], fill=(0, 0, 0, 180))

        # Composite overlay
        img_pil = Image.alpha_composite(img_pil.convert("RGBA"), overlay)
        draw_final = ImageDraw.Draw(img_pil)

        # Render lines with stroke/outline
        y_text = banner_y1 + 15
        for line in lines:
            # Draw text yellow/white with stroke
            bbox = draw_final.textbbox((0, 0), line)
            line_w = bbox[2] - bbox[0]
            x_text = (w - line_w) // 2

            # Stroke shadow
            for dx in [-2, 0, 2]:
                for dy in [-2, 0, 2]:
                    draw_final.text((x_text + dx, y_text + dy), line, fill=(0, 0, 0))

            # Main text (yellow for kid high visibility)
            draw_final.text((x_text, y_text), line, fill=(255, 235, 59))
            y_text += 42

        # Convert back to BGR numpy array
        return cv2.cvtColor(np.array(img_pil.convert("RGB")), cv2.COLOR_RGB2BGR)

    def generate_srt(self, scenes_audio: List[dict], output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        current_time = 0.0

        with open(output_path, "w", encoding="utf-8") as f:
            for idx, item in enumerate(scenes_audio, start=1):
                start_sec = current_time
                end_sec = current_time + item["duration"]
                current_time = end_sec

                start_str = self._format_timestamp(start_sec)
                end_str = self._format_timestamp(end_sec)
                text = item["narration_text"]

                f.write(f"{idx}\n{start_str} --> {end_str}\n{text}\n\n")

    def _format_timestamp(self, seconds: float) -> str:
        millis = int((seconds % 1) * 1000)
        secs = int(seconds) % 60
        mins = int(seconds // 60) % 60
        hrs = int(seconds // 3600)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

subtitle_renderer = SubtitleRenderer()
