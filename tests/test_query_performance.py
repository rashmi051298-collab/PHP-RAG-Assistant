import tempfile
import unittest
from unittest.mock import Mock, patch

import rag


class QueryPerformanceTests(unittest.TestCase):
    def test_code_and_project_requests_use_smaller_retrieval_budgets(self):
        test_cases = (
            ("Write PHP code for a login form", 4, 16, 25),
            ("Build a complete PHP project for inventory", 6, 24, 25),
        )

        for question, expected_k, expected_fetch_k, expected_target in test_cases:
            with self.subTest(question=question), tempfile.TemporaryDirectory() as temporary_dir:
                vectorstore = Mock(
                    max_marginal_relevance_search=Mock(return_value=[])
                )
                components = {
                    "vectorstore": vectorstore,
                    "client": object(),
                    "k": 12,
                    "mock_mode": False,
                    "vectorstore_path": temporary_dir,
                }

                with (
                    patch.object(
                        rag,
                        "get_supported_gemini_models",
                        return_value=["models/gemini-3.8-flash"],
                    ),
                    patch.object(
                        rag,
                        "generate_answer",
                        return_value="Generated answer",
                    ),
                    patch.object(rag, "save_generated_php_code", return_value=None),
                ):
                    rag.query_rag(components, question, use_cache=False)

                self.assertEqual(
                    rag.get_response_time_target(),
                    expected_target,
                )
                self.assertEqual(
                    vectorstore.max_marginal_relevance_search.call_args.kwargs[
                        "k"
                    ],
                    expected_k,
                )
                self.assertEqual(
                    vectorstore.max_marginal_relevance_search.call_args.kwargs[
                        "fetch_k"
                    ],
                    expected_fetch_k,
                )

    def test_explanation_retrieval_depth_remains_unchanged(self):
        vectorstore = Mock(max_marginal_relevance_search=Mock(return_value=[]))
        components = {
            "vectorstore": vectorstore,
            "client": None,
            "k": 12,
            "mock_mode": False,
            "vectorstore_path": "vectorstore",
        }

        with (
            patch.object(rag, "generate_answer", return_value="Explanation"),
            patch.object(rag, "save_generated_php_code", return_value=None),
        ):
            rag.query_rag(
                components,
                "Explain how caching works in a search system",
                use_cache=False,
            )

        self.assertEqual(
            rag.get_response_time_target(),
            25,
        )
        self.assertEqual(
            vectorstore.max_marginal_relevance_search.call_args.kwargs["k"],
            12,
        )
        self.assertEqual(
            vectorstore.max_marginal_relevance_search.call_args.kwargs[
                "fetch_k"
            ],
            48,
        )

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
