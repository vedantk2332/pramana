"""
Pramana Real RAG Service:
- PDF (pypdf) & TXT text extraction with page/section tracking
- Text chunking with metadata preservation
- Embeddings generation via Gemini API
- Persistent FAISS vector storage
- Semantic similarity retrieval
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

from django.conf import settings

logger = logging.getLogger(__name__)

# Paths for vector index and metadata
VECTOR_DIR = getattr(settings, 'VECTOR_STORE_DIR', Path('data/vector_store'))
INDEX_FILE = VECTOR_DIR / 'faiss.index'
METADATA_FILE = VECTOR_DIR / 'chunks_metadata.json'
DOCUMENTS_FILE = VECTOR_DIR / 'documents.json'


from pramana.services.config import get_gemini_client, get_gemini_api_key, classify_gemini_error


class VectorStoreManager:
    """Manages persistent FAISS index and chunk metadata."""

    def __init__(self):
        self.index = None
        self.metadata: List[Dict[str, Any]] = []
        self.documents: List[Dict[str, Any]] = []
        self.dimension = None
        self.load_index()

    def load_index(self):
        """Loads FAISS index and metadata from disk if available."""
        VECTOR_DIR.mkdir(parents=True, exist_ok=True)
        
        if DOCUMENTS_FILE.exists():
            try:
                with open(DOCUMENTS_FILE, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
            except Exception as e:
                logger.error(f"Error loading documents record: {e}")
                self.documents = []

        if METADATA_FILE.exists():
            try:
                with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.error(f"Error loading chunk metadata: {e}")
                self.metadata = []

        if INDEX_FILE.exists() and faiss is not None:
            try:
                self.index = faiss.read_index(str(INDEX_FILE))
                self.dimension = self.index.d
            except Exception as e:
                logger.error(f"Error reading FAISS index: {e}")
                self.index = None

    def save_index(self):
        """Persists FAISS index and metadata to disk."""
        VECTOR_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)

        with open(DOCUMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, indent=2)

        if self.index is not None and faiss is not None:
            faiss.write_index(self.index, str(INDEX_FILE))

    def add_vectors(self, vectors: np.ndarray, chunks_meta: List[Dict[str, Any]], doc_info: Dict[str, Any]):
        """Adds normalized embedding vectors and their metadata."""
        if faiss is None:
            raise RuntimeError("FAISS is not installed or available.")
            
        dim = vectors.shape[1]
        if self.index is None or self.dimension != dim:
            # Inner Product index on L2-normalized vectors equals Cosine Similarity
            self.index = faiss.IndexFlatIP(dim)
            self.dimension = dim
            self.metadata = []
            
        # Ensure L2 normalization for cosine similarity
        faiss.normalize_L2(vectors)
        self.index.add(vectors)
        self.metadata.extend(chunks_meta)
        
        # Track document
        existing = [d for d in self.documents if d['filename'] == doc_info['filename']]
        if not existing:
            self.documents.append(doc_info)
        else:
            existing[0].update(doc_info)
            
        self.save_index()

    def ensure_loaded(self):
        """Ensures index and metadata are loaded from disk if available."""
        if (self.index is None or not self.metadata) and INDEX_FILE.exists():
            self.load_index()

    def search(self, query_vector: np.ndarray, top_k: int = 4, score_threshold: float = 0.65) -> List[Dict[str, Any]]:
        """
        Searches the FAISS index for top_k nearest neighbors.
        Returns list of matching chunks with similarity scores.
        """
        self.ensure_loaded()
        if self.index is None or self.index.ntotal == 0:
            return []

        # Normalize query vector
        query_copy = query_vector.copy().astype('float32')
        faiss.normalize_L2(query_copy)

        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query_copy, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            sim_score = float(score)
            if sim_score >= score_threshold:
                match = dict(self.metadata[idx])
                match['similarity_score'] = round(sim_score, 4)
                results.append(match)

        return results

    def clear(self):
        """Clears all vectors, metadata, and files."""
        self.index = None
        self.metadata = []
        self.documents = []
        self.dimension = None
        if INDEX_FILE.exists():
            INDEX_FILE.unlink(missing_ok=True)
        if METADATA_FILE.exists():
            METADATA_FILE.unlink(missing_ok=True)
        if DOCUMENTS_FILE.exists():
            DOCUMENTS_FILE.unlink(missing_ok=True)


# Singleton instance
store_manager = VectorStoreManager()


def extract_text_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extracts text preserving page numbers or section indices.
    Returns list of page items: [{'page_number': 1, 'text': '...'}]
    """
    ext = file_path.suffix.lower()
    pages_data = []

    if ext == '.pdf':
        if PdfReader is None:
            raise RuntimeError("pypdf is required to read PDF documents.")
        reader = PdfReader(str(file_path))
        for page_idx, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ''
            clean = text.strip()
            if clean:
                pages_data.append({
                    'page_number': page_idx,
                    'text': clean
                })
    elif ext in ('.txt', '.md', '.py', '.js', '.json', '.html', '.css', '.rst'):
        # Text based programming docs
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = file_path.read_text(encoding='latin-1', errors='replace')
            
        clean = content.strip()
        if clean:
            # If large text, split into simulated page sections (every ~3000 chars)
            section_len = 3000
            for i in range(0, len(clean), section_len):
                section_text = clean[i:i + section_len].strip()
                if section_text:
                    pages_data.append({
                        'page_number': (i // section_len) + 1,
                        'text': section_text
                    })
    else:
        raise ValueError(f"Unsupported file format: {ext}. Only PDF and TXT documentation are accepted.")

    return pages_data


def chunk_text(pages: List[Dict[str, Any]], filename: str, chunk_size: int = 650, chunk_overlap: int = 120) -> List[Dict[str, Any]]:
    """
    Chunks extracted pages with metadata preservation.
    """
    chunks = []
    chunk_counter = 0

    for p in pages:
        page_num = p['page_number']
        text = p['text']
        
        if len(text) <= chunk_size:
            chunks.append({
                'filename': filename,
                'page_number': page_num,
                'chunk_index': chunk_counter,
                'text': text
            })
            chunk_counter += 1
            continue

        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_str = text[start:end].strip()
            if chunk_str:
                chunks.append({
                    'filename': filename,
                    'page_number': page_num,
                    'chunk_index': chunk_counter,
                    'text': chunk_str
                })
                chunk_counter += 1
            start += (chunk_size - chunk_overlap)

    return chunks


def generate_embeddings_gemini(texts: List[str]) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """
    Generates embeddings using Gemini API (gemini-embedding-001 or gemini-embedding-2).
    Returns (numpy_matrix, error_message).
    """
    client, err_type, err_msg = get_gemini_client()
    if not client:
        return None, err_msg or "GEMINI_API_KEY is not configured in .env."

    embedding_model = os.getenv('GEMINI_EMBEDDING_MODEL', 'gemini-embedding-001').strip()
    
    all_vectors = []
    # Batch embeddings to avoid rate limits
    batch_size = 10
    try:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text_item in batch:
                res = client.models.embed_content(
                    model=embedding_model,
                    contents=text_item
                )
                if hasattr(res, 'embeddings') and res.embeddings:
                    emb = res.embeddings[0].values
                elif hasattr(res, 'embedding') and res.embedding:
                    emb = res.embedding.values
                else:
                    return None, "Unexpected embedding response structure from Gemini API."
                all_vectors.append(emb)

        arr = np.array(all_vectors, dtype='float32')
        return arr, None
    except Exception as e:
        logger.error(f"Gemini embedding error: {e}")
        _, user_msg = classify_gemini_error(e)
        return None, f"Embedding generation failed: {user_msg}"


def index_document(file_path: Path, original_filename: str) -> Dict[str, Any]:
    """
    Full pipeline: Extract -> Chunk -> Embed -> FAISS Index.
    """
    # 1. Extraction
    try:
        pages = extract_text_from_file(file_path)
    except Exception as e:
        return {'success': False, 'error': f"Extraction error: {str(e)}"}

    if not pages:
        return {'success': False, 'error': "Document contains no extractable text."}

    # 2. Chunking
    chunks = chunk_text(pages, original_filename)
    if not chunks:
        return {'success': False, 'error': "No text chunks generated from document."}

    # 3. Embedding
    texts_to_embed = [c['text'] for c in chunks]
    vectors, err = generate_embeddings_gemini(texts_to_embed)
    if err or vectors is None:
        return {'success': False, 'error': err or 'Failed to generate embeddings.'}

    # 4. Vector store indexing
    doc_info = {
        'filename': original_filename,
        'pages_count': len(pages),
        'chunks_count': len(chunks),
        'file_size_bytes': file_path.stat().st_size
    }
    
    try:
        store_manager.add_vectors(vectors, chunks, doc_info)
    except Exception as e:
        return {'success': False, 'error': f"FAISS storage error: {str(e)}"}

    return {
        'success': True,
        'filename': original_filename,
        'pages_extracted': len(pages),
        'chunks_indexed': len(chunks),
        'total_indexed_chunks': len(store_manager.metadata),
        'total_documents': len(store_manager.documents)
    }


def retrieve_evidence(query: str, top_k: int = 4, score_threshold: float = 0.65) -> Dict[str, Any]:
    """
    Constructs query embedding and retrieves relevant document chunks from persistent FAISS index.
    Honest reporting: returns has_evidence=False if no documents or below relevance threshold.
    Tracks retrieval_duration_seconds separately from LLM generation time.
    """
    import time
    t_start = time.time()
    store_manager.ensure_loaded()

    if store_manager.index is None or store_manager.index.ntotal == 0:
        return {
            'has_evidence': False,
            'retrieval_duration_seconds': round(time.time() - t_start, 2),
            'message': 'No documentation has been uploaded or indexed yet. Explanations will rely on general model knowledge.',
            'passages': []
        }

    client, err_type, err_msg = get_gemini_client()
    if not client:
        return {
            'has_evidence': False,
            'retrieval_duration_seconds': round(time.time() - t_start, 2),
            'message': err_msg or 'GEMINI_API_KEY is missing. Semantic retrieval requires a valid Gemini API key.',
            'passages': []
        }

    embedding_model = os.getenv('GEMINI_EMBEDDING_MODEL', 'gemini-embedding-001').strip()
    try:
        res = client.models.embed_content(
            model=embedding_model,
            contents=query
        )
        if hasattr(res, 'embeddings') and res.embeddings:
            query_vector = np.array([res.embeddings[0].values], dtype='float32')
        elif hasattr(res, 'embedding') and res.embedding:
            query_vector = np.array([res.embedding.values], dtype='float32')
        else:
            return {
                'has_evidence': False,
                'retrieval_duration_seconds': round(time.time() - t_start, 2),
                'message': 'Unable to parse query embedding vector.',
                'passages': []
            }
    except Exception as e:
        _, user_msg = classify_gemini_error(e)
        return {
            'has_evidence': False,
            'retrieval_duration_seconds': round(time.time() - t_start, 2),
            'message': f"Query embedding generation error: {user_msg}",
            'passages': []
        }

    # Perform FAISS search
    matches = store_manager.search(query_vector, top_k=top_k, score_threshold=score_threshold)
    duration = round(time.time() - t_start, 2)

    if not matches:
        return {
            'has_evidence': False,
            'retrieval_duration_seconds': duration,
            'message': f"No matching passages in the uploaded corpus met the relevance threshold ({score_threshold}). General AI reasoning will be used.",
            'passages': []
        }

    return {
        'has_evidence': True,
        'retrieval_duration_seconds': duration,
        'message': f"Retrieved {len(matches)} supporting documentation passage(s) with semantic vector search.",
        'passages': matches
    }
