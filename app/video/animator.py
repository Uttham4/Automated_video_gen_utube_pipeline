import cv2
import numpy as np
from PIL import Image
from typing import Tuple, List

class SceneAnimator:
    """
    Applies smooth 2D camera motion (Ken Burns zoom in/out, pan left/right, subtle tilt)
    to static scene images for high-engagement cartoon storytelling.
    """
    def apply_motion(
        self,
        image_path: str,
        motion_type: str,
        fps: int,
        duration_seconds: float,
        target_size: Tuple[int, int] = (1280, 720)
    ) -> List[np.ndarray]:
        img = Image.open(image_path).convert("RGB")
        img_w, img_h = img.size
        out_w, out_h = target_size

        total_frames = int(fps * duration_seconds)
        frames = []

        # Convert to numpy array for cv2 resizing
        img_np = np.array(img)

        motion = motion_type.lower()

        for f in range(total_frames):
            progress = f / max(1, total_frames - 1) # 0.0 to 1.0

            if "zoom_in" in motion:
                scale = 1.0 + (0.15 * progress) # Zoom from 1.0 to 1.15x
                crop_w = int(img_w / scale)
                crop_h = int(img_h / scale)
                x1 = (img_w - crop_w) // 2
                y1 = (img_h - crop_h) // 2
            elif "zoom_out" in motion:
                scale = 1.15 - (0.15 * progress) # Zoom out from 1.15 to 1.0x
                crop_w = int(img_w / scale)
                crop_h = int(img_h / scale)
                x1 = (img_w - crop_w) // 2
                y1 = (img_h - crop_h) // 2
            elif "pan_right" in motion:
                scale = 1.10
                crop_w = int(img_w / scale)
                crop_h = int(img_h / scale)
                max_x = img_w - crop_w
                x1 = int(max_x * progress)
                y1 = (img_h - crop_h) // 2
            elif "pan_left" in motion:
                scale = 1.10
                crop_w = int(img_w / scale)
                crop_h = int(img_h / scale)
                max_x = img_w - crop_w
                x1 = int(max_x * (1.0 - progress))
                y1 = (img_h - crop_h) // 2
            else: # Default subtle zoom
                scale = 1.0 + (0.08 * progress)
                crop_w = int(img_w / scale)
                crop_h = int(img_h / scale)
                x1 = (img_w - crop_w) // 2
                y1 = (img_h - crop_h) // 2

            # Clamp coordinates
            x1 = max(0, min(img_w - crop_w, x1))
            y1 = max(0, min(img_h - crop_h, y1))
            cropped = img_np[y1:y1+crop_h, x1:x1+crop_w]

            # Resize to target resolution
            frame_resized = cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LINEAR)
            frames.append(frame_resized)

        return frames

scene_animator = SceneAnimator()
