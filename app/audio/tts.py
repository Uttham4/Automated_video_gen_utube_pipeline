import asyncio
import logging
import wave
import contextlib
from pathlib import Path
from typing import Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)

class TTSEngine:
    def __init__(self, voice: Optional[str] = None):
        self.voice = voice or settings.DEFAULT_VOICE

    def generate_speech(self, text: str, output_path: Path) -> float:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 1. Try edge-tts (High quality Microsoft Neural Voice for kids)
        try:
            asyncio.run(self._edge_tts_generate(text, str(output_path)))
            duration = self.get_audio_duration(output_path)
            if duration > 0.5:
                logger.info(f"Generated Edge-TTS voice audio -> {output_path} ({duration:.2f}s)")
                return duration
        except Exception as e:
            logger.warning(f"Edge-TTS generation failed: {e}. Trying gTTS fallback...")

        # 2. Try gTTS fallback
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(str(output_path))
            duration = self.get_audio_duration(output_path)
            logger.info(f"Generated gTTS voice audio -> {output_path} ({duration:.2f}s)")
            return duration
        except Exception as e:
            logger.warning(f"gTTS fallback failed: {e}. Generating silence/tone placeholder.")

        # 3. Last fallback: Generate synthetic WAV silence with tone
        return self._generate_fallback_wav(text, output_path)

    async def _edge_tts_generate(self, text: str, output_file: str):
        import edge_tts
        communicate = edge_tts.Communicate(text, self.voice, rate=settings.TTS_SPEED)
        await communicate.save(output_file)

    def get_audio_duration(self, audio_path: Path) -> float:
        try:
            # Check wave
            if str(audio_path).endswith(".wav"):
                with contextlib.closing(wave.open(str(audio_path), 'r')) as f:
                    frames = f.getnframes()
                    rate = f.getframerate()
                    return frames / float(rate)
            # Try wave/ffprobe or opencv / imageio or size heuristic
            size = audio_path.stat().st_size
            # Rough estimation for MP3 (128kbps = 16KB/s)
            return max(3.0, size / 16000.0)
        except Exception as e:
            logger.warning(f"Could not determine audio duration for {audio_path}: {e}")
            return 5.0

    def _generate_fallback_wav(self, text: str, output_path: Path) -> float:
        # Approximate duration based on word count (avg 2.5 words per second)
        word_count = len(text.split())
        duration = max(4.0, word_count / 2.5)

        sample_rate = 22050
        num_samples = int(sample_rate * duration)
        with wave.open(str(output_path), 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for _ in range(num_samples):
                wav_file.writeframesraw(b'\x00\x00')

        return duration

tts_engine = TTSEngine()
