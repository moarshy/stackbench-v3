"""
Hybrid retrieval combining keyword and vector search.

Implements Reciprocal Rank Fusion (RRF) to merge results from:
- KeywordRetrieval (fast, exact matches, deterministic)
- VectorRetrieval (semantic understanding, handles synonyms)

Provides best of both worlds: precision from keywords, recall from semantics.
"""

from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict
import logging

from stackbench.readme_llm.schemas import SearchResult
from stackbench.readme_llm.mcp_servers.retrieval.keyword_search import KeywordRetrieval

# Conditional import for vector search
try:
    from stackbench.readme_llm.mcp_servers.retrieval.vector_search import VectorRetrieval
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False

logger = logging.getLogger(__name__)


class HybridRetrieval:
    """
    Hybrid search combining keyword and semantic retrieval.

    Uses Reciprocal Rank Fusion (RRF) to combine rankings:
    - Keyword results: Fast, precise, good for exact API names
    - Vector results: Semantic, handles synonyms and paraphrases

    RRF formula: score(doc) = Σ 1 / (k + rank(doc))
    where k=60 is a constant (standard in literature)

    Example:
        >>> retrieval = HybridRetrieval(kb_path)
        >>> results = retrieval.search("connect to database", top_k=5)
        >>> for result in results:
        ...     print(f"{result.title}: {result.score}")
    """

    # RRF constant (standard value from research)
    RRF_K = 60

    # Fallback weights when vector search unavailable
    KEYWORD_ONLY_WEIGHT = 1.0

    def __init__(
        self,
        knowledge_base_path: Path,
        vector_model: Optional[str] = None,
        keyword_weight: float = 0.5,
        vector_weight: float = 0.5,
        enable_vector: bool = True,
    ):
        """
        Initialize hybrid retrieval system.

        Args:
            knowledge_base_path: Path to knowledge_base/ directory
            vector_model: Sentence-transformer model name (optional)
            keyword_weight: Weight for keyword results (0.0-1.0)
            vector_weight: Weight for vector results (0.0-1.0)
            enable_vector: Enable vector search (requires sentence-transformers)
        """
        self.kb_path = Path(knowledge_base_path)
        self.keyword_weight = keyword_weight
        self.vector_weight = vector_weight

        # Initialize keyword retrieval (always available)
        logger.info("Initializing keyword retrieval...")
        self.keyword_retrieval = KeywordRetrieval(self.kb_path)

        # Initialize vector retrieval (optional)
        self.vector_retrieval = None
        if enable_vector:
            if VECTOR_SEARCH_AVAILABLE:
                try:
                    logger.info("Initializing vector retrieval...")
                    self.vector_retrieval = VectorRetrieval(
                        self.kb_path,
                        model_name=vector_model
                    )
                    logger.info("Hybrid mode: keyword + vector")
                except Exception as e:
                    logger.warning(f"Failed to initialize vector retrieval: {e}")
                    logger.info("Falling back to keyword-only mode")
            else:
                logger.warning(
                    "sentence-transformers not available. "
                    "Install with: pip install sentence-transformers"
                )
                logger.info("Falling back to keyword-only mode")
        else:
            logger.info("Vector search disabled - keyword-only mode")

        # Adjust weights if vector not available
        if self.vector_retrieval is None:
            self.keyword_weight = self.KEYWORD_ONLY_WEIGHT
            self.vector_weight = 0.0

    def _reciprocal_rank_fusion(
        self,
        keyword_results: List[SearchResult],
        vector_results: List[SearchResult],
    ) -> List[SearchResult]:
        """
        Combine results using Reciprocal Rank Fusion.

        RRF score for each document:
        score = (keyword_weight / (k + keyword_rank)) + (vector_weight / (k + vector_rank))

        Args:
            keyword_results: Results from keyword search
            vector_results: Results from vector search

        Returns:
            Fused results sorted by RRF score
        """
        # Build rank maps
        keyword_ranks = {r.result_id: i + 1 for i, r in enumerate(keyword_results)}
        vector_ranks = {r.result_id: i + 1 for i, r in enumerate(vector_results)}

        # Collect all unique result IDs
        all_result_ids = set(keyword_ranks.keys()) | set(vector_ranks.keys())

        # Build result map (need full SearchResult objects)
        result_map = {}
        for r in keyword_results:
            result_map[r.result_id] = r
        for r in vector_results:
            if r.result_id not in result_map:
                result_map[r.result_id] = r

        # Calculate RRF scores
        rrf_scores = {}
        for result_id in all_result_ids:
            keyword_rank = keyword_ranks.get(result_id)
            vector_rank = vector_ranks.get(result_id)

            score = 0.0

            if keyword_rank is not None:
                score += self.keyword_weight / (self.RRF_K + keyword_rank)

            if vector_rank is not None:
                score += self.vector_weight / (self.RRF_K + vector_rank)

            rrf_scores[result_id] = score

        # Create fused results with RRF scores
        fused_results = []
        for result_id, rrf_score in rrf_scores.items():
            result = result_map[result_id]

            # Create new SearchResult with RRF score
            fused_result = SearchResult(
                result_type=result.result_type,
                result_id=result.result_id,
                title=result.title,
                description=result.description,
                score=rrf_score,
                language=result.language,
                metadata={
                    **result.metadata,
                    "fusion_method": "rrf",
                    "keyword_rank": keyword_ranks.get(result_id),
                    "vector_rank": vector_ranks.get(result_id),
                    "original_keyword_score": next(
                        (r.score for r in keyword_results if r.result_id == result_id),
                        None
                    ),
                    "original_vector_score": next(
                        (r.score for r in vector_results if r.result_id == result_id),
                        None
                    ),
                }
            )
            fused_results.append(fused_result)

        # Sort by RRF score
        fused_results.sort(key=lambda x: x.score, reverse=True)

        return fused_results

    def search_apis(
        self,
        query: str,
        language: Optional[str] = None,
        top_k: int = 10,
        min_importance: float = 0.0,
    ) -> List[SearchResult]:
        """
        Hybrid search for APIs.

        Args:
            query: Search query
            language: Filter by language (optional)
            top_k: Number of final results
            min_importance: Minimum importance score filter

        Returns:
            Fused search results
        """
        # Get keyword results (always available)
        keyword_results = self.keyword_retrieval.search_apis(
            query=query,
            language=language,
            top_k=top_k * 2,  # Get more for fusion
            min_importance=min_importance
        )

        # Get vector results (if available)
        vector_results = []
        if self.vector_retrieval is not None:
            vector_results = self.vector_retrieval.search_apis(
                query=query,
                language=language,
                top_k=top_k * 2,  # Get more for fusion
                min_importance=min_importance
            )

        # Fuse results
        if vector_results:
            fused_results = self._reciprocal_rank_fusion(keyword_results, vector_results)
        else:
            # Keyword-only mode
            fused_results = keyword_results

        return fused_results[:top_k]

    def search_examples(
        self,
        query: str,
        language: Optional[str] = None,
        complexity: Optional[str] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Hybrid search for examples.

        Args:
            query: Search query
            language: Filter by language (optional)
            complexity: Filter by complexity (beginner/intermediate/advanced)
            top_k: Number of final results

        Returns:
            Fused search results
        """
        # Get keyword results (always available)
        keyword_results = self.keyword_retrieval.search_examples(
            query=query,
            language=language,
            complexity=complexity,
            top_k=top_k * 2  # Get more for fusion
        )

        # Get vector results (if available)
        vector_results = []
        if self.vector_retrieval is not None:
            vector_results = self.vector_retrieval.search_examples(
                query=query,
                language=language,
                complexity=complexity,
                top_k=top_k * 2  # Get more for fusion
            )

        # Fuse results
        if vector_results:
            fused_results = self._reciprocal_rank_fusion(keyword_results, vector_results)
        else:
            # Keyword-only mode
            fused_results = keyword_results

        return fused_results[:top_k]

    def search(
        self,
        query: str,
        result_type: Optional[str] = None,
        language: Optional[str] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Unified hybrid search across APIs and examples.

        Args:
            query: Search query
            result_type: Filter by type ("api" or "example")
            language: Filter by language
            top_k: Total number of results

        Returns:
            Fused and sorted search results
        """
        results = []

        if result_type is None or result_type == "api":
            api_results = self.search_apis(query, language, top_k)
            results.extend(api_results)

        if result_type is None or result_type == "example":
            example_results = self.search_examples(query, language, top_k=top_k)
            results.extend(example_results)

        # Sort combined results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def compare_methods(
        self,
        query: str,
        result_type: Optional[str] = None,
        language: Optional[str] = None,
        top_k: int = 10,
    ) -> Dict:
        """
        Compare keyword, vector, and hybrid search results.

        Useful for debugging and understanding search quality.

        Args:
            query: Search query
            result_type: Filter by type
            language: Filter by language
            top_k: Number of results per method

        Returns:
            Dictionary with results from each method
        """
        comparison = {
            "query": query,
            "filters": {
                "result_type": result_type,
                "language": language,
            },
            "keyword_results": [],
            "vector_results": [],
            "hybrid_results": [],
        }

        # Keyword results
        if result_type is None or result_type == "api":
            comparison["keyword_results"] = self.keyword_retrieval.search_apis(
                query, language, top_k
            )
        elif result_type == "example":
            comparison["keyword_results"] = self.keyword_retrieval.search_examples(
                query, language, top_k=top_k
            )

        # Vector results (if available)
        if self.vector_retrieval is not None:
            if result_type is None or result_type == "api":
                comparison["vector_results"] = self.vector_retrieval.search_apis(
                    query, language, top_k
                )
            elif result_type == "example":
                comparison["vector_results"] = self.vector_retrieval.search_examples(
                    query, language, top_k=top_k
                )

        # Hybrid results
        comparison["hybrid_results"] = self.search(query, result_type, language, top_k)

        return comparison

    def get_api_details(self, api_id: str) -> Optional[Dict]:
        """Get full details for a specific API."""
        return self.keyword_retrieval.get_api_details(api_id)

    def get_example_details(self, example_id: str) -> Optional[Dict]:
        """Get full details for a specific example."""
        return self.keyword_retrieval.get_example_details(example_id)

    @property
    def is_hybrid_mode(self) -> bool:
        """Check if running in hybrid mode (keyword + vector)."""
        return self.vector_retrieval is not None

    @property
    def mode_description(self) -> str:
        """Get description of current search mode."""
        if self.is_hybrid_mode:
            return f"Hybrid (keyword: {self.keyword_weight}, vector: {self.vector_weight})"
        else:
            return "Keyword-only"
