import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from app.ai.nvidia_client import NvidiaClient


class NvidiaClientStreamingTests(unittest.TestCase):
    def test_generate_chat_completion_collects_streamed_content(self):
        chunks = [
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Hello"))]),
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=None))]),
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=" world"))]),
        ]
        client = NvidiaClient(api_key="test-key")
        client.client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=Mock(return_value=iter(chunks)))
            )
        )

        result = client.generate_chat_completion(
            messages=[{"role": "user", "content": "Say hello"}],
            model="test-model",
        )

        self.assertEqual(result, "Hello world")
        client.client.chat.completions.create.assert_called_once_with(
            model="test-model",
            messages=[{"role": "user", "content": "Say hello"}],
            temperature=0.7,
            max_tokens=4000,
            stream=True,
            response_format={"type": "json_object"},
        )


if __name__ == "__main__":
    unittest.main()
