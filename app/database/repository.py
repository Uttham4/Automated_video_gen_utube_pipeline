import sqlite3
from datetime import datetime, timezone
from typing import List, Optional
from app.config.settings import settings
from app.database.models import VideoRecord, VideoStatus

class VideoRepository:
    def __init__(self, db_path=None):
        self.db_path = str(db_path or settings.DB_PATH)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id TEXT UNIQUE NOT NULL,
                topic TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                story_json_path TEXT,
                video_path TEXT,
                thumbnail_path TEXT,
                narration_path TEXT,
                youtube_id TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()

    def create_video(self, episode_id: str, topic: str, title: str = "Untitled Episode") -> VideoRecord:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO videos (episode_id, topic, title, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (episode_id, topic, title, VideoStatus.CREATED.value, now, now))
            conn.commit()
            record_id = cursor.lastrowid
        return self.get_by_id(record_id)

    def update_status(
        self,
        episode_id: str,
        status: VideoStatus,
        story_json_path: Optional[str] = None,
        video_path: Optional[str] = None,
        thumbnail_path: Optional[str] = None,
        narration_path: Optional[str] = None,
        youtube_id: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        now = datetime.utcnow().isoformat()
        updates = ["status = ?", "updated_at = ?"]
        params = [status.value, now]

        if story_json_path is not None:
            updates.append("story_json_path = ?")
            params.append(story_json_path)
        if video_path is not None:
            updates.append("video_path = ?")
            params.append(video_path)
        if thumbnail_path is not None:
            updates.append("thumbnail_path = ?")
            params.append(thumbnail_path)
        if narration_path is not None:
            updates.append("narration_path = ?")
            params.append(narration_path)
        if youtube_id is not None:
            updates.append("youtube_id = ?")
            params.append(youtube_id)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)

        params.append(episode_id)
        sql = f"UPDATE videos SET {', '.join(updates)} WHERE episode_id = ?"

        with self.get_connection() as conn:
            conn.execute(sql, params)
            conn.commit()

    def transition_status(
        self,
        episode_id: str,
        expected_statuses: List[VideoStatus],
        status: VideoStatus,
    ) -> bool:
        if not expected_statuses:
            raise ValueError("At least one expected status is required")

        placeholders = ", ".join("?" for _ in expected_statuses)
        params = [
            status.value,
            datetime.now(timezone.utc).isoformat(),
            episode_id,
            *(expected.value for expected in expected_statuses),
        ]
        with self.get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE videos SET status = ?, updated_at = ?, error_message = NULL "
                f"WHERE episode_id = ? AND status IN ({placeholders})",
                params,
            )
            conn.commit()
        return cursor.rowcount == 1

    def get_by_episode_id(self, episode_id: str) -> Optional[VideoRecord]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM videos WHERE episode_id = ?", (episode_id,)).fetchone()
            if row:
                return self._row_to_record(row)
        return None

    def get_by_id(self, video_id: int) -> Optional[VideoRecord]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
            if row:
                return self._row_to_record(row)
        return None

    def list_all(self, limit: int = 50) -> List[VideoRecord]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM videos ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: sqlite3.Row) -> VideoRecord:
        return VideoRecord(
            id=row["id"],
            episode_id=row["episode_id"],
            topic=row["topic"],
            title=row["title"],
            status=VideoStatus(row["status"]),
            story_json_path=row["story_json_path"],
            video_path=row["video_path"],
            thumbnail_path=row["thumbnail_path"],
            narration_path=row["narration_path"],
            youtube_id=row["youtube_id"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

repo = VideoRepository()
