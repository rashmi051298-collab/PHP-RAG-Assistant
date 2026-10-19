import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from google.genai.errors import APIError

import rag


class ProviderRoutingTests(unittest.TestCase):
    def test_code_requests_use_gemini_and_explanations_use_nvidia(self):
        self.assertTrue(
            rag.is_code_generation_request("Build a PHP project with login")
        )
        self.assertFalse(
            rag.is_code_generation_request("Explain this PHP code")
        )
        self.assertFalse(
            rag.is_code_generation_request(
                "Explain how to build a PHP inventory application"
            )
        )
        self.assertFalse(
            rag.is_code_generation_request(
                "How do I create a PHP application?"
            )
        )
        self.assertTrue(
            rag.is_code_generation_request(
                "Explain how sessions work, then write a PHP example"
            )
        )

        with (
            patch.object(rag, "generate_gemini_answer", return_value="code") as gemini,
            patch.object(rag, "generate_nvidia_answer", return_value="explanation") as nvidia,
        ):
            code_answer = rag.generate_answer(
                object(),
                "prompt",
                question="Generate a PHP login form",
            )
            explanation = rag.generate_answer(
                object(),
                "prompt",
                question="Explain how PHP sessions work",
            )

        self.assertEqual(code_answer, "code")
        self.assertEqual(explanation, "explanation")
        gemini.assert_called_once()
        nvidia.assert_called_once()

    def test_model_discovery_includes_supported_text_models_in_range_only(self):
        client = SimpleNamespace(
            models=SimpleNamespace(
                list=Mock(
                    return_value=[
                        SimpleNamespace(
                            name="models/gemini-2.5-pro",
                            supported_actions=["generateContent"],
                        ),
                        SimpleNamespace(
                            name="models/gemini-3.8-flash",
                            supported_actions=["generateContent"],
                        ),
                        SimpleNamespace(
                            name="models/gemini-3.8-live",
                            supported_actions=["generateContent"],
                        ),
                        SimpleNamespace(
                            name="models/gemini-3.9-flash",
                            supported_actions=["generateContent"],
                        ),
                        SimpleNamespace(
                            name="models/gemini-3.7-flash-image",
                            supported_actions=["generateContent"],
                        ),
                    ]
                )
            )
        )

        self.assertEqual(
            rag.get_supported_gemini_models(client),
            ["models/gemini-3.8-flash", "models/gemini-2.5-pro"],
        )
        client.models.list.assert_called_once()

    def test_gemini_falls_back_when_a_model_is_unavailable(self):
        client = SimpleNamespace(
            models=SimpleNamespace(
                list=Mock(
                    return_value=[
                        SimpleNamespace(
                            name="models/gemini-3.8-flash",
                            supported_actions=["generateContent"],
                        ),
                        SimpleNamespace(
                            name="models/gemini-2.5-flash",
                            supported_actions=["generateContent"],
                        ),
                    ]
                )
            )
        )
        with patch.object(
            rag,
            "_generate_content_with_retry",
            side_effect=[
                APIError(503, {}),
                SimpleNamespace(text="fallback response"),
            ],
        ) as generate:
            answer = rag.generate_gemini_answer(client, "prompt")

        self.assertEqual(answer, "fallback response")
        self.assertEqual(
            [call.args[1] for call in generate.call_args_list],
            ["models/gemini-3.8-flash", "models/gemini-2.5-flash"],
        )

    def test_nvidia_api_uses_configured_model_and_key(self):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "Explanation"}}]
        }
        with (
            patch.dict(os.environ, {"NVIDIA_API_KEY": "test-key"}),
            patch.object(
                rag,
                "NVIDIA_MODEL",
                "nvidia/nemotron-3.5-lightning-30b-a3b",
            ),
            patch.object(rag.requests, "post", return_value=response) as post,
        ):
            answer = rag.generate_nvidia_answer("prompt")

        self.assertEqual(answer, "Explanation")
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Bearer test-key",
        )
        self.assertEqual(
            post.call_args.kwargs["json"]["model"],
            "nvidia/nemotron-3.5-lightning-30b-a3b",
        )
        self.assertEqual(post.call_args.kwargs["timeout"], (10, 120))

    def test_nvidia_request_failures_are_reported(self):
        with (
            patch.dict(os.environ, {"NVIDIA_API_KEY": "test-key"}),
            patch.object(
                rag.requests,
                "post",
                side_effect=requests.ConnectionError("offline"),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "NVIDIA explanation request failed",
            ):
                rag.generate_nvidia_answer("prompt")

    def test_nvidia_http_410_explains_model_unavailability(self):
        response = Mock()
        response.status_code = 410
        response.json.return_value = {
            "detail": "This model endpoint is no longer available."
        }
        http_error = requests.HTTPError(response=response)

        with (
            patch.dict(os.environ, {"NVIDIA_API_KEY": "test-key"}),
            patch.object(
                rag.requests,
                "post",
                return_value=Mock(
                    raise_for_status=Mock(side_effect=http_error)
                ),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                r"HTTP 410 \(Gone\).*NVIDIA_MODEL.*no longer available",
            ):
                rag.generate_nvidia_answer("prompt")


if __name__ == "__main__":
    unittest.main()
