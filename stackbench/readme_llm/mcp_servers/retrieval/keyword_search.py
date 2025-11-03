"""
Keyword-based retrieval for README.LLM knowledge base.

Implements TF-IDF-style scoring with importance weighting and tag matching.
Fast, deterministic, and works without external dependencies.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from collections import Counter
import math
import logging

from stackbench.readme_llm.schemas import SearchResult

logger = logging.getLogger(__name__)


class KeywordRetrieval:
    """
    Fast keyword-based search for APIs and examples.

    Features:
    - TF-IDF scoring for relevance
    - Exact match boosting
    - Tag overlap scoring
    - Importance weighting
    - No external dependencies

    Example:
        >>> retrieval = KeywordRetrieval(kb_path)
        >>> results = retrieval.search("connect to database", top_k=5)
        >>> for result in results:
        ...     print(f"{result.title}: {result.score}")
    """

    def __init__(self, knowledge_base_path: Path):
        """
        Initialize retrieval system.

        Args:
            knowledge_base_path: Path to knowledge_base/ directory
        """
        self.kb_path = Path(knowledge_base_path)

        # Load knowledge base structure
        self.index = self._load_index()
        self.library_overview = self._load_library_overview()

        # Build search indices
        self.api_index: Dict[str, Dict] = {}  # {api_id: metadata}
        self.example_index: Dict[str, Dict] = {}  # {example_id: metadata}
        self.vocabulary: Set[str] = set()  # All unique terms
        self.idf_scores: Dict[str, float] = {}  # IDF scores per term

        self._build_indices()

        logger.info(f"Initialized KeywordRetrieval with {len(self.api_index)} APIs, {len(self.example_index)} examples")

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

    def _build_indices(self):
        """
        Build search indices from knowledge base.

        Creates:
        - api_index: {api_id: {data, terms, tags}}
        - example_index: {example_id: {data, terms, tags}}
        - vocabulary: Set of all unique terms
        - idf_scores: IDF scores for each term
        """
        logger.info("Building search indices...")

        # Load all APIs
        for language, api_list in self.index.get("apis", {}).items():
            for api_meta in api_list:
                api_id = api_meta["api_id"]
                api_file = self.kb_path / api_meta["file"]

                if not api_file.exists():
                    logger.warning(f"API file not found: {api_file}")
                    continue

                api_data = json.loads(api_file.read_text(encoding='utf-8'))

                # Extract searchable text
                searchable_text = " ".join([
                    api_data.get("api_id", ""),
                    api_data.get("signature", ""),
                    api_data.get("description", ""),
                    " ".join(api_data.get("search_keywords", [])),
                ])

                # Tokenize
                terms = self._tokenize(searchable_text)
                self.vocabulary.update(terms)

                # Store in index
                self.api_index[api_id] = {
                    "data": api_data,
                    "terms": terms,
                    "term_counts": Counter(terms),
                    "tags": set(api_data.get("tags", [])),
                    "importance": api_data.get("importance_score", 0.5),
                    "language": api_data.get("language", ""),
                }

        # Load all examples
        for language, example_list in self.index.get("examples", {}).items():
            for example_meta in example_list:
                example_id = example_meta["example_id"]
                example_file = self.kb_path / example_meta["file"]

                if not example_file.exists():
                    logger.warning(f"Example file not found: {example_file}")
                    continue

                example_data = json.loads(example_file.read_text(encoding='utf-8'))

                # Extract searchable text
                searchable_text = " ".join([
                    example_data.get("title", ""),
                    example_data.get("use_case", ""),
                    " ".join(example_data.get("apis_used", [])),
                ])

                # Tokenize
                terms = self._tokenize(searchable_text)
                self.vocabulary.update(terms)

                # Store in index
                self.example_index[example_id] = {
                    "data": example_data,
                    "terms": terms,
                    "term_counts": Counter(terms),
                    "tags": set(example_data.get("tags", [])),
                    "complexity": example_data.get("complexity", "beginner"),
                    "language": example_data.get("language", ""),
                }

        # Calculate IDF scores
        self._calculate_idf()

        logger.info(f"Built indices: {len(self.api_index)} APIs, {len(self.example_index)} examples, {len(self.vocabulary)} terms")

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into searchable terms.

        Args:
            text: Input text

        Returns:
            List of lowercase tokens
        """
        # Convert to lowercase
        text = text.lower()

        # Split on non-alphanumeric (keep dots for API names)
        tokens = re.findall(r'[a-z0-9_\.]+', text)

        # Filter out single characters and common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        tokens = [t for t in tokens if len(t) > 1 and t not in stop_words]

        return tokens

    def _calculate_idf(self):
        """
        Calculate IDF (Inverse Document Frequency) scores.

        IDF(term) = log(N / df(term))
        where N = total documents, df(term) = documents containing term
        """
        total_docs = len(self.api_index) + len(self.example_index)

        # Count document frequencies
        doc_frequencies = Counter()

        for api_data in self.api_index.values():
            unique_terms = set(api_data["terms"])
            doc_frequencies.update(unique_terms)

        for example_data in self.example_index.values():
            unique_terms = set(example_data["terms"])
            doc_frequencies.update(unique_terms)

        # Calculate IDF scores
        for term in self.vocabulary:
            df = doc_frequencies.get(term, 0)
            if df > 0:
                self.idf_scores[term] = math.log(total_docs / df)
            else:
                self.idf_scores[term] = 0.0

    def _tf_idf_score(self, query_terms: List[str], doc_term_counts: Counter) -> float:
        """
        Calculate TF-IDF score between query and document.

        Args:
            query_terms: Query tokens
            doc_term_counts: Document term counts

        Returns:
            TF-IDF similarity score
        """
        score = 0.0
        doc_length = sum(doc_term_counts.values())

        for term in query_terms:
            if term in doc_term_counts:
                tf = doc_term_counts[term] / doc_length  # Term frequency (normalized)
                idf = self.idf_scores.get(term, 0.0)  # Inverse document frequency
                score += tf * idf

        return score

    def _exact_match_boost(self, query: str, doc_text: str) -> float:
        """
        Boost score if query appears exactly in document.

        Args:
            query: Original query string
            doc_text: Document text

        Returns:
            Boost multiplier (1.0 to 2.0)
        """
        query_lower = query.lower()
        doc_lower = doc_text.lower()

        if query_lower in doc_lower:
            return 2.0

        # Partial match boost
        query_words = query_lower.split()
        if len(query_words) > 1:
            matches = sum(1 for word in query_words if word in doc_lower)
            if matches > 0:
                return 1.0 + (matches / len(query_words)) * 0.5

        return 1.0

    def _tag_overlap_score(self, query_terms: List[str], doc_tags: Set[str]) -> float:
        """
        Score based on tag overlap with query.

        Args:
            query_terms: Query tokens
            doc_tags: Document tags

        Returns:
            Tag overlap score (0.0 to 1.0)
        """
        if not doc_tags:
            return 0.0

        query_set = set(query_terms)
        overlap = len(query_set.intersection(doc_tags))

        return overlap / max(len(query_set), len(doc_tags))

    def search_apis(
        self,
        query: str,
        language: Optional[str] = None,
        top_k: int = 10,
        min_importance: float = 0.0
    ) -> List[SearchResult]:
        """
        Search for APIs matching query.

        Args:
            query: Search query
            language: Filter by language (optional)
            top_k: Number of results to return
            min_importance: Minimum importance score filter

        Returns:
            List of SearchResult objects, sorted by relevance
        """
        query_terms = self._tokenize(query)
        results = []

        for api_id, api_info in self.api_index.items():
            # Language filter
            if language and api_info["language"] != language:
                continue

            # Importance filter
            if api_info["importance"] < min_importance:
                continue

            api_data = api_info["data"]

            # Calculate TF-IDF score
            tfidf_score = self._tf_idf_score(query_terms, api_info["term_counts"])

            # Exact match boost
            searchable_text = f"{api_data['api_id']} {api_data['description']}"
            exact_boost = self._exact_match_boost(query, searchable_text)

            # Tag overlap
            tag_score = self._tag_overlap_score(query_terms, api_info["tags"])

            # Combined score with importance weighting
            final_score = (
                tfidf_score * exact_boost * 0.6 +
                tag_score * 0.2 +
                api_info["importance"] * 0.2
            )

            if final_score > 0:
                results.append(SearchResult(
                    result_type="api",
                    result_id=api_id,
                    title=api_data["api_id"],
                    description=api_data.get("description", ""),
                    score=final_score,
                    language=api_info["language"],
                    metadata={
                        "signature": api_data.get("signature", ""),
                        "importance_score": api_info["importance"],
                        "tags": list(api_info["tags"]),
                        "related_apis": api_data.get("related_apis", []),
                    }
                ))

        # Sort by score and return top K
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def search_examples(
        self,
        query: str,
        language: Optional[str] = None,
        complexity: Optional[str] = None,
        top_k: int = 10
    ) -> List[SearchResult]:
        """
        Search for examples matching query.

        Args:
            query: Search query
            language: Filter by language (optional)
            complexity: Filter by complexity (beginner/intermediate/advanced)
            top_k: Number of results to return

        Returns:
            List of SearchResult objects, sorted by relevance
        """
        query_terms = self._tokenize(query)
        results = []

        for example_id, example_info in self.example_index.items():
            # Language filter
            if language and example_info["language"] != language:
                continue

            # Complexity filter
            if complexity and example_info["complexity"] != complexity:
                continue

            example_data = example_info["data"]

            # Calculate TF-IDF score
            tfidf_score = self._tf_idf_score(query_terms, example_info["term_counts"])

            # Exact match boost
            searchable_text = f"{example_data['title']} {example_data.get('use_case', '')}"
            exact_boost = self._exact_match_boost(query, searchable_text)

            # Tag overlap
            tag_score = self._tag_overlap_score(query_terms, example_info["tags"])

            # Combined score
            final_score = (
                tfidf_score * exact_boost * 0.7 +
                tag_score * 0.3
            )

            if final_score > 0:
                results.append(SearchResult(
                    result_type="example",
                    result_id=example_id,
                    title=example_data["title"],
                    description=example_data.get("use_case", ""),
                    score=final_score,
                    language=example_info["language"],
                    metadata={
                        "complexity": example_info["complexity"],
                        "apis_used": example_data.get("apis_used", []),
                        "tags": list(example_info["tags"]),
                        "validated": example_data.get("validated", False),
                    }
                ))

        # Sort by score and return top K
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
        Unified search across APIs and examples.

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

    def get_api_details(self, api_id: str) -> Optional[Dict]:
        """
        Get full details for a specific API.

        Args:
            api_id: API identifier

        Returns:
            API data dictionary or None if not found
        """
        api_info = self.api_index.get(api_id)
        if api_info:
            return api_info["data"]
        return None

    def get_example_details(self, example_id: str) -> Optional[Dict]:
        """
        Get full details for a specific example.

        Args:
            example_id: Example identifier

        Returns:
            Example data dictionary or None if not found
        """
        example_info = self.example_index.get(example_id)
        if example_info:
            return example_info["data"]
        return None
