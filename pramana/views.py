"""
Pramana Application Views & REST Endpoints.
"""

import json
import os
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings

from pramana.services.ai_service import explain_code_line_by_line, analyze_bug_dna
from pramana.services.config import get_gemini_client, get_gemini_api_key, get_api_key_diagnostic
from pramana.services.rag_service import index_document, retrieve_evidence, store_manager
from pramana.services.verification_service import verify_code
from pramana.services.game_data import get_all_challenges, validate_game_answer, GAMES_CONFIG


def index_view(request):
    """Renders the main single-page application dashboard."""
    diag = get_api_key_diagnostic()
    has_api_key = diag['has_api_key']
    context = {
        'has_api_key': has_api_key,
        'gemini_model': os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite'),
        'embedding_model': os.getenv('GEMINI_EMBEDDING_MODEL', 'gemini-embedding-001'),
        'total_docs': len(store_manager.documents),
        'total_chunks': len(store_manager.metadata),
    }
    return render(request, 'pramana/index.html', context)


@require_GET
def system_status_view(request):
    """Returns system configuration and service health with safe diagnostic."""
    diag = get_api_key_diagnostic()
    has_api_key = diag['has_api_key']
    return JsonResponse({
        'status': 'healthy',
        'has_api_key': has_api_key,
        'diagnostic': {
            'env_file_exists': diag['env_file_exists'],
            'has_api_key': diag['has_api_key'],
            'key_length': diag['key_length'],
            'is_placeholder': diag['is_placeholder']
        },
        'gemini_model': os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite'),
        'embedding_model': os.getenv('GEMINI_EMBEDDING_MODEL', 'gemini-embedding-001'),
        'total_documents': len(store_manager.documents),
        'total_indexed_chunks': len(store_manager.metadata),
        'vector_store_ready': store_manager.index is not None
    })


@csrf_exempt
@require_POST
def learn_explain_view(request):
    """Learn Mode: Line-by-line explanation of code."""
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON request payload.'}, status=400)

    code = body.get('code', '')
    language = body.get('language', 'python')

    if not code.strip():
        return JsonResponse({'success': False, 'error': 'No code provided.'}, status=400)

    result = explain_code_line_by_line(code, language)
    return JsonResponse(result)


@csrf_exempt
@require_POST
def debug_analyze_view(request):
    """Debug Mode: Bug DNA analysis, Fix Confidence check, and Evidence Trail."""
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON request payload.'}, status=400)

    code = body.get('code', '')
    language = body.get('language', 'python')
    problem_description = body.get('problem_description', '')

    if not code.strip():
        return JsonResponse({'success': False, 'error': 'No code provided.'}, status=400)

    result = analyze_bug_dna(code, language, problem_description)
    return JsonResponse(result)


@csrf_exempt
@require_POST
def verify_code_view(request):
    """Direct static AST verification without executing user code."""
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON request payload.'}, status=400)

    code = body.get('code', '')
    language = body.get('language', 'python')

    result = verify_code(code, language)
    return JsonResponse({'success': True, 'verification': result})


@csrf_exempt
@require_POST
def rag_upload_view(request):
    """Uploads and indexes PDF or TXT programming documentation."""
    if 'document' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No document file provided.'}, status=400)

    uploaded_file = request.FILES['document']
    orig_name = uploaded_file.name
    ext = Path(orig_name).suffix.lower()

    if ext not in ('.pdf', '.txt', '.md', '.py', '.js', '.rst'):
        return JsonResponse({
            'success': False,
            'error': f'Unsupported file type: {ext}. Only PDF and text programming documentation are accepted.'
        }, status=400)

    # Enforce size limit (15 MB)
    if uploaded_file.size > 15 * 1024 * 1024:
        return JsonResponse({'success': False, 'error': 'File exceeds maximum 15MB limit.'}, status=400)

    # Save to uploads dir
    dest_path = settings.UPLOADS_DIR / orig_name
    try:
        with open(dest_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'File write failed: {str(e)}'}, status=500)

    # Run RAG Indexing Pipeline
    index_result = index_document(dest_path, orig_name)
    return JsonResponse(index_result)


@require_GET
def rag_documents_view(request):
    """Returns list of indexed documents and chunk statistics."""
    return JsonResponse({
        'success': True,
        'documents': store_manager.documents,
        'total_documents': len(store_manager.documents),
        'total_indexed_chunks': len(store_manager.metadata)
    })


@csrf_exempt
@require_POST
def rag_clear_view(request):
    """Clears the indexed vector store."""
    store_manager.clear()
    return JsonResponse({
        'success': True,
        'message': 'Vector store and indexed documents cleared successfully.'
    })


@csrf_exempt
@require_POST
def rag_query_view(request):
    """Tests semantic vector search on indexed documentation."""
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON request payload.'}, status=400)

    query = body.get('query', '')
    if not query.strip():
        return JsonResponse({'success': False, 'error': 'Search query is required.'}, status=400)

    evidence = retrieve_evidence(query, top_k=5, score_threshold=0.65)
    return JsonResponse({'success': True, 'evidence': evidence})


@require_GET
def games_list_view(request):
    """Returns all available Game Mode challenges and metadata."""
    challenges = get_all_challenges()
    return JsonResponse({
        'success': True,
        'games_config': GAMES_CONFIG,
        'challenges': challenges,
        'total_challenges': len(challenges)
    })


@csrf_exempt
@require_POST
def games_check_view(request):
    """Checks user submitted game answer, returns explanation and XP."""
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON request payload.'}, status=400)

    challenge_id = body.get('challenge_id', '')
    user_answer = body.get('answer', '')

    if not challenge_id or not user_answer:
        return JsonResponse({'success': False, 'error': 'Challenge ID and answer are required.'}, status=400)

    result = validate_game_answer(challenge_id, user_answer)
    return JsonResponse(result)
