from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

class VideoStatus(str, Enum):
    CREATED = "CREATED"
    STORY_GENERATED = "STORY_GENERATED"
    SAFETY_CHECKED = "SAFETY_CHECKED"
    SCENES_GENERATED = "SCENES_GENERATED"
    AUDIO_GENERATED = "AUDIO_GENERATED"
    VIDEO_RENDERED = "VIDEO_RENDERED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    UPLOADING = "UPLOADING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"

@dataclass
class VideoRecord:
    id: Optional[int]
    episode_id: str
    topic: str
    title: str
    status: VideoStatus
    story_json_path: Optional[str] = None
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    narration_path: Optional[str] = None
    youtube_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
