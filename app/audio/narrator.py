import logging
from pathlib import Path
from typing import Dict, Any, List
from app.config.settings import settings
from app.audio.tts import tts_engine

logger = logging.getLogger(__name__)

class Narrator:
    def __init__(self, tts=None):
        self.tts = tts or tts_engine

    def generate_episode_narration(self, story_json: Dict[str, Any], episode_id: str) -> List[Dict[str, Any]]:
        audio_dir = settings.AUDIO_DIR / episode_id
        audio_dir.mkdir(parents=True, exist_ok=True)

        scenes_audio = []
        scenes = story_json.get("scenes", [])

        for idx, scene in enumerate(scenes, start=1):
            narration_text = scene.get("narration_text", "")
            output_file = audio_dir / f"scene_{idx:02d}.mp3"
            
            logger.info(f"Generating narration for Scene {idx}: '{narration_text[:40]}...'")
            duration = self.tts.generate_speech(narration_text, output_file)
            
            # Update scene duration if audio is longer than default
            scene_duration = max(float(scene.get("duration_seconds", 5)), duration + 0.8)

            scenes_audio.append({
                "scene_number": idx,
                "narration_text": narration_text,
                "audio_path": str(output_file),
                "duration": scene_duration
            })

        logger.info(f"Generated narration for {len(scenes_audio)} scenes in episode {episode_id}")
        return scenes_audio

narrator = Narrator()
