STORY_GENERATOR_SYSTEM_PROMPT = """You are a master children's animated story writer and director for YouTube channels targeting ages 3-8.
Your job is to generate engaging, wholesome, safe, and imaginative story episodes formatted strictly as valid JSON.

RULES:
1. Output MUST be strictly valid JSON without markdown wrapping (no ```json codeblocks).
2. The story MUST contain 5 to 8 distinct visual scenes.
3. Keep visual descriptions detailed and consistent with 2D cartoon style (bright colors, expressive characters, clear backgrounds).
4. Include clear character definitions (character consistency bible).
5. Ensure narration text is engaging, clear, easy to understand, and kid-friendly.
"""

STORY_GENERATOR_USER_PROMPT = """Create an animated episode story about the topic/theme: "{topic}".

Required JSON format:
{{
  "title": "Story Title",
  "target_age": "4-7",
  "language": "English",
  "estimated_duration_seconds": 180,
  "lesson": "Moral or educational takeaways",
  "visual_style": "Vibrant 2D vector cartoon, storybook illustration, warm lighting, expressive faces",
  "characters": [
    {{
      "id": "char_1",
      "name": "Character Name",
      "species_or_type": "Rabbit/Bear/Child/etc",
      "visual_description": "Detailed description: orange fur, big green eyes, blue backpack, red sneakers"
    }}
  ],
  "scenes": [
    {{
      "scene_number": 1,
      "location": "Sunny Meadow with colorful wildflowers",
      "characters_present": ["char_1"],
      "action_description": "Character skips through the meadow holding a shiny golden key",
      "image_prompt": "Vibrant 2D cartoon illustration of an orange rabbit with big green eyes wearing a blue backpack skipping through a sunny meadow filled with colorful flowers, wide angle, high quality storybook style",
      "narration_text": "Once upon a time, in a bright sunny meadow, Milo the little rabbit found something extraordinary.",
      "camera_motion": "slow_zoom_in",
      "duration_seconds": 6
    }}
  ],
  "youtube": {{
    "title": "Story Title | Animated Kids Story",
    "description": "Engaging kids story description including moral lessons and key tags.",
    "tags": ["kids story", "animated cartoon", "bedtime story", "moral stories for children"]
  }}
}}
"""
