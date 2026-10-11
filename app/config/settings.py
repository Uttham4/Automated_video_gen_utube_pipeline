import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    BASE_DIR: Path = BASE_DIR
    APP_DIR: Path = BASE_DIR / "app"
    ASSETS_DIR: Path = BASE_DIR / "assets"
    DATA_DIR: Path = BASE_DIR / "data"
    CREDENTIALS_DIR: Path = BASE_DIR / "credentials"

    STORIES_DIR: Path = DATA_DIR / "stories"
    SCENES_DIR: Path = DATA_DIR / "scenes"
    AUDIO_DIR: Path = DATA_DIR / "audio"
    RENDERS_DIR: Path = DATA_DIR / "renders"
    THUMBNAILS_DIR: Path = DATA_DIR / "thumbnails"
    LOGS_DIR: Path = DATA_DIR / "logs"
    DB_PATH: Path = DATA_DIR / "app.db"

    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    STORY_MODEL: str = os.getenv("STORY_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    NVIDIA_TIMEOUT_SECONDS: float = float(os.getenv("NVIDIA_TIMEOUT_SECONDS", "120"))
    SAFETY_MODEL: str = os.getenv("SAFETY_MODEL", "nvidia/nemotron-3.5-content-safety")
    IMAGE_MODEL: str = os.getenv("IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
    VIDEO_GENERATION_PROVIDER: str = os.getenv("VIDEO_GENERATION_PROVIDER", "local").lower()
    PIXAZO_API_KEY: str = os.getenv("PIXAZO_API_KEY", "")
    PIXAZO_VIDEO_API_URL: str = os.getenv("PIXAZO_VIDEO_API_URL", "https://api.pixazo.ai/v1/text-to-video")
    PIXAZO_VIDEO_RESOLUTION: str = os.getenv("PIXAZO_VIDEO_RESOLUTION", "720p")
    COMFYUI_API_URL: str = os.getenv("COMFYUI_API_URL", "http://127.0.0.1:8188")
    COMFYUI_WORKFLOW_PATH: Path = Path(
        os.getenv(
            "COMFYUI_WORKFLOW_PATH",
            str(APP_DIR / "config" / "ltxv_2b_api_workflow.json"),
        )
    )
    COMFYUI_TIMEOUT_SECONDS: float = float(os.getenv("COMFYUI_TIMEOUT_SECONDS", "1800"))
    COMFYUI_WIDTH: int = int(os.getenv("COMFYUI_WIDTH", "512"))
    COMFYUI_HEIGHT: int = int(os.getenv("COMFYUI_HEIGHT", "288"))
    COMFYUI_FPS: int = int(os.getenv("COMFYUI_FPS", "12"))
    COMFYUI_MAX_FRAMES: int = int(os.getenv("COMFYUI_MAX_FRAMES", "49"))

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    TTS_ENGINE: str = os.getenv("TTS_ENGINE", "edge-tts")
    DEFAULT_VOICE: str = os.getenv("DEFAULT_VOICE", "en-US-AnaNeural")
    TTS_SPEED: str = os.getenv("TTS_SPEED", "+0%")

    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "127.0.0.1")
    APP_URL: str = os.getenv("APP_URL", f"http://localhost:{PORT}")

    GMAIL_SENDER_EMAIL: str = os.getenv("GMAIL_SENDER_EMAIL", "")
    GMAIL_RECIPIENT_EMAIL: str = os.getenv("GMAIL_RECIPIENT_EMAIL", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")

    YOUTUBE_PRIVACY_STATUS: str = os.getenv("YOUTUBE_PRIVACY_STATUS", "private")
    YOUTUBE_CATEGORY_ID: str = os.getenv("YOUTUBE_CATEGORY_ID", "1")

    def ensure_directories(self):
        for dir_path in [
            self.ASSETS_DIR, self.ASSETS_DIR / "music", self.ASSETS_DIR / "fonts",
            self.DATA_DIR, self.STORIES_DIR, self.SCENES_DIR, self.AUDIO_DIR,
            self.RENDERS_DIR, self.THUMBNAILS_DIR, self.LOGS_DIR, self.CREDENTIALS_DIR
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
