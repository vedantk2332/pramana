"""
Pramana Central Configuration & Gemini Environment Utilities.
Provides robust absolute-path .env resolution, safe diagnostics, and client lifecycle.
SECURITY NOTICE: Never log, print, or expose the actual API key value.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv
from django.conf import settings

logger = logging.getLogger(__name__)

def get_env_file_path() -> Path:
    """Returns the absolute path to the project root .env file."""
    if hasattr(settings, 'BASE_DIR'):
        return Path(settings.BASE_DIR) / '.env'
    return Path(__file__).resolve().parent.parent.parent / '.env'


def get_gemini_api_key(force_reload: bool = False) -> str:
    """
    Safely retrieves the GEMINI_API_KEY.
    If the key is missing from memory or force_reload is True, reloads the root .env file.
    Guarantees no stale cached empty values across requests.
    """
    key = os.getenv('GEMINI_API_KEY', '').strip()
    placeholder = 'your_gemini_api_key_here'

    # If key is empty or is placeholder, or reload requested, attempt fresh load from .env
    if not key or key == placeholder or force_reload:
        env_path = get_env_file_path()
        if env_path.exists():
            load_dotenv(env_path, override=True)
            key = os.getenv('GEMINI_API_KEY', '').strip()

    if not key or key == placeholder:
        return ''
    return key


def get_api_key_diagnostic() -> Dict[str, Any]:
    """
    Safe diagnostic inspection.
    SECURITY: Reports only presence, length, and file existence. NEVER reveals key contents.
    """
    env_path = get_env_file_path()
    raw_env_key = ''
    if env_path.exists():
        load_dotenv(env_path, override=True)
        raw_env_key = os.getenv('GEMINI_API_KEY', '').strip()

    is_present = bool(raw_env_key and raw_env_key != 'your_gemini_api_key_here')
    is_placeholder = (raw_env_key == 'your_gemini_api_key_here')

    return {
        'env_file_exists': env_path.exists(),
        'env_file_path': str(env_path),
        'has_api_key': is_present,
        'key_length': len(raw_env_key) if is_present else 0,
        'is_placeholder': is_placeholder,
    }


_cached_client = None
_cached_key = None

def get_gemini_client() -> Tuple[Optional[Any], Optional[str], Optional[str]]:
    """
    Initializes or returns a cached authenticated google-genai Client.
    Reuses existing client across requests to eliminate connection handshake latency.
    Returns: (client, error_type, user_friendly_message)
    """
    global _cached_client, _cached_key
    key = get_gemini_api_key()
    if not key:
        return (
            None,
            'API_KEY_MISSING',
            'GEMINI_API_KEY is not configured in .env. Please add your API key from Google AI Studio to unlock live AI code explanation.'
        )

    if _cached_client is not None and _cached_key == key:
        return (_cached_client, None, None)

    try:
        from google import genai
        client = genai.Client(api_key=key)
        _cached_client = client
        _cached_key = key
        return (client, None, None)
    except Exception as e:
        logger.error(f"Error initializing Gemini client: {e}")
        return (
            None,
            'CLIENT_INIT_ERROR',
            f'Failed to initialize Gemini SDK client: {str(e)}'
        )


def classify_gemini_error(e: Exception) -> Tuple[str, str]:
    """
    Classifies Gemini API exceptions into clear, helpful user error messages.
    Distinguishes invalid keys, quota limits, model not found, and network issues.
    """
    err_str = str(e).lower()
    err_type_name = type(e).__name__

    if 'api_key_invalid' in err_str or 'api key not valid' in err_str or 'unauthenticated' in err_str or '401' in err_str or '403' in err_str:
        return (
            'API_KEY_INVALID',
            'The configured GEMINI_API_KEY is invalid or has expired. Please verify your API key in Google AI Studio (https://aistudio.google.com/).'
        )
    elif 'quota' in err_str or 'resource_exhausted' in err_str or '429' in err_str or 'rate limit' in err_str:
        return (
            'QUOTA_EXCEEDED',
            'Gemini API rate limit or quota exceeded. Please wait a moment before sending another request.'
        )
    elif 'not_found' in err_str or '404' in err_str or 'not found' in err_str:
        return (
            'MODEL_NOT_FOUND',
            'The configured model was not found or is discontinued. Pramana uses gemini-3.8-flash as the active production model.'
        )
    elif 'connection' in err_str or 'timeout' in err_str or 'network' in err_str or 'dns' in err_str:
        return (
            'NETWORK_ERROR',
            'Network connectivity error while reaching the Google Gemini API. Please check your internet connection.'
        )
    elif '503' in err_str or 'unavailable' in err_str or 'high demand' in err_str or 'overloaded' in err_str:
        return (
            'SERVICE_BUSY',
            'Google Gemini service is temporarily experiencing high demand. Please retry your request in a few moments.'
        )
    else:
        return (
            'AI_SERVICE_ERROR',
            f'Gemini API request failed ({err_type_name}): {str(e)}'
        )
