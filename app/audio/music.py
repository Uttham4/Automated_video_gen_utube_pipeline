import logging
from pathlib import Path
from typing import Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)

class MusicManager:
    def __init__(self):
        self.music_dir = settings.ASSETS_DIR / "music"
        self.music_dir.mkdir(parents=True, exist_ok=True)

    def get_music_track(self, mood: Optional[str] = None) -> Optional[Path]:
        tracks = [
            path
            for path in list(self.music_dir.glob("*.wav")) + list(self.music_dir.glob("*.mp3"))
            if path.name.lower() != "happy_whimsical.wav"
        ]
        if tracks:
            return sorted(tracks)[0]
        return None

music_manager = MusicManager()
