import cv2
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from app.config.settings import settings
from app.ai.video_generator import scene_video_generator
from app.video.animator import scene_animator
from app.video.subtitles import subtitle_renderer
from app.audio.music import music_manager

logger = logging.getLogger(__name__)

class VideoRenderer:
    def render_episode(
        self,
        story_json: Dict[str, Any],
        scenes_audio: List[Dict[str, Any]],
        episode_id: str,
        fps: int = 24
    ) -> Path:
        output_dir = settings.RENDERS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_video_path = output_dir / f"{episode_id}_temp_raw.mp4"
        final_video_path = output_dir / f"{episode_id}_final.mp4"

        width, height = 1280, 720
        logger.info(f"Starting video composite render for episode: {episode_id}")

        # 1. OpenCV Video Writer for Visual Frames
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(str(raw_video_path), fourcc, fps, (width, height))

        scenes = story_json.get("scenes", [])
        scenes_dir = settings.SCENES_DIR / episode_id

        try:
            for idx, (scene, audio_info) in enumerate(zip(scenes, scenes_audio), start=1):
                scene_img_path = scenes_dir / f"scene_{idx:02d}.png"
                motion_type = scene.get("camera_motion", "slow_zoom_in")
                duration = audio_info.get("duration", 5.0)
                narration_text = audio_info.get("narration_text", "")

                logger.info(
                    f"Rendering frames for Scene {idx} "
                    f"(duration: {duration:.2f}s, motion: {motion_type})..."
                )

                clip_path = scene_video_generator.generate_scene_video(
                    scene_info=scene,
                    episode_id=episode_id,
                    scene_number=idx,
                    visual_style=story_json.get("visual_style", "Vibrant 2D cartoon"),
                    characters=story_json.get("characters", []),
                    duration_seconds=duration,
                )
                if settings.VIDEO_GENERATION_PROVIDER == "comfyui" and clip_path is None:
                    raise RuntimeError(f"ComfyUI did not generate a clip for scene {idx}")
                frames = (
                    self._read_clip_frames(clip_path, fps, duration, (width, height))
                    if clip_path
                    else []
                )
                if clip_path and not frames and settings.VIDEO_GENERATION_PROVIDER == "comfyui":
                    raise RuntimeError(f"ComfyUI returned an unreadable scene clip: {clip_path}")
                if not frames:
                    frames = scene_animator.apply_motion(
                        image_path=str(scene_img_path),
                        motion_type=motion_type,
                        fps=fps,
                        duration_seconds=duration,
                        target_size=(width, height)
                    )

                for frame_rgb in frames:
                    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                    frame_subtitled = subtitle_renderer.overlay_subtitle(
                        frame_bgr,
                        text=narration_text,
                    )
                    writer.write(frame_subtitled)
        except Exception:
            writer.release()
            if raw_video_path.exists():
                raw_video_path.unlink()
            raise

        writer.release()
        logger.info(f"Raw frame composition saved to {raw_video_path}")

        # 2. Combine Raw Video with Audio Narration using FFmpeg / imageio-ffmpeg
        self._combine_video_and_audio(raw_video_path, scenes_audio, final_video_path)

        # Cleanup temp file
        if raw_video_path.exists():
            try:
                raw_video_path.unlink()
            except Exception:
                pass

        logger.info(f"Final MP4 Rendered Successfully: {final_video_path}")
        return final_video_path

    def _read_clip_frames(self, clip_path: Path, fps: int, duration: float, target_size):
        capture = cv2.VideoCapture(str(clip_path))
        if not capture.isOpened():
            capture.release()
            logger.warning("Could not open generated scene clip: %s", clip_path)
            return []

        target_frame_count = max(1, int(fps * duration))
        frames = []
        try:
            for frame_index in range(target_frame_count):
                capture.set(cv2.CAP_PROP_POS_MSEC, frame_index * 1000 / fps)
                success, frame_bgr = capture.read()
                if not success:
                    break
                frame_resized = cv2.resize(frame_bgr, target_size, interpolation=cv2.INTER_AREA)
                frames.append(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB))
        finally:
            capture.release()

        if frames and len(frames) < target_frame_count:
            frames.extend([frames[-1]] * (target_frame_count - len(frames)))
        return frames

    def _combine_video_and_audio(self, raw_video_path: Path, scenes_audio: List[Dict[str, Any]], output_path: Path):
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        audio_files = {}
        for scene_index, item in enumerate(scenes_audio):
            audio_path = Path(item["audio_path"])
            if audio_path.exists():
                audio_files[scene_index] = audio_path

        bg_music_track = music_manager.get_music_track()
        cmd = [
            ffmpeg_exe, "-y",
            "-i", str(raw_video_path)
        ]
        audio_input_indices = {}
        next_input_index = 1
        for scene_index, audio_path in audio_files.items():
            cmd.extend(["-i", str(audio_path)])
            audio_input_indices[scene_index] = next_input_index
            next_input_index += 1

        music_input_index = None
        if bg_music_track and bg_music_track.exists():
            cmd.extend(["-stream_loop", "-1", "-i", str(bg_music_track)])
            music_input_index = next_input_index

        filter_parts = []
        scene_audio_labels = []
        total_duration = 0.0
        for scene_index, item in enumerate(scenes_audio):
            duration = max(0.1, float(item.get("duration", 5.0)))
            total_duration += duration
            label = f"scene_audio_{scene_index}"
            scene_audio_labels.append(f"[{label}]")

            if scene_index in audio_input_indices:
                input_index = audio_input_indices[scene_index]
                filter_parts.append(
                    f"[{input_index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                    f"apad=pad_dur={duration},atrim=duration={duration},asetpts=PTS-STARTPTS[{label}]"
                )
            else:
                filter_parts.append(
                    f"anullsrc=r=48000:cl=stereo:d={duration},asetpts=PTS-STARTPTS[{label}]"
                )

        has_narration = bool(scene_audio_labels)
        if has_narration:
            filter_parts.append(
                f"{''.join(scene_audio_labels)}concat=n={len(scene_audio_labels)}:v=0:a=1[narration]"
            )

        if music_input_index is not None:
            filter_parts.append(f"[{music_input_index}:a]aresample=48000,volume=0.12[music]")
            if has_narration:
                filter_parts.append(
                    "[narration][music]amix=inputs=2:duration=first:dropout_transition=2,"
                    "alimiter=limit=0.95[aout]"
                )
            else:
                filter_parts.append("[music]alimiter=limit=0.95[aout]")
        elif has_narration:
            filter_parts.append("[narration]alimiter=limit=0.95[aout]")

        if filter_parts:
            cmd.extend(["-filter_complex", ";".join(filter_parts)])
        cmd.extend(["-map", "0:v:0"])
        if has_narration or music_input_index is not None:
            cmd.extend(["-map", "[aout]"])
        cmd.extend([
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart"
        ])
        if has_narration or music_input_index is not None:
            cmd.extend(["-c:a", "aac", "-b:a", "192k", "-ar", "48000"])
        if total_duration > 0:
            cmd.extend(["-t", f"{total_duration:.3f}"])
        if has_narration or music_input_index is not None:
            cmd.append("-shortest")
        cmd.append(str(output_path))

        try:
            logger.info(f"Combining video and audio using FFmpeg binary: {ffmpeg_exe}")
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            logger.exception("FFmpeg render failed for %s", output_path)
            raise RuntimeError(f"Could not encode final video: {e}") from e

video_renderer = VideoRenderer()
