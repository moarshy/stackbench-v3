"""MCP servers for README.LLM system."""

from .documentor_server import DocuMentorServer
from .feedback_analyzer import FeedbackAnalyzer
from .retrieval import KeywordRetrieval, HybridRetrieval

# Conditional import for vector search
try:
    from .retrieval import VectorRetrieval
    __all__ = [
        "DocuMentorServer",
        "FeedbackAnalyzer",
        "KeywordRetrieval",
        "VectorRetrieval",
        "HybridRetrieval",
    ]
except ImportError:
    # sentence-transformers not available
    __all__ = [
        "DocuMentorServer",
        "FeedbackAnalyzer",
        "KeywordRetrieval",
        "HybridRetrieval",
    ]
