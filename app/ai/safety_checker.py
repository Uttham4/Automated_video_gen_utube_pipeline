import logging
from typing import Dict, Any, List, Tuple
from app.config.settings import settings
from app.ai.nvidia_client import nvidia_client

logger = logging.getLogger(__name__)

# Mandatory safety filter keywords for kids content
PROHIBITED_KEYWORDS = [
    "violence", "weapon", "gun", "knife", "blood", "kill", "death", "murder",
    "scary", "monster", "demon", "horror", "sexual", "nude", "explicit",
    "drug", "alcohol", "smoke", "gamble", "political", "hate", "racist"
]

class SafetyChecker:
    def __init__(self, client=None):
        self.client = client or nvidia_client

    def check_story_safety(self, story_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
        reasons = []

        # 1. Deterministic Rule Checks
        title = story_json.get("title", "")
        text_content = f"{title} {story_json.get('lesson', '')} "
        for scene in story_json.get("scenes", []):
            text_content += f"{scene.get('narration_text', '')} {scene.get('action_description', '')} "

        lower_text = text_content.lower()
        for kw in PROHIBITED_KEYWORDS:
            if kw in lower_text:
                reasons.append(f"Contains prohibited keyword for children: '{kw}'")

        # 2. NVIDIA Nemotron Content Safety Check (if API key available)
        if self.client.client and settings.SAFETY_MODEL:
            try:
                safety_prompt = f"Assess if the following story is 100% safe, appropriate, and wholesome for young children (ages 4-7):\n{text_content[:2000]}"
                response = self.client.generate_chat_completion(
                    messages=[{"role": "user", "content": safety_prompt}],
                    model=settings.SAFETY_MODEL,
                    max_tokens=200
                )
                if "unsafe" in response.lower() or "violation" in response.lower():
                    reasons.append(f"Nemotron Safety Flagged Content: {response[:100]}")
            except Exception as e:
                logger.warning(f"Nemotron safety API call failed: {e}. Relying on deterministic safety rules.")

        is_safe = len(reasons) == 0
        if is_safe:
            logger.info("Content Safety Check: PASSED ✅")
        else:
            logger.warning(f"Content Safety Check: FAILED ❌. Reasons: {reasons}")

        return is_safe, reasons

safety_checker = SafetyChecker()
