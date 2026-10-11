import json
import logging
import re
from pathlib import Path
from typing import Dict, Any
from app.config.settings import settings
from app.config.prompts import STORY_GENERATOR_SYSTEM_PROMPT, STORY_GENERATOR_USER_PROMPT
from app.ai.nvidia_client import nvidia_client

logger = logging.getLogger(__name__)

class StoryGenerator:
    def __init__(self, client=None):
        self.client = client or nvidia_client

    def generate_story(self, topic: str, episode_id: str) -> Dict[str, Any]:
        logger.info(f"Generating story for topic: '{topic}' (episode_id: {episode_id})")

        messages = [
            {"role": "system", "content": STORY_GENERATOR_SYSTEM_PROMPT},
            {"role": "user", "content": STORY_GENERATOR_USER_PROMPT.format(topic=topic)}
        ]

        raw_response = self.client.generate_chat_completion(messages=messages, model=settings.STORY_MODEL)
        story_json = self._parse_json(raw_response)

        # Ensure directory & save json file
        settings.STORIES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = settings.STORIES_DIR / f"{episode_id}.json"

        story_json["episode_id"] = episode_id
        story_json["topic"] = topic

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(story_json, f, indent=2, ensure_ascii=False)

        logger.info(f"Story saved to {file_path}")
        return story_json

    def _parse_json(self, raw_text: str) -> Dict[str, Any]:
        # Strip markdown fences if LLM returns ```json ... ```
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode failed on raw response: {e}. Attempting extraction via regex...")
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            raise ValueError(f"Could not parse valid JSON from AI story output: {raw_text[:200]}")

story_generator = StoryGenerator()
