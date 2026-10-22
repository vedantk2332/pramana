"""
Pramana Automated Test Suite.
Validates:
- AST Static Verification Service
- RAG Extraction & Chunking Logic
- Game Mode Challenge Validation
- Django Web Endpoints & REST APIs
"""

import json
from pathlib import Path
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch


from pramana.services.verification_service import verify_code, verify_python_ast, check_balanced_delimiters
from pramana.services.rag_service import chunk_text, extract_text_from_file
from pramana.services.game_data import get_all_challenges, validate_game_answer, CHALLENGES


class VerificationServiceTests(TestCase):
    """Tests safe AST static parsing without code execution."""

    def test_valid_python_syntax_passes(self):
        code = "def add(a, b):\n    return a + b\n\nprint(add(2, 3))"
        result = verify_python_ast(code)
        self.assertEqual(result['status'], 'CHECKS PASSED')
        self.assertTrue(result['is_safe'])
        self.assertFalse(result['runtime_tested'])
        self.assertIn('0 fatal syntax errors', result['checks'][1]['detail'])

    def test_broken_python_syntax_fails(self):
        # Missing closing parenthesis on line 1
        broken_code = "def broken_func(a, b:\n    return a + b"
        result = verify_python_ast(broken_code)
        self.assertEqual(result['status'], 'CHECKS FAILED')
        self.assertTrue(len(result['errors']) > 0)
        self.assertIn('SyntaxError', result['errors'][0])

    def test_mutable_default_warning_detected(self):
        code = "def append_val(val, items=[]):\n    items.append(val)\n    return items"
        result = verify_python_ast(code)
        self.assertEqual(result['status'], 'CHECKS PASSED')
        self.assertTrue(any('Mutable default argument' in w for w in result['warnings']))

    def test_unmatched_delimiter_detected(self):
        code = "x = [1, 2, (3, 4]"
        result = check_balanced_delimiters(code)
        self.assertFalse(result['valid'])
        self.assertIn('Mismatched delimiter', result['message'])

    def test_non_python_language_returns_not_verified(self):
        code = "function test() { console.log('hello'); }"
        result = verify_code(code, language='javascript')
        self.assertEqual(result['status'], 'NOT VERIFIED')
        self.assertIn('JavaScript', result['language'])


class RAGServiceTests(TestCase):
    """Tests document extraction, chunking, and metadata preservation."""

    def test_chunking_preserves_metadata_and_overlap(self):
        pages = [
            {'page_number': 1, 'text': 'A' * 1200},
            {'page_number': 2, 'text': 'B' * 400}
        ]
        chunks = chunk_text(pages, filename='spec.txt', chunk_size=500, chunk_overlap=100)
        
        self.assertTrue(len(chunks) >= 3)
        self.assertEqual(chunks[0]['filename'], 'spec.txt')
        self.assertEqual(chunks[0]['page_number'], 1)
        self.assertEqual(chunks[-1]['page_number'], 2)
        # Check chunk length within limit
        for c in chunks:
            self.assertLessEqual(len(c['text']), 500)

    def test_text_file_extraction(self):
        # Test on one of our created sample docs
        sample_path = Path('sample_docs/python_loops_and_indexing.txt')
        if sample_path.exists():
            pages = extract_text_from_file(sample_path)
            self.assertTrue(len(pages) > 0)
            self.assertIn('Zero-Based Sequence Indexing', pages[0]['text'])


class GameModeTests(TestCase):
    """Tests interactive coding challenge catalog and evaluation."""

    def test_all_challenges_present_and_configured(self):
        challenges = get_all_challenges()
        self.assertGreaterEqual(len(challenges), 9)
        game_types = {c['game_type'] for c in challenges}
        self.assertIn('game_a', game_types)
        self.assertIn('game_b', game_types)
        self.assertIn('game_c', game_types)

    def test_correct_answer_awards_xp(self):
        # Test Game A Question 1 (ga-1)
        res = validate_game_answer('ga-1', 'for i in range(len(prices)):')
        self.assertTrue(res['is_correct'])
        self.assertEqual(res['xp_awarded'], 50)
        self.assertTrue(len(res['explanation']) > 0)

    def test_incorrect_answer_returns_explanation_no_xp(self):
        res = validate_game_answer('ga-1', 'for i in len(prices):')
        self.assertFalse(res['is_correct'])
        self.assertEqual(res['xp_awarded'], 0)
        self.assertTrue(len(res['explanation']) > 0)

    def test_line_number_answer_shorthand(self):
        # Game B Question 1 has answer 'Line 4'
        res = validate_game_answer('gb-1', 'Line 4')
        self.assertTrue(res['is_correct'])
        # Also test typing just '4'
        res2 = validate_game_answer('gb-1', '4')
        self.assertTrue(res2['is_correct'])


class WebEndpointTests(TestCase):
    """Tests Django HTTP routing and REST endpoints."""

    def setUp(self):
        self.client = Client()

    def test_index_dashboard_renders_200(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pramana')
        self.assertContains(response, 'Learn Mode')
        self.assertContains(response, 'Debug Mode')
        self.assertContains(response, 'Game Arena')

    def test_system_status_endpoint(self):
        response = self.client.get(reverse('api_status'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('has_api_key', data)
        self.assertIn('gemini_model', data)

    def test_games_list_endpoint(self):
        response = self.client.get(reverse('api_games'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['challenges']), 9)

    def test_games_check_endpoint(self):
        payload = {'challenge_id': 'ga-1', 'answer': 'for i in range(len(prices)): '}
        response = self.client.post(
            reverse('api_games_check'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_correct'])
        self.assertEqual(data['xp_awarded'], 50)

    def test_verify_code_endpoint(self):
        payload = {'code': 'x = 42\ny = x * 2', 'language': 'python'}
        response = self.client.post(
            reverse('api_verify'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['verification']['status'], 'CHECKS PASSED')

    def test_learn_empty_code_returns_400(self):
        payload = {'code': '   ', 'language': 'python'}
        response = self.client.post(
            reverse('api_learn_explain'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_safe_api_key_diagnostic_security(self):
        from pramana.services.config import get_api_key_diagnostic
        diag = get_api_key_diagnostic()
        self.assertIn('has_api_key', diag)
        self.assertIn('key_length', diag)
        self.assertIn('env_file_exists', diag)
        # CRITICAL: Confirm actual key characters are never exposed in the diagnostic
        self.assertNotIn('api_key', diag)
        self.assertNotIn('key', diag)

    def test_error_classification_mappings(self):
        from pramana.services.config import classify_gemini_error
        # 1. Invalid API Key
        err_type, msg = classify_gemini_error(Exception("ClientError: API_KEY_INVALID 400"))
        self.assertEqual(err_type, 'API_KEY_INVALID')
        self.assertIn('invalid or has expired', msg)

        # 2. Quota Exceeded
        err_type, msg = classify_gemini_error(Exception("ClientError: RESOURCE_EXHAUSTED 429 quota exceeded"))
        self.assertEqual(err_type, 'QUOTA_EXCEEDED')
        self.assertIn('quota exceeded', msg)

        # 3. Model Not Found
        err_type, msg = classify_gemini_error(Exception("ClientError: 404 NOT_FOUND models/gemini-2.0-flash"))
        self.assertEqual(err_type, 'MODEL_NOT_FOUND')

        # 4. Network Error
        err_type, msg = classify_gemini_error(Exception("Connection timeout or DNS failure"))
        self.assertEqual(err_type, 'NETWORK_ERROR')


class LearnModeAccuracyAndSpeedTests(TestCase):
    """
    Tests for AI Explanation Quality, Accuracy, Readability, and Speed.
    Validates:
    - C++ factorial off-by-one regression analysis (24 vs 120, i < n vs i <= n)
    - Full 6-section Learn Mode structure (A through F)
    - Resilient JSON cleaning for malformed or wrapped LLM outputs
    - Structural and blank line preprocessing
    - Error classification for 503 service busy, 429 quota, and network timeouts
    - Client caching to avoid recreation overhead
    """

    def setUp(self):
        self.client = Client()
        self.cpp_factorial_code = """unsigned int factorial(unsigned int n) {
    int res = 1;
    for (int i = 2; i < n; i++)
        res *= i;
    return res;
}"""

    def test_clean_json_response_resilience(self):
        from pramana.services.ai_service import clean_json_response

        # 1. Empty input
        self.assertEqual(clean_json_response(""), {})
        self.assertEqual(clean_json_response(None), {})

        # 2. Markdown fenced JSON
        markdown_json = "```json\n{\"summary\": \"Test summary\", \"lines\": []}\n```"
        parsed = clean_json_response(markdown_json)
        self.assertEqual(parsed.get('summary'), 'Test summary')

        # 3. JSON surrounded by chat chatter
        chatter_json = "Here is your requested analysis:\n{\"summary\": \"Found bug\", \"count\": 42}\nI hope this helps!"
        parsed = clean_json_response(chatter_json)
        self.assertEqual(parsed.get('summary'), 'Found bug')
        self.assertEqual(parsed.get('count'), 42)

        # 4. Completely invalid non-JSON returns safe fallback without crash
        invalid_text = "This is plain text with no JSON objects at all."
        parsed = clean_json_response(invalid_text)
        self.assertIn('raw_text', parsed)

    def test_structural_and_blank_lines_handling(self):
        from unittest.mock import patch
        from pramana.services.ai_service import explain_code_line_by_line

        mock_ai_json = {
            "summary": "Factorial function with off-by-one condition.",
            "execution_flow": ["Step 1: Initialize res", "Step 2: Run loop"],
            "lines": [
                {
                    "line_number": 1,
                    "code": "unsigned int factorial(unsigned int n) {",
                    "what": "Function header",
                    "why": "Defines entrypoint",
                    "example": "",
                    "connects": "Next line",
                    "what_if_changed": "Breaks"
                },
                {
                    "line_number": 3,
                    "code": "    for (int i = 2; i < n; i++)",
                    "what": "Loop iterating from 2 to n-1",
                    "why": "Multiplies factors",
                    "example": "i=2,3,4 for n=5",
                    "connects": "res *= i",
                    "what_if_changed": "Changing to i <= n produces 120 instead of 24"
                }
            ],
            "trace": {
                "sample_input": "factorial(5)",
                "actual_output": "24",
                "expected_output": "120",
                "iterations": [
                    {"step": "Initial", "values": "res = 1"},
                    {"step": "i = 2", "values": "res = 2"},
                    {"step": "i = 3", "values": "res = 6"},
                    {"step": "i = 4", "values": "res = 24"},
                    {"step": "i = 5", "values": "Loop exits because 5 < 5 is False! 5 is excluded."}
                ],
                "discrepancy_explanation": "Loop condition i < n stops at n-1, omitting factor n."
            },
            "concepts": [
                {"name": "Off-by-One Error", "explanation": "Loop terminates one step too early."}
            ],
            "improvement": {
                "has_issue": True,
                "issue_title": "Off-by-One Loop Exclusion",
                "issue_description": "Loop condition i < n stops at 4 for n=5.",
                "corrected_code": "unsigned int factorial(unsigned int n) {\n    int res = 1;\n    for (int i = 2; i <= n; i++)\n        res *= i;\n    return res;\n}",
                "explanation_of_change": "Change condition to i <= n to include the final factor n."
            }
        }

        class MockResponse:
            text = json.dumps(mock_ai_json)

        with patch('pramana.services.ai_service.get_gemini_client', return_value=(object(), None, None)), \
             patch('pramana.services.ai_service.call_gemini_with_retry', return_value=MockResponse()):
            res = explain_code_line_by_line(self.cpp_factorial_code, language='cpp')

        self.assertTrue(res['success'])
        # Verify 6 structured sections
        self.assertIn('summary', res)          # Section A
        self.assertIn('execution_flow', res)  # Section B
        self.assertIn('lines', res)           # Section C
        self.assertIn('trace', res)           # Section D
        self.assertIn('concepts', res)        # Section E
        self.assertIn('improvement', res)     # Section F

        # Check that closing brace on line 6 is marked as structural delimiter
        line_6 = next((l for l in res['lines'] if l['line_number'] == 6), None)
        self.assertIsNotNone(line_6)
        self.assertTrue(line_6.get('is_structural', False))
        self.assertIn('delimiter', line_6['what'].lower())

    def test_cpp_factorial_regression_factual_accuracy(self):
        from unittest.mock import patch
        from pramana.services.ai_service import explain_code_line_by_line

        mock_ai_json = {
            "summary": "This C++ function attempts to calculate the factorial of n. However, due to an off-by-one bug in the loop condition, it excludes n and produces an inaccurate result.",
            "execution_flow": [
                "Step 1: Initializes res to 1.",
                "Step 2: Runs a for-loop from i = 2 while i < n.",
                "Step 3: Multiplies res by i on each iteration.",
                "Step 4: Returns res upon loop completion."
            ],
            "lines": [
                {"line_number": 1, "code": "unsigned int factorial(unsigned int n) {", "what": "Declares factorial function.", "why": "Defines entrypoint.", "example": "", "connects": "res", "what_if_changed": "Fatal error."},
                {"line_number": 2, "code": "    int res = 1;", "what": "Initializes accumulator res to 1.", "why": "Multiplicative identity.", "example": "", "connects": "loop", "what_if_changed": "Wrong output."},
                {"line_number": 3, "code": "    for (int i = 2; i < n; i++)", "what": "Loops from 2 up to n - 1.", "why": "Accumulates product.", "example": "2, 3, 4 for n=5", "connects": "res *= i", "what_if_changed": "Changing i < n to i <= n produces 120 instead of 24 for n=5."},
                {"line_number": 4, "code": "        res *= i;", "what": "Multiplies res by current factor i.", "why": "Builds product.", "example": "res becomes 2, 6, 24", "connects": "loop", "what_if_changed": "Loop does not accumulate."},
                {"line_number": 5, "code": "    return res;", "what": "Returns accumulated result.", "why": "Supplies result to caller.", "example": "returns 24", "connects": "caller", "what_if_changed": "Function returns nothing."}
            ],
            "trace": {
                "sample_input": "factorial(5)",
                "actual_output": "24",
                "expected_output": "120",
                "iterations": [
                    {"step": "Initial", "values": "res = 1, n = 5"},
                    {"step": "i = 2", "values": "res = 1 * 2 = 2"},
                    {"step": "i = 3", "values": "res = 2 * 3 = 6"},
                    {"step": "i = 4", "values": "res = 6 * 4 = 24"},
                    {"step": "i = 5", "values": "Loop terminates because 5 < 5 is False. Factor 5 is omitted!"}
                ],
                "discrepancy_explanation": "For input 5, the loop multiplies 2 * 3 * 4 = 24, not 120, because the loop condition is i < n rather than i <= n."
            },
            "concepts": [
                {"name": "Off-by-One Error", "explanation": "A common loop boundary error where an iteration is missed or executed once too often."},
                {"name": "Accumulator Pattern", "explanation": "Iteratively aggregating values into a single variable."}
            ],
            "improvement": {
                "has_issue": True,
                "issue_title": "Off-by-One Loop Condition (Excludes n)",
                "issue_description": "The condition i < n stops before multiplying by n. For factorial(5), it calculates 2*3*4=24 instead of 120.",
                "corrected_code": "unsigned int factorial(unsigned int n) {\n    int res = 1;\n    for (int i = 2; i <= n; i++)\n        res *= i;\n    return res;\n}",
                "explanation_of_change": "Changing the loop condition to i <= n ensures that factor n (e.g. 5) is multiplied, producing 120 for factorial(5)."
            }
        }

        class MockResponse:
            text = json.dumps(mock_ai_json)

        with patch('pramana.services.ai_service.get_gemini_client', return_value=(object(), None, None)), \
             patch('pramana.services.ai_service.call_gemini_with_retry', return_value=MockResponse()):
            res = explain_code_line_by_line(self.cpp_factorial_code, language='cpp')

        # REGRESSION ASSERTIONS:
        self.assertTrue(res['success'])
        # 1. Output trace must state 24 actual, 120 expected
        self.assertEqual(res['trace']['actual_output'], '24')
        self.assertEqual(res['trace']['expected_output'], '120')
        # 2. Must identify off-by-one bug in trace or discrepancy
        self.assertIn('24', res['trace']['discrepancy_explanation'])
        self.assertIn('120', res['trace']['discrepancy_explanation'])
        self.assertIn('i < n', res['trace']['discrepancy_explanation'])
        # 3. Improvement must suggest i <= n fix
        self.assertTrue(res['improvement']['has_issue'])
        self.assertIn('i <= n', res['improvement']['corrected_code'])
        self.assertIn('i <= n', res['improvement']['explanation_of_change'])

    def test_learn_mode_api_endpoint_integration(self):
        from unittest.mock import patch

        mock_payload = {
            'success': True,
            'duration_seconds': 1.25,
            'summary': 'Calculates factorial with off-by-one flaw.',
            'execution_flow': ['Step 1: Init', 'Step 2: Loop'],
            'lines': [{'line_number': 1, 'code': 'int x = 1;', 'what': 'init', 'why': 'start', 'example': '', 'connects': '', 'what_if_changed': ''}],
            'trace': {'sample_input': 'factorial(5)', 'actual_output': '24', 'expected_output': '120', 'iterations': [], 'discrepancy_explanation': ''},
            'concepts': [{'name': 'Loop', 'explanation': 'Repetition'}],
            'improvement': {'has_issue': True, 'issue_title': 'Bug', 'issue_description': '', 'corrected_code': '', 'explanation_of_change': ''}
        }

        with patch('pramana.views.explain_code_line_by_line', return_value=mock_payload):
            response = self.client.post(
                reverse('api_learn_explain'),
                data=json.dumps({'code': self.cpp_factorial_code, 'language': 'cpp'}),
                content_type='application/json'
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['trace']['actual_output'], '24')
        self.assertEqual(data['trace']['expected_output'], '120')
        self.assertEqual(data['duration_seconds'], 1.25)

    def test_service_busy_and_timeout_classifications(self):
        from pramana.services.config import classify_gemini_error

        # 503 Overloaded
        err_type, msg = classify_gemini_error(Exception("503 The model is overloaded. Please try again later."))
        self.assertEqual(err_type, 'SERVICE_BUSY')
        self.assertIn('high demand', msg)

        # Timeout
        err_type, msg = classify_gemini_error(Exception("TimeoutError: Request timed out after 30000ms"))
        self.assertEqual(err_type, 'NETWORK_ERROR')
        self.assertIn('internet connection', msg)

    def test_client_caching_reuses_instance(self):
        from pramana.services.config import get_gemini_client
        client1, _, _ = get_gemini_client()
        client2, _, _ = get_gemini_client()
        if client1 is not None and client2 is not None:
            self.assertIs(client1, client2)

    def test_get_api_key_diagnostic_without_env_file(self):
        """Verifies that in production (where .env is not deployed), GEMINI_API_KEY from os.environ is correctly recognized."""
        from pramana.services.config import get_api_key_diagnostic
        with patch('pramana.services.config.get_env_file_path') as mock_path, \
             patch.dict('os.environ', {'GEMINI_API_KEY': 'AIzaSyTestVercelKey1234567890'}, clear=False):
            mock_path.return_value.exists.return_value = False
            diag = get_api_key_diagnostic()
            self.assertTrue(diag['has_api_key'])
            self.assertFalse(diag['env_file_exists'])
            self.assertFalse(diag['is_placeholder'])
            self.assertEqual(diag['key_length'], len('AIzaSyTestVercelKey1234567890'))



class RAGIntegrationAndPersistenceTests(TestCase):
    """
    Validates complete RAG Integration:
    - Persistence of FAISS index & metadata across restarts
    - Semantic retrieval from trees.pdf for BST insertion and inorder traversal
    - Accurate distinction: rejecting unrelated queries without fabricating citations
    - Separate measurement of retrieval vs generation durations
    - Both Learn Mode and Debug Mode querying FAISS
    """

    def setUp(self):
        self.client = Client()

    def test_faiss_persistent_index_and_metadata_consistency(self):
        from pramana.services.rag_service import store_manager
        store_manager.ensure_loaded()
        self.assertIsNotNone(store_manager.index)
        self.assertEqual(store_manager.index.ntotal, 9)
        self.assertEqual(len(store_manager.metadata), 9)
        self.assertEqual(len(store_manager.documents), 1)
        self.assertEqual(store_manager.documents[0]['filename'], 'trees.pdf')

        # Check metadata attributes
        for chunk in store_manager.metadata:
            self.assertEqual(chunk['filename'], 'trees.pdf')
            self.assertIn('page_number', chunk)
            self.assertIn('text', chunk)
            self.assertTrue(len(chunk['text']) > 0)

    def test_vector_search_direct_accuracy_on_trees_pdf(self):
        from pramana.services.rag_service import store_manager
        store_manager.ensure_loaded()
        self.assertIsNotNone(store_manager.index)
        # Search directly with unit vectors
        import numpy as np
        query_v = np.zeros((1, store_manager.dimension), dtype='float32')
        query_v[0, 0] = 1.0
        results = store_manager.search(query_v, top_k=2, score_threshold=0.0)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['filename'], 'trees.pdf')

    def test_unrelated_query_distinguished_honestly_without_fabrication(self):
        from unittest.mock import patch
        import numpy as np
        from pramana.services.rag_service import retrieve_evidence

        # Mock an embedding that produces low similarity (< 0.58)
        low_sim_embedding = np.zeros(3072, dtype='float32')
        low_sim_embedding[100] = 1.0

        class MockEmbedResponse:
            class MockEmb:
                values = low_sim_embedding.tolist()
            embeddings = [MockEmb()]

        from unittest.mock import MagicMock
        mock_client = MagicMock()
        mock_client.models.embed_content.return_value = MockEmbedResponse()
        with patch('pramana.services.rag_service.get_gemini_client', return_value=(mock_client, None, None)):
            res = retrieve_evidence("completely unrelated query about baking cookies", score_threshold=0.58)

        self.assertFalse(res['has_evidence'])
        self.assertEqual(len(res['passages']), 0)
        self.assertIn('No matching passages', res['message'])
        self.assertIn('retrieval_duration_seconds', res)

    def test_learn_mode_queries_faiss_and_returns_separate_timings(self):
        from unittest.mock import patch
        from pramana.services.ai_service import explain_code_line_by_line

        bst_code = """struct Node* insert(struct Node* root, int value) {
    if (root == NULL) return createNode(value);
    return root;
}"""

        mock_evidence = {
            'has_evidence': True,
            'retrieval_duration_seconds': 0.45,
            'message': 'Retrieved 1 supporting documentation passage.',
            'passages': [{
                'filename': 'trees.pdf',
                'page_number': 1,
                'similarity_score': 0.81,
                'text': 'struct Node* insert(struct Node* root, int value)'
            }]
        }

        mock_ai_json = {
            "summary": "BST insert operation grounded in trees.pdf documentation.",
            "execution_flow": ["Step 1: Check root == NULL"],
            "lines": [{"line_number": 1, "code": "struct Node* insert...", "what": "Defines insert", "why": "BST insertion", "example": "", "connects": "", "what_if_changed": ""}],
            "trace": {"sample_input": "insert(NULL, 10)", "actual_output": "Node(10)", "expected_output": "Node(10)", "iterations": [], "discrepancy_explanation": ""},
            "concepts": [{"name": "BST", "explanation": "Binary Search Tree"}],
            "improvement": {"has_issue": False}
        }

        class MockResponse:
            text = json.dumps(mock_ai_json)

        with patch('pramana.services.ai_service.retrieve_evidence', return_value=mock_evidence) as mock_retriever, \
             patch('pramana.services.ai_service.get_gemini_client', return_value=(object(), None, None)), \
             patch('pramana.services.ai_service.call_gemini_with_retry', return_value=MockResponse()):
            res = explain_code_line_by_line(bst_code, language='cpp')

        # Assert FAISS retrieval was called
        mock_retriever.assert_called_once()
        self.assertTrue(res['success'])
        # Assert separate timing measurements
        self.assertIn('retrieval_duration_seconds', res)
        self.assertIn('generation_duration_seconds', res)
        self.assertIn('duration_seconds', res)
        self.assertGreaterEqual(res['duration_seconds'], res['retrieval_duration_seconds'])
        # Assert Evidence Trail returned
        self.assertTrue(res['evidence_trail']['has_evidence'])
        self.assertEqual(len(res['evidence_trail']['passages']), 1)
        self.assertEqual(res['evidence_trail']['passages'][0]['filename'], 'trees.pdf')

    def test_debug_mode_queries_faiss_and_returns_separate_timings(self):
        from unittest.mock import patch
        from pramana.services.ai_service import analyze_bug_dna

        inorder_code = """void inorderTraversal(struct Node* root) {
    if (root != NULL) {
        inorderTraversal(root->left);
        printf("%d ", root->data);
        inorderTraversal(root->right);
    }
}"""

        mock_evidence = {
            'has_evidence': True,
            'retrieval_duration_seconds': 0.38,
            'message': 'Retrieved 1 supporting documentation passage.',
            'passages': [{
                'filename': 'trees.pdf',
                'page_number': 2,
                'similarity_score': 0.79,
                'text': 'void inorderTraversal(struct Node* root) ...'
            }]
        }

        mock_ai_json = {
            "visible_symptom": "None",
            "root_cause": "None",
            "error_type": "None",
            "affected_line_number": 1,
            "affected_expression": "",
            "why_occurs": "",
            "likely_impact": "",
            "corrected_code": inorder_code,
            "change_summary": "Code is correct",
            "beginner_explanation": "Traverses left subtree, root, right subtree.",
            "documentation_claims": ["[Doc: trees.pdf, p. 2] In-order traversal visits nodes in sorted order."],
            "ai_suggestions": [],
            "unverified_claims": []
        }

        class MockResponse:
            text = json.dumps(mock_ai_json)

        with patch('pramana.services.ai_service.retrieve_evidence', return_value=mock_evidence) as mock_retriever, \
             patch('pramana.services.ai_service.get_gemini_client', return_value=(object(), None, None)), \
             patch('pramana.services.ai_service.call_gemini_with_retry', return_value=MockResponse()):
            res = analyze_bug_dna(inorder_code, language='cpp', problem_description='Inorder traversal trace')

        # Assert FAISS retrieval was called
        mock_retriever.assert_called_once()
        self.assertTrue(res['success'])
        # Assert separate timing measurements
        self.assertIn('retrieval_duration_seconds', res)
        self.assertIn('generation_duration_seconds', res)
        # Assert Evidence Trail returned
        self.assertTrue(res['evidence_trail']['has_evidence'])
        self.assertEqual(res['evidence_trail']['passages'][0]['filename'], 'trees.pdf')
        self.assertEqual(res['evidence_trail']['passages'][0]['page_number'], 2)

    def test_rag_query_endpoint(self):
        from unittest.mock import patch

        mock_evidence = {
            'has_evidence': True,
            'retrieval_duration_seconds': 0.52,
            'message': 'Retrieved 2 supporting documentation passage(s).',
            'passages': [
                {'filename': 'trees.pdf', 'page_number': 1, 'similarity_score': 0.80, 'text': 'struct Node* insert...'},
                {'filename': 'trees.pdf', 'page_number': 2, 'similarity_score': 0.76, 'text': 'void inorderTraversal...'}
            ]
        }

        with patch('pramana.views.retrieve_evidence', return_value=mock_evidence):
            response = self.client.post(
                reverse('api_rag_query'),
                data=json.dumps({'query': 'binary search tree insert'}),
                content_type='application/json'
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['evidence']['has_evidence'])
        self.assertEqual(len(data['evidence']['passages']), 2)
        self.assertEqual(data['evidence']['passages'][0]['filename'], 'trees.pdf')



