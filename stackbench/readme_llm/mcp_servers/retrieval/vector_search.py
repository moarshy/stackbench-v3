"""
Vector-based semantic retrieval for README.LLM knowledge base.

Implements semantic search using sentence-transformers embeddings and cosine similarity.
Provides deeper understanding of query intent beyond keyword matching.
"""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import logging
import numpy as np

from stackbench.readme_llm.schemas import SearchResult

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available. Install with: pip install sentence-transformers")


class VectorRetrieval:
    """
    Semantic search using sentence-transformers embeddings.

    Features:
    - Deep semantic understanding via embeddings
    - Cosine similarity ranking
    - Embedding caching for performance
    - Batch processing
    - Multiple model support

    Example:
        >>> retrieval = VectorRetrieval(kb_path, model_name="all-MiniLM-L6-v2")
        >>> results = retrieval.search("connect to database", top_k=5)
        >>> for result in results:
        ...     print(f"{result.title}: {result.score}")
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"  # Fast, good quality, 384 dimensions

    # Alternative models:
    # "all-mpnet-base-v2" - Highest quality, 768 dimensions, slower
    # "all-MiniLM-L12-v2" - Balanced, 384 dimensions
    # "paraphrase-MiniLM-L6-v2" - Fast, 384 dimensions

    def __init__(
        self,
        knowledge_base_path: Path,
        model_name: Optional[str] = None,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize vector retrieval system.

        Args:
            knowledge_base_path: Path to knowledge_base/ directory
            model_name: Sentence-transformers model name (default: all-MiniLM-L6-v2)
            cache_dir: Directory to cache embeddings (default: kb_path/../embeddings/)
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required for vector search. "
                "Install with: pip install sentence-transformers"
            )

        self.kb_path = Path(knowledge_base_path)
        self.model_name = model_name or self.DEFAULT_MODEL

        # Load knowledge base structure
        self.index = self._load_index()
        self.library_overview = self._load_library_overview()

        # Set up cache directory
        if cache_dir is None:
            cache_dir = self.kb_path.parent / "embeddings"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load sentence-transformer model
        logger.info(f"Loading sentence-transformer model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

        # Data structures
        self.api_data: Dict[str, Dict] = {}  # {api_id: full_data}
        self.example_data: Dict[str, Dict] = {}  # {example_id: full_data}

        # Embeddings
        self.api_embeddings: Optional[np.ndarray] = None  # (n_apis, embedding_dim)
        self.example_embeddings: Optional[np.ndarray] = None  # (n_examples, embedding_dim)
        self.api_ids: List[str] = []  # API IDs in same order as embeddings
        self.example_ids: List[str] = []  # Example IDs in same order as embeddings

        # Build or load embeddings
        self._build_or_load_embeddings()

        logger.info(
            f"Initialized VectorRetrieval with {len(self.api_ids)} APIs, "
            f"{len(self.example_ids)} examples"
        )

    def _load_index(self) -> Dict:
        """Load master index.json"""
        index_path = self.kb_path / "index.json"
        if not index_path.exists():
            raise FileNotFoundError(f"Index not found: {index_path}")

        return json.loads(index_path.read_text(encoding='utf-8'))

    def _load_library_overview(self) -> Dict:
        """Load library_overview.json"""
        overview_path = self.kb_path / "library_overview.json"
        if not overview_path.exists():
            raise FileNotFoundError(f"Library overview not found: {overview_path}")

        return json.loads(overview_path.read_text(encoding='utf-8'))

    def _get_cache_path(self, cache_type: str) -> Path:
        """
        Get cache file path for embeddings.

        Args:
            cache_type: "apis" or "examples"

        Returns:
            Path to cache file
        """
        # Include model name in cache key
        model_slug = self.model_name.replace("/", "_")
        return self.cache_dir / f"{cache_type}_{model_slug}.pkl"

    def _build_or_load_embeddings(self):
        """
        Build embeddings from knowledge base or load from cache.

        Checks cache validity (same model, same KB version).
        """
        logger.info("Building or loading embeddings...")

        # Cache paths
        api_cache_path = self._get_cache_path("apis")
        example_cache_path = self._get_cache_path("examples")

        # Try to load from cache
        api_cache_valid = self._load_api_embeddings_from_cache(api_cache_path)
        example_cache_valid = self._load_example_embeddings_from_cache(example_cache_path)

        # Build missing embeddings
        if not api_cache_valid:
            logger.info("Building API embeddings...")
            self._build_api_embeddings()
            self._save_api_embeddings_to_cache(api_cache_path)
        else:
            logger.info("Loaded API embeddings from cache")

        if not example_cache_valid:
            logger.info("Building example embeddings...")
            self._build_example_embeddings()
            self._save_example_embeddings_to_cache(example_cache_path)
        else:
            logger.info("Loaded example embeddings from cache")

    def _load_api_embeddings_from_cache(self, cache_path: Path) -> bool:
        """
        Load API embeddings from cache.

        Returns:
            True if cache is valid and loaded successfully
        """
        if not cache_path.exists():
            return False

        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)

            # Validate cache
            if cache_data.get("model_name") != self.model_name:
                logger.info("Cache invalid: model name mismatch")
                return False

            # Load data
            self.api_embeddings = cache_data["embeddings"]
            self.api_ids = cache_data["api_ids"]
            self.api_data = cache_data["api_data"]

            return True

        except Exception as e:
            logger.warning(f"Failed to load API embeddings cache: {e}")
            return False

    def _load_example_embeddings_from_cache(self, cache_path: Path) -> bool:
        """
        Load example embeddings from cache.

        Returns:
            True if cache is valid and loaded successfully
        """
        if not cache_path.exists():
            return False

        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)

            # Validate cache
            if cache_data.get("model_name") != self.model_name:
                logger.info("Cache invalid: model name mismatch")
                return False

            # Load data
            self.example_embeddings = cache_data["embeddings"]
            self.example_ids = cache_data["example_ids"]
            self.example_data = cache_data["example_data"]

            return True

        except Exception as e:
            logger.warning(f"Failed to load example embeddings cache: {e}")
            return False

    def _build_api_embeddings(self):
        """Build embeddings for all APIs."""
        self.api_ids = []
        self.api_data = {}
        texts = []

        # Load all APIs
        for language, api_list in self.index.get("apis", {}).items():
            for api_meta in api_list:
                api_id = api_meta["api_id"]
                api_file = self.kb_path / api_meta["file"]

                if not api_file.exists():
                    logger.warning(f"API file not found: {api_file}")
                    continue

                api_data = json.loads(api_file.read_text(encoding='utf-8'))

                # Create searchable text for embedding
                text_parts = [
                    api_data.get("api_id", ""),
                    api_data.get("signature", ""),
                    api_data.get("description", ""),
                    " ".join(api_data.get("search_keywords", [])),
                ]
                text = " ".join(filter(None, text_parts))

                self.api_ids.append(api_id)
                self.api_data[api_id] = api_data
                texts.append(text)

        # Generate embeddings in batch
        if texts:
            logger.info(f"Encoding {len(texts)} API texts...")
            self.api_embeddings = self.model.encode(
                texts,
                batch_size=32,
                show_progress_bar=True,
                convert_to_numpy=True
            )
        else:
            self.api_embeddings = np.array([])

    def _build_example_embeddings(self):
        """Build embeddings for all examples."""
        self.example_ids = []
        self.example_data = {}
        texts = []

        # Load all examples
        for language, example_list in self.index.get("examples", {}).items():
            for example_meta in example_list:
                example_id = example_meta["example_id"]
                example_file = self.kb_path / example_meta["file"]

                if not example_file.exists():
                    logger.warning(f"Example file not found: {example_file}")
                    continue

                example_data = json.loads(example_file.read_text(encoding='utf-8'))

                # Create searchable text for embedding
                text_parts = [
                    example_data.get("title", ""),
                    example_data.get("use_case", ""),
                    " ".join(example_data.get("apis_used", [])),
                    # Optionally include code (can be noisy)
                    # example_data.get("code", "")[:500],  # First 500 chars
                ]
                text = " ".join(filter(None, text_parts))

                self.example_ids.append(example_id)
                self.example_data[example_id] = example_data
                texts.append(text)

        # Generate embeddings in batch
        if texts:
            logger.info(f"Encoding {len(texts)} example texts...")
            self.example_embeddings = self.model.encode(
                texts,
                batch_size=32,
                show_progress_bar=True,
                convert_to_numpy=True
            )
        else:
            self.example_embeddings = np.array([])

    def _save_api_embeddings_to_cache(self, cache_path: Path):
        """Save API embeddings to cache."""
        try:
            cache_data = {
                "model_name": self.model_name,
                "embeddings": self.api_embeddings,
                "api_ids": self.api_ids,
                "api_data": self.api_data,
            }

            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)

            logger.info(f"Saved API embeddings cache: {cache_path}")

        except Exception as e:
            logger.warning(f"Failed to save API embeddings cache: {e}")

    def _save_example_embeddings_to_cache(self, cache_path: Path):
        """Save example embeddings to cache."""
        try:
            cache_data = {
                "model_name": self.model_name,
                "embeddings": self.example_embeddings,
                "example_ids": self.example_ids,
                "example_data": self.example_data,
            }

            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)

            logger.info(f"Saved example embeddings cache: {cache_path}")

        except Exception as e:
            logger.warning(f"Failed to save example embeddings cache: {e}")

    def _cosine_similarity(self, query_embedding: np.ndarray, doc_embeddings: np.ndarray) -> np.ndarray:
        """
        Calculate cosine similarity between query and documents.

        Args:
            query_embedding: Query embedding (1D array)
            doc_embeddings: Document embeddings (2D array: n_docs × embedding_dim)

        Returns:
            Similarity scores (1D array: n_docs)
        """
        # Normalize vectors
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        doc_norms = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)

        # Cosine similarity = dot product of normalized vectors
        similarities = np.dot(doc_norms, query_norm)

        return similarities

    def search_apis(
        self,
        query: str,
        language: Optional[str] = None,
        top_k: int = 10,
        min_importance: float = 0.0,
        min_similarity: float = 0.0
    ) -> List[SearchResult]:
        """
        Search for APIs using semantic similarity.

        Args:
            query: Search query
            language: Filter by language (optional)
            top_k: Number of results to return
            min_importance: Minimum importance score filter
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of SearchResult objects, sorted by similarity
        """
        if len(self.api_ids) == 0:
            return []

        # Encode query
        query_embedding = self.model.encode(query, convert_to_numpy=True)

        # Calculate similarities
        similarities = self._cosine_similarity(query_embedding, self.api_embeddings)

        # Create results with filtering
        results = []
        for i, api_id in enumerate(self.api_ids):
            api_data = self.api_data[api_id]

            # Language filter
            if language and api_data.get("language") != language:
                continue

            # Importance filter
            if api_data.get("importance_score", 0.0) < min_importance:
                continue

            # Similarity threshold
            similarity = float(similarities[i])
            if similarity < min_similarity:
                continue

            results.append(SearchResult(
                result_type="api",
                result_id=api_id,
                title=api_data["api_id"],
                description=api_data.get("description", ""),
                score=similarity,
                language=api_data.get("language", ""),
                metadata={
                    "signature": api_data.get("signature", ""),
                    "importance_score": api_data.get("importance_score", 0.0),
                    "tags": api_data.get("tags", []),
                    "related_apis": api_data.get("related_apis", []),
                }
            ))

        # Sort by similarity and return top K
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def search_examples(
        self,
        query: str,
        language: Optional[str] = None,
        complexity: Optional[str] = None,
        top_k: int = 10,
        min_similarity: float = 0.0
    ) -> List[SearchResult]:
        """
        Search for examples using semantic similarity.

        Args:
            query: Search query
            language: Filter by language (optional)
            complexity: Filter by complexity (beginner/intermediate/advanced)
            top_k: Number of results to return
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of SearchResult objects, sorted by similarity
        """
        if len(self.example_ids) == 0:
            return []

        # Encode query
        query_embedding = self.model.encode(query, convert_to_numpy=True)

        # Calculate similarities
        similarities = self._cosine_similarity(query_embedding, self.example_embeddings)

        # Create results with filtering
        results = []
        for i, example_id in enumerate(self.example_ids):
            example_data = self.example_data[example_id]

            # Language filter
            if language and example_data.get("language") != language:
                continue

            # Complexity filter
            if complexity and example_data.get("complexity") != complexity:
                continue

            # Similarity threshold
            similarity = float(similarities[i])
            if similarity < min_similarity:
                continue

            results.append(SearchResult(
                result_type="example",
                result_id=example_id,
                title=example_data["title"],
                description=example_data.get("use_case", ""),
                score=similarity,
                language=example_data.get("language", ""),
                metadata={
                    "complexity": example_data.get("complexity", "beginner"),
                    "apis_used": example_data.get("apis_used", []),
                    "tags": example_data.get("tags", []),
                    "validated": example_data.get("validated", False),
                }
            ))

        # Sort by similarity and return top K
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def search(
        self,
        query: str,
        result_type: Optional[str] = None,
        language: Optional[str] = None,
        top_k: int = 10
    ) -> List[SearchResult]:
        """
        Unified semantic search across APIs and examples.

        Args:
            query: Search query
            result_type: Filter by type ("api" or "example")
            language: Filter by language
            top_k: Total number of results

        Returns:
            Combined and sorted search results
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

    def get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding for arbitrary text.

        Args:
            text: Input text

        Returns:
            Embedding vector (numpy array)
        """
        return self.model.encode(text, convert_to_numpy=True)

    def clear_cache(self):
        """Clear embedding cache files."""
        api_cache_path = self._get_cache_path("apis")
        example_cache_path = self._get_cache_path("examples")

        if api_cache_path.exists():
            api_cache_path.unlink()
            logger.info(f"Cleared API embeddings cache: {api_cache_path}")

        if example_cache_path.exists():
            example_cache_path.unlink()
            logger.info(f"Cleared example embeddings cache: {example_cache_path}")
