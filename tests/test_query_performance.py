import tempfile
import unittest
from unittest.mock import Mock, patch

import rag


class QueryPerformanceTests(unittest.TestCase):
    def test_gemini_model_discovery_is_reused_within_the_cache_window(self):
        models = ["models/gemini-3.8-flash"]
        components = {
            "vectorstore": Mock(max_marginal_relevance_search=Mock(return_value=[])),
            "client": object(),
            "k": 4,
            "mock_mode": False,
            "gemini_models": None,
            "gemini_models_checked_at": 0.0,
        }

        with tempfile.TemporaryDirectory() as temporary_dir:
            components["vectorstore_path"] = temporary_dir
            with (
                patch.object(
                    rag,
                    "get_supported_gemini_models",
                    return_value=models,
                ) as discover_models,
                patch.object(
                    rag,
                    "generate_answer",
                    return_value="Generated answer",
                ) as generate,
                patch.object(rag, "save_generated_php_code", return_value=None),
            ):
                for _ in range(2):
                    answer, _, _, _, _ = rag.query_rag(
                        components,
                        "Generate PHP code for a login form",
                        use_cache=False,
                    )
                    self.assertEqual(answer, "Generated answer")

        discover_models.assert_called_once_with(components["client"])
        self.assertEqual(generate.call_count, 2)
        self.assertEqual(
            [call.kwargs["gemini_models"] for call in generate.call_args_list],
            [models, models],
        )

    def test_missing_gemini_client_keeps_the_actionable_configuration_error(self):
        components = {
            "vectorstore": Mock(max_marginal_relevance_search=Mock(return_value=[])),
            "client": None,
            "k": 4,
            "mock_mode": False,
            "vectorstore_path": "vectorstore",
        }

        with (
            patch.object(rag, "get_supported_gemini_models") as discover_models,
            patch.object(rag, "save_generated_php_code", return_value=None),
            self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY is not set"),
        ):
            rag.query_rag(
                components,
                "Generate PHP code for a login form",
                use_cache=False,
            )

        discover_models.assert_not_called()


if __name__ == "__main__":
    unittest.main()
