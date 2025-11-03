"""Retrieval systems for README.LLM knowledge base."""

from .keyword_search import KeywordRetrieval
from .hybrid_search import HybridRetrieval

# Conditional import for vector search
try:
    from .vector_search import VectorRetrieval
    __all__ = [
        "KeywordRetrieval",
        "VectorRetrieval",
        "HybridRetrieval",
    ]
except ImportError:
    # sentence-transformers not available
    __all__ = [
        "KeywordRetrieval",
        "HybridRetrieval",
    ]
