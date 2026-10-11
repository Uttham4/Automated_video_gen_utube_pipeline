import json
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI
from app.config.settings import settings

logger = logging.getLogger(__name__)

class NvidiaClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.NVIDIA_API_KEY or settings.OPENAI_API_KEY
        self.base_url = base_url or settings.NVIDIA_BASE_URL
        if self.api_key and self.api_key.strip():
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=settings.NVIDIA_TIMEOUT_SECONDS,
                max_retries=1
            )
        else:
            self.client = None

    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        model_name = model or settings.STORY_MODEL

        if not self.client:
            logger.warning("No API key set for NVIDIA NIM / OpenAI. Falling back to local template response.")
            return self._mock_story_response(messages)

        try:
            stream = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                response_format={"type": "json_object"}
            )
            return "".join(
                chunk.choices[0].delta.content
                for chunk in stream
                if chunk.choices and chunk.choices[0].delta.content is not None
            )
        except Exception as e:
            logger.exception("Error calling NVIDIA NIM endpoint (%s)", model_name)
            raise RuntimeError(f"Story generation failed using NVIDIA model {model_name}") from e

    def _mock_story_response(self, messages: List[Dict[str, str]]) -> str:
        # Extract topic if present in user message
        topic = "Milo the Rabbit and the Lost Star"
        for msg in messages:
            if msg.get("role") == "user":
                topic = msg.get("content", topic)

        mock_data = {
            "title": f"Milo and the Magic Adventure",
            "target_age": "4-7",
            "language": "English",
            "estimated_duration_seconds": 30,
            "lesson": "Kindness, curiosity, and teamwork bring magic into the world.",
            "visual_style": "Vibrant 2D vector cartoon, storybook illustration, warm lighting, cute character design",
            "characters": [
                {
                    "id": "milo",
                    "name": "Milo",
                    "species_or_type": "Little Orange Rabbit",
                    "visual_description": "Small fluffy orange rabbit with big playful green eyes and a blue backpack"
                },
                {
                    "id": "luna",
                    "name": "Luna",
                    "species_or_type": "Wise Owl",
                    "visual_description": "Gentle purple owl with round glasses and yellow feathers"
                }
            ],
            "scenes": [
                {
                    "scene_number": 1,
                    "location": "Sunny Enchanted Forest Meadow",
                    "characters_present": ["milo"],
                    "action_description": "Milo wakes up under a rainbow tree and discovers a glowing map",
                    "image_prompt": "Cute orange rabbit with blue backpack looking amazed at a glowing golden map in a vibrant sunlit cartoon forest, storybook 2D digital art",
                    "narration_text": "One sunny morning in the Whispering Forest, Milo the little rabbit found a glowing golden map right under his favorite sleeping tree.",
                    "camera_motion": "slow_zoom_in",
                    "duration_seconds": 6
                },
                {
                    "scene_number": 2,
                    "location": "Sparkling River Bank",
                    "characters_present": ["milo", "luna"],
                    "action_description": "Milo meets Luna the owl near a bridge made of colorful stones",
                    "image_prompt": "Cute orange rabbit showing a map to a friendly purple owl wearing round glasses by a sparkling blue river, vibrant 2D cartoon style",
                    "narration_text": "Down by the sparkling river, Milo met Luna the wise owl. Together, they read the mysterious secret path.",
                    "camera_motion": "pan_right",
                    "duration_seconds": 6
                },
                {
                    "scene_number": 3,
                    "location": "Crystal Cave Entrance",
                    "characters_present": ["milo", "luna"],
                    "action_description": "They reach a cave filled with glowing stars and gentle fireflies",
                    "image_prompt": "Orange rabbit and purple owl stepping inside a magical crystal cave filled with twinkling blue and gold lights, whimsical 2D animation style",
                    "narration_text": "Following the glowing map, they arrived at Star Cave, where thousands of tiny friendly fireflies danced in the air.",
                    "camera_motion": "slow_zoom_out",
                    "duration_seconds": 6
                },
                {
                    "scene_number": 4,
                    "location": "Center of Star Cave",
                    "characters_present": ["milo", "luna"],
                    "action_description": "Milo finds a lost little star and gently holds it",
                    "image_prompt": "Cute little orange rabbit gently holding a happy sparkling baby star that shines brightly, joyful cartoon illustration",
                    "narration_text": "In the middle of the cave sat a tiny lost star, sparkling softly. Milo gave it a warm bunny hug.",
                    "camera_motion": "slow_zoom_in",
                    "duration_seconds": 6
                },
                {
                    "scene_number": 5,
                    "location": "Night Sky View above Forest",
                    "characters_present": ["milo", "luna"],
                    "action_description": "The star floats up into the magical night sky and twinkles brightly",
                    "image_prompt": "Cute orange rabbit and purple owl waving goodbye to a bright star flying up into a stunning magical starry night sky, cozy storybook art",
                    "narration_text": "With help from his friend Luna, Milo helped the star float high back up into the night sky. Helping others always makes the world shine brighter!",
                    "camera_motion": "pan_left",
                    "duration_seconds": 6
                }
            ],
            "youtube": {
                "title": "Milo and the Magic Star | Wholesome Animated Kids Story",
                "description": "Join Milo the rabbit and Luna the owl on a magical adventure to help a lost star find its way home!",
                "tags": ["kids story", "animated cartoon", "bedtime story", "moral stories for children", "milo rabbit"]
            }
        }
        return json.dumps(mock_data)

nvidia_client = NvidiaClient()
