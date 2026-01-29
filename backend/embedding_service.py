"""
Embedding service for semantic matching of DCT questions to manual sections.

Uses sentence-transformers for local, zero-cost semantic embeddings.
"""

import logging
from typing import List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Lazy load sentence-transformers to avoid startup delay
_model = None
_model_name = None


def get_model(model_name: str = 'all-MiniLM-L6-v2'):
    """
    Get or initialize the embedding model (lazy loading).

    Args:
        model_name: Name of the sentence-transformers model to use.
                   Default is 'all-MiniLM-L6-v2' (~80MB, fast, good quality).

    Returns:
        SentenceTransformer model instance.
    """
    global _model, _model_name

    if _model is None or _model_name != model_name:
        logger.info(f"Loading embedding model: {model_name}")
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(model_name)
            _model_name = model_name
            logger.info(f"Embedding model loaded successfully")
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise ImportError("sentence-transformers is required for semantic matching. "
                            "Install with: pip install sentence-transformers")

    return _model


class EmbeddingService:
    """
    Service for generating and comparing text embeddings.

    Uses sentence-transformers to convert text into semantic vectors
    that can be compared for similarity.
    """

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the embedding service.

        Args:
            model_name: Name of the sentence-transformers model.
                       Options:
                       - 'all-MiniLM-L6-v2': Fast, small (~80MB), good quality (default)
                       - 'all-mpnet-base-v2': Slower, larger (~420MB), best quality
                       - 'paraphrase-MiniLM-L6-v2': Good for paraphrase detection
        """
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy load the model on first use."""
        if self._model is None:
            self._model = get_model(self.model_name)
        return self._model

    def embed_text(self, text: str) -> np.ndarray:
        """
        Convert text to a semantic vector (embedding).

        Args:
            text: The text to embed.

        Returns:
            Normalized embedding vector (384 dimensions for MiniLM).
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(384)

        # Truncate very long text to avoid memory issues
        max_length = 8000  # Characters, roughly 2000 tokens
        if len(text) > max_length:
            text = text[:max_length]

        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding

    def embed_batch(self, texts: List[str], show_progress: bool = False) -> np.ndarray:
        """
        Batch embed multiple texts efficiently.

        Args:
            texts: List of texts to embed.
            show_progress: Whether to show progress bar.

        Returns:
            Array of embeddings, shape (len(texts), embedding_dim).
        """
        if not texts:
            return np.array([])

        # Handle empty strings
        processed_texts = []
        for text in texts:
            if not text or not text.strip():
                processed_texts.append(" ")  # Use space for empty
            elif len(text) > 8000:
                processed_texts.append(text[:8000])
            else:
                processed_texts.append(text)

        embeddings = self.model.encode(
            processed_texts,
            normalize_embeddings=True,
            show_progress_bar=show_progress
        )
        return embeddings

    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector.
            embedding2: Second embedding vector.

        Returns:
            Similarity score between 0 and 1 (1 = identical meaning).
        """
        # Since embeddings are normalized, dot product = cosine similarity
        return float(np.dot(embedding1, embedding2))

    def find_most_similar(self, query_embedding: np.ndarray,
                          candidate_embeddings: np.ndarray,
                          top_k: int = 5) -> List[Tuple[int, float]]:
        """
        Find the most similar candidates to a query.

        Args:
            query_embedding: The query embedding vector.
            candidate_embeddings: Array of candidate embeddings.
            top_k: Number of top results to return.

        Returns:
            List of (index, similarity_score) tuples, sorted by similarity.
        """
        if len(candidate_embeddings) == 0:
            return []

        # Compute all similarities at once (fast matrix multiplication)
        similarities = np.dot(candidate_embeddings, query_embedding)

        # Get top-k indices
        if len(similarities) <= top_k:
            top_indices = np.argsort(similarities)[::-1]
        else:
            top_indices = np.argpartition(similarities, -top_k)[-top_k:]
            top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

        return [(int(idx), float(similarities[idx])) for idx in top_indices]


def build_question_intent_text(question) -> str:
    """
    Build comprehensive text capturing the intent of a DCT question.

    This text is used to generate an embedding that represents what
    the question is really asking for - what evidence or documentation
    would satisfy this compliance check.

    Args:
        question: Question model instance or dict with question data.

    Returns:
        Combined text representing the question's intent.
    """
    parts = []

    # Handle both model objects and dicts
    if hasattr(question, 'question_text_full'):
        # Model object
        question_text = question.question_text_full
        guidance = question.data_collection_guidance
        cfr_list = question.reference_cfr_list or []
        faa_list = question.reference_faa_guidance_list or []
        notes = question.notes or []
    else:
        # Dict
        question_text = question.get('Question_Text_Full', '')
        guidance = question.get('Data_Collection_Guidance', '')
        cfr_list = question.get('Reference_CFR_List', [])
        faa_list = question.get('Reference_FAA_Guidance_List', [])
        notes = question.get('Notes', [])

    # Core question text
    if question_text:
        parts.append(question_text)

    # Data collection guidance tells us what evidence is needed
    if guidance:
        parts.append(f"Evidence needed: {guidance}")

    # CFR references indicate regulatory requirements
    if cfr_list:
        cfrs = ', '.join(cfr_list) if isinstance(cfr_list, list) else cfr_list
        parts.append(f"Must comply with: {cfrs}")

    # FAA guidance references
    if faa_list:
        guidance_refs = ', '.join(faa_list) if isinstance(faa_list, list) else faa_list
        parts.append(f"Referenced guidance: {guidance_refs}")

    # Notes may contain additional context
    if notes:
        notes_text = ' '.join(notes) if isinstance(notes, list) else notes
        if notes_text.strip():
            parts.append(f"Additional context: {notes_text}")

    return ' '.join(parts)


def build_section_content_text(section) -> str:
    """
    Build comprehensive text capturing what a manual section covers.

    This text is used to generate an embedding that represents the
    section's content and regulatory coverage.

    Args:
        section: ManualSection model instance or dict with section data.

    Returns:
        Combined text representing the section's coverage.
    """
    parts = []

    # Handle both model objects and dicts
    if hasattr(section, 'section_number'):
        # Model object
        section_number = section.section_number
        section_title = section.section_title
        section_text = section.section_text
        cfr_citations = section.cfr_citations or []
    else:
        # Dict
        section_number = section.get('section_number', '')
        section_title = section.get('section_title', '')
        section_text = section.get('section_text', '')
        cfr_citations = section.get('cfr_citations', [])

    # Section identity
    if section_number and section_title:
        parts.append(f"Section {section_number}: {section_title}")
    elif section_title:
        parts.append(section_title)
    elif section_number:
        parts.append(f"Section {section_number}")

    # Full content
    if section_text:
        parts.append(section_text)

    # Regulatory coverage
    if cfr_citations:
        cfrs = ', '.join(cfr_citations) if isinstance(cfr_citations, list) else cfr_citations
        parts.append(f"Addresses compliance with: {cfrs}")

    return ' '.join(parts)


def embedding_to_bytes(embedding: np.ndarray) -> bytes:
    """Convert numpy embedding to bytes for database storage."""
    return embedding.tobytes()


def bytes_to_embedding(data: bytes, dtype=np.float32) -> np.ndarray:
    """Convert bytes back to numpy embedding."""
    return np.frombuffer(data, dtype=dtype)


# Singleton instance for convenience
_embedding_service = None


def get_embedding_service(model_name: str = 'all-MiniLM-L6-v2') -> EmbeddingService:
    """Get or create the singleton embedding service."""
    global _embedding_service

    if _embedding_service is None or _embedding_service.model_name != model_name:
        _embedding_service = EmbeddingService(model_name)

    return _embedding_service
