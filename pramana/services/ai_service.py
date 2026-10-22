"""
Pramana AI Service:
- High-accuracy Learn Mode code comprehension
- Bug DNA Debug Mode diagnosis
- Real RAG Evidence grounding
- Fast structured JSON generation with controlled thinking budget
"""

import os
import json
import logging
import re
import time
from typing import Dict, Any, Optional, List

from google.genai import types

from pramana.services.config import get_gemini_client, classify_gemini_error
from pramana.services.rag_service import retrieve_evidence
from pramana.services.verification_service import verify_code

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite').strip() or 'gemini-3.1-flash-lite'


def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Extracts JSON safely from LLM output markdown or raw text."""
    if not raw_text:
        return {}

    text = raw_text.strip()

    # Strip markdown code fences if present
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        # Fallback: search for first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except Exception as e:
                logger.error(f"Failed to parse JSON substring: {e}")

    logger.error("Could not parse JSON from model output.")
    return {"raw_text": raw_text}


def call_gemini_with_retry(client, model: str, contents: str, max_retries: int = 3, thinking_budget: int = 1024):
    """
    Executes model generation with controlled thinking budget and exponential retry for 503 spikes.
    Controlled thinking budget dramatically speeds up responses from ~60s down to ~5-15s.
    """
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
        temperature=0.1
    )

    for attempt in range(max_retries + 1):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
        except Exception as e:
            err_str = str(e).lower()
            if attempt < max_retries and ('503' in err_str or 'unavailable' in err_str or 'high demand' in err_str):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise


def explain_code_line_by_line(code: str, language: str = 'python') -> Dict[str, Any]:
    """
    Learn Mode: Rigorous, beginner-friendly, factually accurate code explainer.
    Produces structured sections:
    A. What does this program do?
    B. How does it work? (Execution flow)
    C. Line-by-line explanation (Only meaningful lines; structural/blank lines handled cleanly)
    D. Output and execution trace (With loop iteration table & off-by-one detection)
    E. Important concepts
    F. Suggested improvement (If flaw exists, show minimal fix & rationale)
    """
    if not code or not code.strip():
        return {
            'success': False,
            'error_type': 'EMPTY_INPUT',
            'error': 'Please provide code to analyze.'
        }

    client, err_type, err_msg = get_gemini_client()
    if not client:
        return {
            'success': False,
            'error_type': err_type or 'API_KEY_MISSING',
            'error': err_msg or 'GEMINI_API_KEY is not configured in .env. Please set your key in .env to unlock live AI code explanation.'
        }

    raw_lines = code.split('\n')
    numbered_lines = []
    meaningful_lines_count = 0

    for idx, line in enumerate(raw_lines, 1):
        clean = line.strip()
        numbered_lines.append(f"{idx}: {line}")
        if clean and clean not in ('{', '}', ';'):
            meaningful_lines_count += 1

    numbered_code = "\n".join(numbered_lines)

    # Step 1: Semantic Retrieval from persistent FAISS index (Real RAG)
    t_retrieval_start = time.time()
    query_parts = [language]
    for line in raw_lines[:8]:
        clean_l = line.strip()
        if clean_l and not clean_l.startswith(('//', '#', '/*')) and clean_l not in ('{', '}', ';'):
            query_parts.append(clean_l)
        elif any(kw in clean_l.lower() for kw in ('tree', 'insert', 'inorder', 'traversal', 'node', 'bst', 'delete', 'binary')):
            query_parts.append(clean_l)
    search_query = " ".join(query_parts)[:300].strip()

    evidence_data = retrieve_evidence(search_query, top_k=3, score_threshold=0.65)
    retrieval_duration = round(time.time() - t_retrieval_start, 2)

    evidence_context = ""
    if evidence_data['has_evidence']:
        evidence_context = "SUPPORTING DOCUMENTATION PASSAGES RETRIEVED FROM CORPUS:\n"
        for i, passage in enumerate(evidence_data['passages'], 1):
            evidence_context += f"[Passage {i}] File: {passage['filename']} (Page/Section {passage['page_number']}) (Cosine Similarity: {passage['similarity_score']}):\n"
            evidence_context += f"{passage['text']}\n\n"
    else:
        evidence_context = "NO MATCHING DOCUMENTATION FOUND IN UPLOADED CORPUS.\n"

    prompt = f"""You are Pramana, an elite programming tutor designed to explain code with beginner-friendly clarity, crisp readability, and rigorous factual accuracy.
Analyze the following {language} code.

{evidence_context}

DOCUMENTATION GROUNDING DIRECTIVE:
1. If supporting documentation passages are provided above, explicitly ground your explanation in these verified passages. Cite the exact document name and page number (e.g. [Doc: trees.pdf, p. 1]) when describing concepts or structures that match the uploaded material.
2. If NO matching documentation was found, rely strictly on general programming knowledge and note that no uploaded documentation matched. Do NOT fabricate citations or claim facts are from documents that do not exist in the passages.

CRITICAL LOGICAL ACCURACY DIRECTIVE:
1. Never assume code is correct just from function or variable names.
2. Mathematically evaluate loops, boundary conditions, and accumulator variables.
3. Specifically for accumulator/factorial loops:
   - Check if loop condition is '<' vs '<='.
   - For example, in: for (int i = 2; i < n; i++) res *= i;
     If n = 5, the loop iterates for i = 2, 3, 4 only.
     res = 1 * 2 * 3 * 4 = 24. It does NOT produce 120 because the factor 5 is omitted by the '<' condition!
   - Explicitly highlight any off-by-one errors. Explain that changing 'i < n' to 'i <= n' includes n and produces 120 for input 5.
4. Keep explanations concise, bulleted, and easy for beginners to scan. Avoid giant dense paragraphs.

CODE WITH LINE NUMBERS:
{numbered_code}

Return STRICT JSON matching this exact schema:
{{
  "summary": "2-3 simple sentences explaining what the program actually does and noting any critical flaw or limitation.",
  "execution_flow": [
    "Step 1: Description of first action...",
    "Step 2: Description of next action..."
  ],
  "lines": [
    {{
      "line_number": 1,
      "code": "code line text",
      "what": "Simple explanation of what this statement does.",
      "why": "Why it is needed in this program.",
      "example": "Small concrete example if helpful.",
      "connects": "How it links to nearby lines.",
      "what_if_changed": "Likely consequence if removed or altered."
    }}
  ],
  "trace": {{
    "sample_input": "e.g. factorial(5)",
    "actual_output": "e.g. 24",
    "expected_output": "e.g. 120 (if corrected)",
    "iterations": [
      {{"step": "Initial", "values": "res = 1, n = 5"}},
      {{"step": "i = 2", "values": "res = 1 * 2 = 2"}},
      {{"step": "i = 3", "values": "res = 2 * 3 = 6"}},
      {{"step": "i = 4", "values": "res = 6 * 4 = 24"}},
      {{"step": "i = 5", "values": "Terminates because condition i < n (5 < 5) is False. Factor 5 is omitted!"}}
    ],
    "discrepancy_explanation": "Clear explanation of why actual output differs from mathematical expectations."
  }},
  "concepts": [
    {{
      "name": "Concept Name",
      "explanation": "Brief beginner-friendly explanation."
    }}
  ],
  "improvement": {{
    "has_issue": true,
    "issue_title": "Issue Title",
    "issue_description": "Clear explanation of the bug or limitation.",
    "corrected_code": "Complete corrected code snippet.",
    "explanation_of_change": "Exact description of what was changed and why it fixes the issue."
  }}
}}

Provide line-by-line entries only for meaningful statements.
Return ONLY valid JSON.
"""

    t_gen_start = time.time()
    try:
        model_name = os.getenv('GEMINI_MODEL', GEMINI_MODEL).strip() or 'gemini-3.1-flash-lite'
        response = call_gemini_with_retry(
            client,
            model=model_name,
            contents=prompt,
            thinking_budget=1024
        )
        generation_duration = round(time.time() - t_gen_start, 2)
        total_duration = round(retrieval_duration + generation_duration, 2)
        logger.info(f"Learn Mode generated in {total_duration}s (retrieval: {retrieval_duration}s, gen: {generation_duration}s) using {model_name}")

        raw_output = response.text if hasattr(response, 'text') else str(response)
        parsed = clean_json_response(raw_output)

        model_lines = {l.get('line_number'): l for l in parsed.get('lines', []) if isinstance(l, dict)}

        # Complete line mapping for interactive line inspector
        final_lines = []
        for line_num, line_str in enumerate(raw_lines, 1):
            clean_str = line_str.strip()
            if line_num in model_lines:
                entry = model_lines[line_num]
                entry['code'] = line_str
                final_lines.append(entry)
            elif not clean_str:
                final_lines.append({
                    'line_number': line_num,
                    'code': line_str,
                    'is_blank': True,
                    'what': 'Blank line for vertical spacing.',
                    'why': 'Separates logical blocks to improve visual readability.',
                    'example': '',
                    'connects': 'Surrounds adjacent code blocks.',
                    'what_if_changed': 'Removing this line has no effect on execution.'
                })
            elif clean_str in ('{', '}', ';', '};'):
                final_lines.append({
                    'line_number': line_num,
                    'code': line_str,
                    'is_structural': True,
                    'what': f"Structural delimiter '{clean_str}' marking block boundaries.",
                    'why': 'Defines scope and body enclosing statements for the compiler/interpreter.',
                    'example': '',
                    'connects': 'Pairs with opening or closing block statements.',
                    'what_if_changed': 'Removing or altering this delimiter causes a fatal syntax or compiler error.'
                })
            else:
                final_lines.append({
                    'line_number': line_num,
                    'code': line_str,
                    'what': f"Statement: {clean_str}",
                    'why': 'Part of function execution sequence.',
                    'example': '',
                    'connects': 'Executes sequentially.',
                    'what_if_changed': 'Altering this statement modifies state flow.'
                })

        return {
            'success': True,
            'duration_seconds': total_duration,
            'retrieval_duration_seconds': retrieval_duration,
            'generation_duration_seconds': generation_duration,
            'summary': parsed.get('summary', 'Code analysis complete.'),
            'execution_flow': parsed.get('execution_flow', []),
            'lines': final_lines,
            'trace': parsed.get('trace', {}),
            'concepts': parsed.get('concepts', []),
            'improvement': parsed.get('improvement', {}),
            'evidence_trail': {
                'has_evidence': evidence_data['has_evidence'],
                'message': evidence_data['message'],
                'passages': evidence_data['passages'],
                'search_query': search_query
            }
        }

    except Exception as e:
        generation_duration = round(time.time() - t_gen_start, 2)
        total_duration = round(retrieval_duration + generation_duration, 2)
        logger.error(f"Error calling Gemini in Learn Mode after {total_duration}s: {e}")
        classified_type, user_msg = classify_gemini_error(e)
        return {
            'success': False,
            'duration_seconds': total_duration,
            'retrieval_duration_seconds': retrieval_duration,
            'generation_duration_seconds': generation_duration,
            'error_type': classified_type,
            'error': user_msg,
            'evidence_trail': {
                'has_evidence': evidence_data['has_evidence'],
                'message': evidence_data['message'],
                'passages': evidence_data['passages'],
                'search_query': search_query
            }
        }


def analyze_bug_dna(code: str, language: str = 'python', problem_description: str = '') -> Dict[str, Any]:
    """
    Debug Mode (Bug DNA):
    - Retrieves real evidence from indexed docs
    - Identifies root cause vs symptom
    - Suggests minimal correction
    - Validates correction using safe AST static analysis
    - Distinguishes documentation claims, AI suggestions, and unverified claims
    """
    if not code or not code.strip():
        return {
            'success': False,
            'error_type': 'EMPTY_INPUT',
            'error': 'Please provide code to debug.'
        }

    client, err_type, err_msg = get_gemini_client()
    if not client:
        static_check = verify_code(code, language)
        return {
            'success': False,
            'error_type': err_type or 'API_KEY_MISSING',
            'error': err_msg or 'GEMINI_API_KEY is not configured in .env. (Static AST verification was performed below).',
            'static_check': static_check
        }

    # Step 1: Semantic Retrieval (Real RAG)
    t_retrieval_start = time.time()
    search_query = f"{language} {problem_description} {code[:250]}".strip()
    evidence_data = retrieve_evidence(search_query, top_k=3, score_threshold=0.65)
    retrieval_duration = round(time.time() - t_retrieval_start, 2)

    evidence_context = ""
    if evidence_data['has_evidence']:
        evidence_context = "SUPPORTING DOCUMENTATION PASSAGES RETRIEVED FROM CORPUS:\n"
        for i, passage in enumerate(evidence_data['passages'], 1):
            evidence_context += f"[Passage {i}] File: {passage['filename']} (Page/Section {passage['page_number']}) (Relevance: {passage['similarity_score']}):\n"
            evidence_context += f"{passage['text']}\n\n"
    else:
        evidence_context = "NO DOCUMENTATION FOUND FOR THIS QUERY IN UPLOADED CORPUS.\n"

    lines = code.split('\n')
    numbered_code = "\n".join(f"{idx+1}: {line}" for idx, line in enumerate(lines))

    prompt = f"""You are Pramana Bug DNA, an expert debugging assistant.
Analyze the following {language} code and reported problem with strict technical accuracy.

CODE:
{numbered_code}

USER REPORTED PROBLEM:
{problem_description or "None provided. Analyze for syntax errors, logic bugs, or runtime exceptions."}

{evidence_context}

CRITICAL RULES:
1. Distinguish clearly between the visible symptom and the underlying root cause.
2. Suggest the minimal, cleanest correction.
3. If documentation passages are provided above, explicitly ground your explanation in them and cite the exact file and page.
4. Categorize claims honestly into:
   - documentation_claims: rules/facts strictly verified by the uploaded passages.
   - ai_suggestions: general AI reasoning and best practices.
   - unverified_claims: potential runtime edge cases or assumptions that require dynamic testing.
5. NEVER claim a fix is guaranteed or runtime-tested; label it as a static suggestion.

Return your response as STRICT JSON matching this exact structure:
{{
  "visible_symptom": "The visible error message or incorrect output behavior.",
  "root_cause": "The actual underlying flaw causing the bug.",
  "error_type": "Specific error category (e.g. IndexError, Off-by-One, TypeError, Infinite Loop, NoneType Attribute)",
  "affected_line_number": 1,
  "affected_expression": "The specific token or expression that causes the issue.",
  "why_occurs": "Clear explanation of why this bug occurs.",
  "likely_impact": "What happens if this bug remains in production.",
  "corrected_code": "The complete, corrected code snippet with the fix applied.",
  "change_summary": "Concise summary of what was modified.",
  "beginner_explanation": "Friendly, step-by-step explanation of the fix for a beginner student.",
  "documentation_claims": [
    "Fact or language rule supported by the uploaded docs with [Doc: filename, p. X]"
  ],
  "ai_suggestions": [
    "General AI advice and explanation"
  ],
  "unverified_claims": [
    "Claims that cannot be verified without running unit tests"
  ]
}}

Return ONLY valid JSON.
"""

    t_gen_start = time.time()
    try:
        model_name = os.getenv('GEMINI_MODEL', GEMINI_MODEL).strip() or 'gemini-3.1-flash-lite'
        response = call_gemini_with_retry(
            client,
            model=model_name,
            contents=prompt,
            thinking_budget=1024
        )
        generation_duration = round(time.time() - t_gen_start, 2)
        total_duration = round(retrieval_duration + generation_duration, 2)
        logger.info(f"Debug Mode generated in {total_duration}s (retrieval: {retrieval_duration}s, gen: {generation_duration}s) using {model_name}")

        raw_output = response.text if hasattr(response, 'text') else str(response)
        parsed = clean_json_response(raw_output)

        corrected_code = parsed.get('corrected_code', code)

        # Step 2: Fix Confidence Check (Safe Static Analysis)
        original_check = verify_code(code, language)
        fix_check = verify_code(corrected_code, language)

        # Build comparison verification report
        checks_list = []
        checks_list.append({
            'name': 'Original Code Static Check',
            'status': original_check['status'],
            'detail': original_check['verdict']
        })
        checks_list.append({
            'name': 'Corrected Code Static Check',
            'status': fix_check['status'],
            'detail': fix_check['verdict']
        })

        if fix_check['checks']:
            checks_list.extend(fix_check['checks'])

        overall_status = fix_check['status']

        return {
            'success': True,
            'duration_seconds': total_duration,
            'retrieval_duration_seconds': retrieval_duration,
            'generation_duration_seconds': generation_duration,
            'visible_symptom': parsed.get('visible_symptom', 'Unknown symptom'),
            'root_cause': parsed.get('root_cause', 'Unknown root cause'),
            'error_type': parsed.get('error_type', 'General Error'),
            'affected_line_number': parsed.get('affected_line_number', 1),
            'affected_expression': parsed.get('affected_expression', ''),
            'why_occurs': parsed.get('why_occurs', ''),
            'likely_impact': parsed.get('likely_impact', ''),
            'original_code': code,
            'corrected_code': corrected_code,
            'change_summary': parsed.get('change_summary', 'Applied suggested correction'),
            'beginner_explanation': parsed.get('beginner_explanation', ''),
            'documentation_claims': parsed.get('documentation_claims', []),
            'ai_suggestions': parsed.get('ai_suggestions', []),
            'unverified_claims': parsed.get('unverified_claims', []),
            'evidence_trail': {
                'has_evidence': evidence_data['has_evidence'],
                'message': evidence_data['message'],
                'passages': evidence_data['passages'],
                'search_query': search_query
            },
            'verification': {
                'status': overall_status,
                'verdict': fix_check['verdict'],
                'checks_run': checks_list,
                'warnings': fix_check.get('warnings', []),
                'errors': fix_check.get('errors', []),
                'disclaimer': fix_check.get('disclaimer', '')
            }
        }

    except Exception as e:
        generation_duration = round(time.time() - t_gen_start, 2)
        total_duration = round(retrieval_duration + generation_duration, 2)
        logger.error(f"Error calling Gemini in Debug Mode after {total_duration}s: {e}")
        classified_type, user_msg = classify_gemini_error(e)
        static_check = verify_code(code, language)
        return {
            'success': False,
            'duration_seconds': total_duration,
            'retrieval_duration_seconds': retrieval_duration,
            'generation_duration_seconds': generation_duration,
            'error_type': classified_type,
            'error': user_msg,
            'static_check': static_check,
            'evidence_trail': {
                'has_evidence': evidence_data['has_evidence'],
                'message': evidence_data['message'],
                'passages': evidence_data['passages'],
                'search_query': search_query
            }
        }
