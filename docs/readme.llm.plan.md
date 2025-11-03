# ReadMe.LLM Integration Plan

**From Stackbench Validation to Intelligent Documentation Serving**

*Based on: "ReadMe.LLM: A Framework to Help LLMs Understand Your Library" (Wijaya et al., 2025)*

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Background & Motivation](#background--motivation)
- [Vision Overview](#vision-overview)
- [Stage 1: README.LLM Generator Agent](#stage-1-readmellm-generator-agent)
- [Stage 2: DocuMentor MCP Server](#stage-2-documentor-mcp-server)
- [Retrieval Strategy](#retrieval-strategy)
- [Integration with Stackbench](#integration-with-stackbench)
- [Continuous Improvement Loop](#continuous-improvement-loop)
- [Implementation Roadmap](#implementation-roadmap)
- [Success Metrics](#success-metrics)
- [References](#references)

---

## Executive Summary

The ReadMe.LLM paper [1] demonstrates that LLMs achieve dramatically better code generation with structured, LLM-oriented documentation (30% → 100% success rate). This plan outlines a **two-stage system** that extends Stackbench's capabilities:

1. **Stage 1**: README.LLM Generator - Standalone system that transforms any documentation into LLM-optimized format
2. **Stage 2**: DocuMentor MCP Server - Intelligent, on-demand documentation retrieval for AI coding tools

### Key Architecture Principles

**Standalone by Design**: The README.LLM system (`stackbench/readme_llm/`) operates independently from Stackbench's validation pipeline. It can:

- ✅ **Work with any documentation** - No validation required
- ✅ **Support multiple languages** - Python, TypeScript, JavaScript, Go, Rust
- ✅ **Reuse existing components** - Leverages `stackbench/introspection_templates/`
- ✅ **Handle complex formats** - MkDocs snippets, reStructuredText, various code blocks
- ✅ **Optionally integrate** - Can consume Stackbench validation results for maximum quality

This addresses the core problem identified in the paper: *"Lesser-known libraries are often misused or misrepresented in AI-generated code"* [1, p.1], while providing flexibility to work with any library documentation.

---

## Background & Motivation

### The Problem ReadMe.LLM Identifies

From the paper [1]:

> "Well-established libraries like Pandas have plenty of public documentation... allowing the LLM to produce reliable output, while lesser-known libraries are often misused or misrepresented in AI-generated code." (p.1)

**Key Findings** [1, Section 3]:
- Baseline (no context): ~30% success rate
- Human-oriented docs (README.md): Often *worse* than no context
- LLM-oriented docs (ReadMe.LLM): Up to 100% success rate
- Critical components: Function signatures + Examples + Structured format

### How Stackbench Complements ReadMe.LLM

**ReadMe.LLM's Limitation**: Relies on manual creation of LLM-oriented docs

**Stackbench's Advantage**: Already validates and extracts:
- ✓ Accurate API signatures (API Validation Agent)
- ✓ Working code examples (Code Validation Agent)
- ✓ Structured data extraction (Extraction Agent)
- ✓ API importance scoring (API Completeness Agent)

**Synergy**: Stackbench can **automatically generate** high-quality ReadMe.LLM files from validated documentation.

---

## Vision Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                STACKBENCH VALIDATED DOCUMENTATION                │
│  (Accurate APIs + Working Examples + Clear Instructions)        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
         ┌──────────────────┴──────────────────┐
         │                                     │
    STAGE 1                                STAGE 2
┌─────────────────┐                  ┌──────────────────────┐
│ README.LLM      │                  │ DocuMentor MCP       │
│ Generator Agent │ ──────────────→  │ Server               │
│                 │                  │ (Smart Retrieval)    │
└─────────────────┘                  └──────────────────────┘
         │                                     ↓
         │                            ┌────────────────────┐
         ↓                            │ Claude Code/       │
   README.LLM Format                  │ AI Coding Tools    │
   (Paper's Structure)                └────────────────────┘
                                               ↓
                                      ┌────────────────────┐
                                      │ Continuous         │
                                      │ Improvement via    │
                                      │ Feedback Loop      │
                                      └────────────────────┘
```

### Design Principles (From Paper)

Following ReadMe.LLM's proven structure [1, Section 2]:

1. **Rules**: Instructions on how LLM should process the library
2. **Library Description**: Concise overview of purpose and domain context
3. **Code Snippets**: Interleaved function signatures + examples + descriptions

**XML Tag Structure** [1, p.3]:
> "We used XML tags to separate different types of content (e.g. <examples>). This formatting improves readability for LLMs and helps them easily parse the rules, description, and code snippets in ReadMe.LLM."

---

## Stage 1: README.LLM Generator Agent

### Architecture: Standalone System

**Design Principle**: README.LLM generation is a **standalone system** under `stackbench/readme_llm/`, similar to the walkthroughs system. It operates independently from the Stackbench validation pipeline and can:

1. **Work directly from documentation** - No dependency on prior Stackbench runs
2. **Reuse existing components** - Leverages introspection templates from `stackbench/introspection_templates/`
3. **Multi-language support** - Auto-detects and handles Python, TypeScript, JavaScript, Go, Rust
4. **Comprehensive extraction** - Scans entire docs directory recursively
5. **Handle complex formats** - Processes MkDocs snippets (`--8<--` includes) and various code block styles

### Purpose

Generate optimized ReadMe.LLM format following the paper's methodology [1, Appendix B], creating a **structured, searchable knowledge base** for the MCP server by:
- **Introspecting library APIs** using language-specific templates
- **Extracting code examples** from all documentation via regex/parsing
- **Resolving snippet includes** (MkDocs, reStructuredText, etc.)
- **Matching examples to APIs** for contextual learning

### Input Parameters

```python
{
  "docs_path": "docs/src",           # Base documentation directory
  "library_name": "lancedb",         # Library to introspect and document
  "library_version": "0.25.2",       # Version to install and test
  "languages": ["python"],           # Optional: Auto-detect if not specified
  "repo_url": "...",                 # Optional: Clone if not local
  "branch": "main"                   # Optional: Which branch to use
}
```

**Key Differences from Stackbench Pipeline**:
- ✅ No prior extraction needed - analyzes docs directly
- ✅ No validation dependency - introspects actual library
- ✅ Multi-language from day one
- ✅ Handles snippet resolution programmatically
- ❌ No accuracy validation (that's Stackbench's job)
- ❌ No clarity scoring (focus on structure, not quality)

### Input Sources

The standalone system gathers data from multiple sources:

```python
{
  "documentation_files": {
    "source": "Recursive scan of docs_path",
    "formats": [".md", ".rst", ".mdx"],
    "extraction": "Regex + AST parsing for code blocks"
  },
  "library_introspection": {
    "source": "stackbench/introspection_templates/<language>_introspect.py",
    "method": "Install library via pip/npm, run introspection",
    "output": "api_surface.json with signatures, types, descriptions"
  },
  "code_examples": {
    "source": "All code blocks in documentation",
    "filtering": "Language-specific (python, typescript, javascript, go, rust)",
    "snippet_resolution": "Resolve MkDocs --8<-- includes to actual code",
    "matching": "Match examples to APIs via import/usage analysis"
  },
  "library_metadata": {
    "name": "lancedb",
    "version": "0.25.2",
    "languages": ["python"],  # Auto-detected or specified
    "domain": "vector database"  # Optional: from docs or package metadata
  }
}
```

### Standalone System Workflow

**Unlike Stackbench's validation pipeline**, the README.LLM generator operates in a single-pass workflow:

```
1. Language Detection
   ↓
   Scan docs_path for code blocks
   Identify languages: ```python, ```typescript, ```go, etc.

2. Documentation Parsing
   ↓
   Recursively scan all .md/.rst/.mdx files
   Extract code blocks with metadata (language, file, line number)
   Resolve snippet includes (MkDocs --8<--, reStructuredText literalinclude)

3. Library Introspection
   ↓
   For each detected language:
     - Install library (pip install lancedb==0.25.2, npm install, etc.)
     - Run introspection template (stackbench/introspection_templates/<lang>_introspect.py)
     - Parse API surface (functions, classes, methods, signatures)

4. Example Extraction & Matching
   ↓
   For each code example:
     - Detect imports/usage (import lancedb, lancedb.connect)
     - Match to APIs from introspection
     - Classify as complete/snippet
     - Infer complexity (beginner/intermediate/advanced)

5. Knowledge Base Construction
   ↓
   Build api_catalog: All APIs with signatures
   Build examples_db: Examples linked to APIs
   Generate library_overview: High-level concepts

6. Output Generation
   ↓
   Generate README.LLM (monolithic XML format)
   Generate knowledge_base/ (structured JSON for MCP)
```

**Key Technical Components**:

#### 1. Multi-Language Support

```python
# stackbench/readme_llm/extractors/language_detector.py

class LanguageDetector:
    """
    Auto-detect programming languages in documentation

    Strategy:
    1. Scan all code blocks for language tags (```python, ```typescript)
    2. Count occurrences by language
    3. Return languages with >5 examples (configurable threshold)
    """

    SUPPORTED_LANGUAGES = {
        "python": ["python", "py", "python3"],
        "typescript": ["typescript", "ts"],
        "javascript": ["javascript", "js"],
        "go": ["go", "golang"],
        "rust": ["rust", "rs"]
    }

    def detect_languages(self, docs_path: str) -> List[str]:
        """
        Returns: ["python", "typescript"] based on code block analysis
        """
        pass
```

#### 2. Code Example Extraction (Regex + Parsing)

```python
# stackbench/readme_llm/extractors/code_extractor.py

import re
from pathlib import Path
from typing import List, Dict

class CodeExampleExtractor:
    """
    Extract code examples from all documentation formats

    Handles:
    - Standard markdown code blocks (```python ... ```)
    - MkDocs snippet includes (--8<-- "snippets/example.py")
    - reStructuredText literalinclude (.. literalinclude:: example.py)
    - Indented code blocks (Markdown/reStructuredText)
    """

    CODE_BLOCK_PATTERN = re.compile(
        r'```(\w+)?\n(.*?)```',
        re.DOTALL | re.MULTILINE
    )

    MKDOCS_SNIPPET_PATTERN = re.compile(
        r'--8<--\s+"([^"]+)"'
    )

    def extract_from_file(self, file_path: Path) -> List[CodeExample]:
        """
        Extract all code blocks from a single file

        Returns list of CodeExample objects with:
        - code: The actual code string
        - language: Detected language
        - source_file: Where it came from
        - line_number: Location in file
        - is_snippet: True if from external file
        """
        pass

    def resolve_snippet(self, snippet_path: str, base_path: Path) -> str:
        """
        Resolve MkDocs snippet includes

        Example: --8<-- "snippets/quickstart.py"
        Returns: Content of docs/src/snippets/quickstart.py
        """
        pass
```

#### 3. Introspection Template Reuse

```python
# stackbench/readme_llm/introspection/runner.py

class IntrospectionRunner:
    """
    Reuse existing introspection templates from Stackbench

    Templates: stackbench/introspection_templates/
    - python_introspect.py
    - typescript_introspect.ts (future)
    - go_introspect.go (future)
    """

    def introspect_library(
        self,
        library_name: str,
        version: str,
        language: str
    ) -> IntrospectionResult:
        """
        1. Create isolated environment (venv, npm, etc.)
        2. Install library at specific version
        3. Run introspection template
        4. Parse output (api_surface.json)
        5. Return structured API data
        """
        pass
```

#### 4. Example-to-API Matching

```python
# stackbench/readme_llm/matchers/api_matcher.py

class APIExampleMatcher:
    """
    Match code examples to APIs using import/usage analysis

    Strategy:
    1. Parse imports (import lancedb, from lancedb import connect)
    2. Detect API calls (lancedb.connect, db.create_table)
    3. Match against introspected API surface
    4. Build bi-directional links (API -> Examples, Example -> APIs)
    """

    def match_examples(
        self,
        examples: List[CodeExample],
        api_surface: Dict[str, APIEntry]
    ) -> Dict[str, List[str]]:
        """
        Returns:
        {
          "lancedb.connect": ["quickstart_ex1", "connection_ex2"],
          "Table.search": ["search_ex1", "search_ex2"]
        }
        """
        pass
```

### Output Structure

```
data/<run_id>/readme_llm/
├── README.LLM                    # Traditional monolithic file (Paper format)
├── knowledge_base/               # Structured for MCP server
│   ├── index.json               # Master index
│   ├── library_overview.json   # High-level concepts
│   ├── api_catalog/            # Searchable API database
│   │   ├── search.json
│   │   ├── insert.json
│   │   └── update.json
│   ├── examples_db/            # Contextual examples
│   │   ├── quickstart.json
│   │   ├── search_examples.json
│   │   └── filter_examples.json
│   ├── embeddings/             # Vector embeddings (optional)
│   │   ├── api_embeddings.npy
│   │   └── example_embeddings.npy
│   └── metadata.json           # Stats, importance scores
```

### Monolithic README.LLM Generation

Following the exact structure validated in the paper [1, Appendix C]:

```xml
<ReadMe.LLM>
  <rules>
    Rule number 1: When you are unsure about something, ask the user what information you need.
    Rule number 2: Reuse [Library] functions and code when applicable.
    Rule number 3: Consider library dependencies when generating code solutions.
  </rules>

  <context_description>
    The context will be for the [Library Name]. [High-level library purpose and domain].
    The context is organized into different numbered sections using XML tags.
  </context_description>

  <context_1>
    <context_1_description>
      [API or class description - what it does and why it matters]
    </context_1_description>

    <context_1_function>
      [Function signature with parameters and types]
    </context_1_function>

    <context_1_example>
      [Working, validated code example from Stackbench]
    </context_1_example>
  </context_1>

  <!-- Repeat for N most important APIs based on importance scoring -->
</ReadMe.LLM>
```

**Key Insight from Paper** [1, Section 3.1.1]:
> "Relying solely on examples achieved a 96% average success rate, while incorporating combined contexts enabled all models to hit 100%."

Therefore, our generator prioritizes:
1. Validated examples (from Code Validation Agent)
2. Accurate signatures (from API Validation Agent)
3. Clear descriptions (from Clarity Validation Agent)

### Knowledge Base Structure

#### API Catalog Schema

```json
{
  "api_id": "lancedb.connect",
  "signature": "connect(uri: str, **kwargs) -> Connection",
  "description": "Connect to a LanceDB instance",
  "parameters": [
    {
      "name": "uri",
      "type": "str",
      "required": true,
      "description": "Path or URI to database"
    }
  ],
  "returns": {
    "type": "Connection",
    "description": "Connection object to interact with database"
  },
  "examples": ["quickstart_ex1", "connection_ex2"],
  "importance_score": 0.95,
  "tags": ["connection", "initialization", "database"],
  "related_apis": ["lancedb.disconnect", "Connection.close"],
  "search_keywords": ["connect", "database", "initialize", "setup"]
}
```

**Importance Scoring**: Leverages Stackbench's API Completeness Agent heuristics

#### Examples Database Schema

```json
{
  "example_id": "quickstart_ex1",
  "title": "Connect to database and create table",
  "code": "import lancedb\ndb = lancedb.connect(...)",
  "apis_used": ["lancedb.connect", "Connection.create_table"],
  "use_case": "initialization",
  "complexity": "beginner",
  "tags": ["quickstart", "setup", "table"],
  "prerequisites": ["pip install lancedb"],
  "expected_output": "Table created successfully",
  "validated": true,
  "execution_context": {
    "works_on_version": "0.25.2",
    "validated_at": "2025-01-15"
  }
}
```

**Validation Guarantee**: All examples marked `"validated": true` have passed Stackbench's Code Validation Agent

### Agent Implementation

```python
# stackbench/agents/readme_llm_generator_agent.py

class ReadMeLLMGeneratorAgent:
    """
    Transforms validated Stackbench data into:
    1. Traditional README.LLM (monolithic, following paper format)
    2. Structured knowledge base for MCP server

    References:
    - ReadMe.LLM structure: [1, Section 2]
    - Context interleaving: [1, Appendix B]
    - XML tag formatting: [1, Section 2, p.3]
    """

    def __init__(self, run_id: str, library_name: str, version: str):
        self.run_id = run_id
        self.library = library_name
        self.version = version
        self.base_path = f"data/{run_id}"

    def generate(self):
        """Main orchestration method"""
        # Load validated data from all Stackbench agents
        extractions = self._load_extractions()
        api_completeness = self._load_api_completeness()
        validated_examples = self._load_validated_examples()
        clarity_data = self._load_clarity_validation()

        # Generate both formats
        readme_llm = self._generate_monolithic_readme_llm(
            extractions, api_completeness, validated_examples
        )

        knowledge_base = self._generate_knowledge_base(
            extractions, api_completeness, validated_examples, clarity_data
        )

        # Save outputs
        self._save_readme_llm(readme_llm)
        self._save_knowledge_base(knowledge_base)

        return {
            "readme_llm_path": f"{self.base_path}/readme_llm/README.LLM",
            "knowledge_base_path": f"{self.base_path}/readme_llm/knowledge_base/",
            "stats": self._generate_stats(knowledge_base)
        }

    def _generate_monolithic_readme_llm(self, extractions, completeness, examples):
        """
        Generate traditional README.LLM following the paper's format [1, Appendix C]

        Structure:
        1. Rules (customizable guidelines)
        2. Library Description (domain context)
        3. Code Snippets (sorted by importance, interleaved format)
        """
        sections = []

        # Rules section (paper's recommendations)
        rules = self._generate_rules()
        sections.append(f"<rules>\n{rules}\n</rules>")

        # Library description
        description = self._generate_library_description()
        sections.append(f"<library_description>\n{description}\n</library_description>")

        # Code snippets - sorted by importance score from API Completeness Agent
        sorted_apis = self._sort_by_importance(extractions["apis"], completeness)

        # Top N most important APIs (paper found 50 works well)
        for i, api in enumerate(sorted_apis[:50], 1):
            context = self._create_context_section(api, examples, i)
            sections.append(context)

        return "\n\n".join(sections)

    def _create_context_section(self, api, examples, index):
        """
        Create <context_N> section following ReadMe.LLM format [1, Appendix B]

        Paper's finding: Interleaving description + function + example
        is more effective than separate sections.
        """
        relevant_examples = self._get_examples_for_api(api, examples)

        return f"""<context_{index}>
<context_{index}_description>
{api['description']}
</context_{index}_description>

<context_{index}_function>
{api['signature']}

Parameters:
{self._format_parameters(api['parameters'])}

Returns:
{api.get('returns', 'None')}
</context_{index}_function>

<context_{index}_example>
{self._format_examples(relevant_examples)}
</context_{index}_example>
</context_{index}>"""

    def _generate_knowledge_base(self, extractions, completeness, examples, clarity):
        """
        Create structured, searchable knowledge base for MCP server

        Extends ReadMe.LLM concept with:
        - Searchable API catalog
        - Tagged examples database
        - Relationship graph
        - Metadata for ranking
        """
        kb = {
            "library_overview": self._create_overview(clarity),
            "api_catalog": self._create_api_catalog(extractions, completeness),
            "examples_db": self._create_examples_db(examples),
            "concept_graph": self._create_concept_graph(),
        }
        return kb

    def _create_api_catalog(self, extractions, completeness):
        """
        Create searchable API catalog with rich metadata

        Each entry includes:
        - Signature and description
        - Parameter details
        - Importance score (from API Completeness Agent)
        - Search keywords and tags
        - Related APIs
        """
        catalog = {}
        for api in extractions["apis"]:
            api_entry = {
                "api_id": api["full_name"],
                "signature": api["signature"],
                "description": api["description"],
                "parameters": self._parse_parameters(api),
                "returns": api.get("returns"),
                "examples": self._link_examples(api, examples),
                "importance_score": self._get_importance_score(api, completeness),
                "tags": self._generate_tags(api),
                "related_apis": self._find_related_apis(api),
                "search_keywords": self._generate_search_keywords(api),
            }
            catalog[api["full_name"]] = api_entry
        return catalog

    def _create_examples_db(self, validated_examples):
        """
        Create contextual examples database

        Only includes examples that passed Stackbench validation.
        Paper's finding: Examples are critical for LLM success [1, Section 3].
        """
        examples_db = {}
        for ex in validated_examples:
            if ex["status"] == "passed":  # Only validated examples
                example_entry = {
                    "example_id": self._generate_example_id(ex),
                    "title": ex.get("title"),
                    "code": ex["code"],
                    "apis_used": self._extract_apis_from_code(ex["code"]),
                    "use_case": self._infer_use_case(ex),
                    "complexity": self._infer_complexity(ex),
                    "tags": self._generate_example_tags(ex),
                    "prerequisites": ex.get("prerequisites", []),
                    "validated": True,
                    "execution_context": {
                        "works_on_version": self.version,
                        "validated_at": ex["validated_at"]
                    }
                }
                examples_db[example_entry["example_id"]] = example_entry
        return examples_db
```

### Paper's Content Selection Strategy

From the Supervision case study [1, Section 3.1.1]:

> "We decided to omit ReadMe.md information from our final ReadMe.LLM and instead included only code snippets—interweaving function implementations and code examples."

**Our Approach**:
1. **Skip human docs**: Don't include README.md content directly
2. **Prioritize examples**: Validated examples from Code Validation Agent
3. **Add signatures**: Accurate signatures from API Validation Agent
4. **Importance ranking**: Top N APIs based on API Completeness scoring

---

## Stage 2: DocuMentor MCP Server

### Naming Rationale

**DocuMentor** = *Documentation Mentor*

An intelligent guide that helps AI agents understand and use libraries effectively, inspired by the paper's goal [1, p.2]:

> "ReadMe.LLM provides structured descriptions of the codebase. Just as traditional header files help tell how to use a library to a traditional compiler, the ReadMe.LLM file tells an LLM how to effectively use this library to get things done."

### Architecture Overview

```python
# stackbench/mcp_servers/documentor_server.py

from mcp.server import Server
from mcp.types import Tool, TextContent
import numpy as np
from typing import Optional, List, Dict
from datetime import datetime
import json

class DocuMentorServer:
    """
    MCP server that intelligently serves library documentation
    based on validated knowledge base from Stackbench.

    Implements ReadMe.LLM's principles [1] with on-demand retrieval:
    - Context-aware API discovery
    - Validated example matching
    - Continuous improvement via feedback
    """

    def __init__(self, knowledge_base_path: str):
        self.kb_path = knowledge_base_path
        self.server = Server("documentor")

        # Load knowledge base
        self.overview = self._load_json("library_overview.json")
        self.api_catalog = self._load_json("api_catalog/")
        self.examples_db = self._load_json("examples_db/")
        self.embeddings = self._load_embeddings()  # Optional

        # Usage analytics for continuous improvement
        self.usage_log = []

        # Register tools
        self._register_tools()
```

### Four Core MCP Tools

#### Tool 1: `get_library_overview`

**Purpose**: Provide high-level understanding of library organization and concepts

**Rationale from Paper** [1, Section 2]:
> "Library Description: A concise overview that sets the scene by outlining the library's purpose, core functionalities, and domain context."

```python
{
  "name": "get_library_overview",
  "description": "Get high-level understanding of library organization, core concepts, and common workflows",
  "inputSchema": {
    "type": "object",
    "properties": {
      "aspect": {
        "type": "string",
        "enum": ["architecture", "quickstart", "concepts", "all"],
        "description": "Which aspect to focus on"
      }
    }
  }
}
```

**Example Response**:
```
## Library Architecture
LanceDB is a vector database built on Lance columnar format...

### Key Modules:
- **lancedb.table**: Table operations and queries
- **lancedb.index**: Vector index management
- **lancedb.schema**: Schema definition and validation

## Quick Start
1. Install: `pip install lancedb`
2. Connect: `db = lancedb.connect("./my_db")`
3. Create table: `table = db.create_table("vectors", data)`

## Core Concepts
### Vector Search
Similarity search using ANN indexes for fast retrieval...
```

#### Tool 2: `find_api`

**Purpose**: Find specific APIs based on natural language queries

**Rationale**: Addresses the paper's finding that LLMs need structured function signatures [1, Section 3]

```python
{
  "name": "find_api",
  "description": "Find specific API signatures based on natural language query. Returns function signatures, parameters, and basic usage.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Natural language description of what you want to do"
      },
      "max_results": {
        "type": "integer",
        "default": 5,
        "description": "Maximum number of APIs to return"
      }
    },
    "required": ["query"]
  }
}
```

**Implementation**:

```python
async def _handle_find_api(self, args: dict) -> List[TextContent]:
    """
    Tool 2: Find API based on natural language query

    Uses hybrid search (see Retrieval Strategy section):
    1. Semantic search (if embeddings available)
    2. Keyword matching
    3. Tag-based filtering
    4. Importance weighting (from API Completeness Agent)
    """
    query = args["query"]
    max_results = args.get("max_results", 5)

    # Log for analytics
    self.usage_log.append({
        "tool": "find_api",
        "query": query,
        "timestamp": datetime.now()
    })

    # Hybrid search
    candidates = self._hybrid_search(
        query=query,
        search_space=self.api_catalog,
        max_results=max_results * 3  # Over-fetch for re-ranking
    )

    # Re-rank by importance score
    ranked = sorted(
        candidates,
        key=lambda x: x["relevance_score"] * x["importance_score"],
        reverse=True
    )[:max_results]

    # Format results
    results = []
    for i, api in enumerate(ranked, 1):
        results.append(f"\n### {i}. {api['api_id']}\n")
        results.append(f"**Signature:** `{api['signature']}`\n")
        results.append(f"**Description:** {api['description']}\n")
        results.append(f"**Parameters:**\n")
        for param in api['parameters']:
            required = "required" if param['required'] else "optional"
            results.append(f"  - `{param['name']}` ({param['type']}, {required}): {param['description']}\n")

        if api.get('returns'):
            results.append(f"**Returns:** {api['returns']['type']} - {api['returns']['description']}\n")

        results.append(f"**Relevance:** {api['relevance_score']:.2f} | **Importance:** {api['importance_score']:.2f}\n")

    return [TextContent(type="text", text="".join(results))]
```

**Example Usage**:
```
Query: "How do I search for similar vectors?"

Response:
### 1. Table.search
**Signature:** `search(query: List[float], limit: int = 10) -> LanceQueryBuilder`
**Description:** Search for vectors similar to the query vector
**Parameters:**
  - `query` (List[float], required): Query vector
  - `limit` (int, optional): Maximum results to return
**Returns:** LanceQueryBuilder - Query builder for refinement
**Relevance:** 0.95 | **Importance:** 0.92
```

#### Tool 3: `get_examples`

**Purpose**: Get validated, working code examples

**Rationale from Paper** [1, Section 3.1.1]:
> "Relying solely on examples achieved a 96% average success rate"

Examples are critical for LLM success.

```python
{
  "name": "get_examples",
  "description": "Get validated, working code examples relevant to your task. All examples are guaranteed to work with the specified library version.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_description": {
        "type": "string",
        "description": "What you're trying to accomplish"
      },
      "apis_involved": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional: Specific APIs you want examples for"
      },
      "complexity": {
        "type": "string",
        "enum": ["beginner", "intermediate", "advanced", "any"],
        "default": "any"
      }
    },
    "required": ["task_description"]
  }
}
```

**Implementation**:

```python
async def _handle_get_examples(self, args: dict) -> List[TextContent]:
    """
    Tool 3: Get relevant examples

    Returns validated, working examples based on:
    1. Task description similarity
    2. APIs involved
    3. Complexity level
    4. Use case matching

    Guarantee: All examples passed Stackbench Code Validation Agent
    """
    task = args["task_description"]
    apis_involved = args.get("apis_involved", [])
    complexity = args.get("complexity", "any")

    # Log usage
    self.usage_log.append({
        "tool": "get_examples",
        "task": task,
        "apis": apis_involved,
        "timestamp": datetime.now()
    })

    # Find relevant examples
    candidates = self._find_relevant_examples(
        task_description=task,
        apis_involved=apis_involved,
        complexity=complexity
    )

    if not candidates:
        return [TextContent(
            type="text",
            text=f"No examples found matching: '{task}'\n\n"
                 f"Try:\n"
                 f"1. Use 'find_api' tool first to discover relevant APIs\n"
                 f"2. Broaden your task description\n"
                 f"3. Report this as missing example via 'report_issue' tool"
        )]

    # Format examples
    results = []
    for i, ex in enumerate(candidates[:3], 1):  # Top 3 examples
        results.append(f"\n### Example {i}: {ex['title']}\n")
        results.append(f"**Use Case:** {ex['use_case']}\n")
        results.append(f"**Complexity:** {ex['complexity']}\n")
        results.append(f"**APIs Used:** {', '.join(ex['apis_used'])}\n")

        if ex['prerequisites']:
            results.append(f"**Prerequisites:**\n")
            for prereq in ex['prerequisites']:
                results.append(f"  - {prereq}\n")

        results.append(f"\n**Code:**\n```python\n{ex['code']}\n```\n")

        if ex.get('expected_output'):
            results.append(f"**Expected Output:** {ex['expected_output']}\n")

        results.append(f"\n✓ *Validated on version {ex['execution_context']['works_on_version']}*\n")

    return [TextContent(type="text", text="".join(results))]
```

**Example Response**:
```
### Example 1: Basic vector search
**Use Case:** similarity_search
**Complexity:** beginner
**APIs Used:** lancedb.connect, Table.search

**Prerequisites:**
  - pip install lancedb

**Code:**
```python
import lancedb

# Connect to database
db = lancedb.connect("./my_db")
table = db.open_table("vectors")

# Search for similar vectors
results = table.search([0.1, 0.2, 0.3]).limit(5).to_list()
print(f"Found {len(results)} results")
```

**Expected Output:** Found 5 results

✓ *Validated on version 0.25.2*
```

#### Tool 4: `report_issue`

**Purpose**: Continuous improvement via feedback collection

**Rationale**: Implements the paper's vision of iterative improvement [1, Section 2.1]:

> "Once released, developers can engage with the user community to gather feedback and iterate on the ReadMe.LLM, improving its clarity and effectiveness over time."

```python
{
  "name": "report_issue",
  "description": "Report when you're stuck, got an error, or documentation seems wrong. Helps improve the documentation continuously.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "What you were trying to do"
      },
      "apis_tried": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Which APIs you attempted to use"
      },
      "error_message": {
        "type": "string",
        "description": "The error message you received"
      },
      "code_attempted": {
        "type": "string",
        "description": "The code that didn't work"
      },
      "issue_type": {
        "type": "string",
        "enum": ["error", "unclear_docs", "missing_example", "wrong_signature"],
        "description": "Type of issue encountered"
      }
    },
    "required": ["query", "issue_type"]
  }
}
```

**Implementation**:

```python
async def _handle_report_issue(self, args: dict) -> List[TextContent]:
    """
    Tool 4: Report issue for continuous improvement

    Logs issues to feedback database for:
    1. Identifying documentation gaps
    2. Prioritizing improvements
    3. Retraining search/ranking algorithms

    Creates feedback loop similar to paper's developer workflow [1, Section 2.1]
    """
    issue = {
        "timestamp": datetime.now().isoformat(),
        "query": args["query"],
        "apis_tried": args.get("apis_tried", []),
        "error_message": args.get("error_message"),
        "code_attempted": args.get("code_attempted"),
        "issue_type": args["issue_type"],
        "session_context": self._get_recent_session_context()
    }

    # Save to feedback database (JSONL format)
    feedback_path = f"{self.kb_path}/../feedback/issues.jsonl"
    with open(feedback_path, "a") as f:
        f.write(json.dumps(issue) + "\n")

    # Analyze and provide immediate help
    suggestions = self._generate_suggestions(issue)

    response = [
        "Thank you for reporting this issue!\n\n",
        f"**Issue Type:** {issue['issue_type']}\n",
        f"**Query:** {issue['query']}\n\n",
        "**Immediate Suggestions:**\n"
    ]

    for suggestion in suggestions:
        response.append(f"- {suggestion}\n")

    response.append("\nThis issue has been logged for documentation improvement.")

    return [TextContent(type="text", text="".join(response))]

def _generate_suggestions(self, issue: dict) -> List[str]:
    """
    Generate helpful suggestions based on reported issue
    """
    suggestions = []

    if issue['issue_type'] == 'error':
        if issue.get('error_message'):
            if "ModuleNotFoundError" in issue['error_message']:
                suggestions.append("Ensure library is installed: `pip install <library>`")
            elif "AttributeError" in issue['error_message']:
                suggestions.append("Try using 'find_api' to verify correct API signature")
            else:
                suggestions.append("Check if library version matches documentation")

    elif issue['issue_type'] == 'missing_example':
        suggestions.append(f"Try searching with 'find_api' for: {issue['query']}")
        suggestions.append("Look at related APIs that might have examples")

    elif issue['issue_type'] == 'unclear_docs':
        if issue.get('apis_tried'):
            suggestions.append(f"Try 'get_examples' for these APIs: {', '.join(issue['apis_tried'])}")

    # Always offer to check overview
    suggestions.append("Use 'get_library_overview' to understand library architecture")

    return suggestions
```

---

## Retrieval Strategy

### Challenge

From the paper [1, p.2]:

> "While web search is only available in the US... integrating ReadMe.LLM into settings where web search is not feasible, such as internal company libraries..."

We need effective retrieval **without** relying on external search.

### Three Approaches

#### Option 1: Lightweight Keyword Search (No Dependencies)

**Pros**: Fast, no ML dependencies, works offline
**Cons**: Less accurate than semantic search

```python
# stackbench/mcp_servers/retrieval/keyword_search.py

class KeywordRetrieval:
    """
    BM25-style search with tag boosting

    No external dependencies, purely rule-based matching
    """

    def search(self, query: str, corpus: dict, k: int = 5) -> List[dict]:
        """
        Search using:
        1. TF-IDF scoring on descriptions
        2. Exact match boosting on API names
        3. Tag overlap scoring
        4. Fuzzy string matching for function names
        5. Importance score weighting
        """
        query_tokens = set(query.lower().split())

        scores = []
        for api_id, api_data in corpus.items():
            # Create searchable text
            searchable = " ".join([
                api_data['api_id'],
                api_data['description'],
                " ".join(api_data.get('search_keywords', [])),
                " ".join([p['name'] for p in api_data['parameters']])
            ]).lower()

            # Simple scoring: count matching tokens
            tokens = set(searchable.split())
            matches = query_tokens.intersection(tokens)
            score = len(matches) / len(query_tokens) if query_tokens else 0

            # Boost for exact matches in API name
            if any(token in api_data['api_id'].lower() for token in query_tokens):
                score *= 1.5

            # Boost by importance score
            score *= api_data['importance_score']

            if score > 0:
                api_data_copy = api_data.copy()
                api_data_copy['relevance_score'] = score
                scores.append(api_data_copy)

        return sorted(scores, key=lambda x: x['relevance_score'], reverse=True)[:k]
```

#### Option 2: Vector Search (Better Accuracy)

**Pros**: Semantic understanding, handles synonyms, better relevance
**Cons**: Requires embedding model (~80MB), slower initialization

```python
# stackbench/mcp_servers/retrieval/vector_search.py

from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class VectorRetrieval:
    """
    Semantic search using sentence embeddings

    Model: all-MiniLM-L6-v2 (80MB, fast, good quality)
    Reference: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
    """

    def __init__(self):
        # Lightweight model optimized for semantic search
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def index_knowledge_base(self, apis: dict, examples: dict):
        """
        Pre-compute embeddings for all APIs and examples

        Saves to disk for fast loading on server restart
        """
        # Embed API descriptions
        api_texts = [
            f"{api['api_id']}: {api['description']}"
            for api in apis.values()
        ]
        api_embeddings = self.model.encode(api_texts, show_progress_bar=True)

        # Embed example descriptions
        ex_texts = [
            f"{ex['title']}: {ex['use_case']}"
            for ex in examples.values()
        ]
        ex_embeddings = self.model.encode(ex_texts, show_progress_bar=True)

        return {
            "api_embeddings": api_embeddings,
            "example_embeddings": ex_embeddings,
            "api_ids": list(apis.keys()),
            "example_ids": list(examples.keys())
        }

    def search(self, query: str, embeddings_data: dict, k: int = 5):
        """
        Find k most similar items using cosine similarity
        """
        query_embedding = self.model.encode([query])

        similarities = cosine_similarity(
            query_embedding,
            embeddings_data['api_embeddings']
        )[0]

        top_k_indices = np.argsort(similarities)[-k:][::-1]

        results = []
        for idx in top_k_indices:
            results.append({
                "id": embeddings_data['api_ids'][idx],
                "relevance_score": float(similarities[idx])
            })

        return results
```

#### Option 3: Hybrid Approach (Recommended)

**Combines best of both worlds**

```python
# stackbench/mcp_servers/retrieval/hybrid_search.py

class HybridRetrieval:
    """
    Hybrid search combining keyword and vector approaches

    Strategy (from information retrieval literature):
    1. Get candidates from both retrievers
    2. Merge using Reciprocal Rank Fusion (RRF)
    3. Re-rank by importance scores
    """

    def __init__(self, use_vectors: bool = True):
        self.keyword_searcher = KeywordRetrieval()
        self.vector_searcher = VectorRetrieval() if use_vectors else None

    def search(self, query: str, catalog: dict, k: int = 5):
        """
        Hybrid search with RRF merging
        """
        # Get candidates from keyword search
        keyword_results = self.keyword_searcher.search(query, catalog, k*2)

        if self.vector_searcher:
            # Get candidates from vector search
            vector_results = self.vector_searcher.search(query, catalog, k*2)

            # Merge with Reciprocal Rank Fusion
            results = self._reciprocal_rank_fusion(
                keyword_results,
                vector_results,
                k=60  # RRF constant
            )
        else:
            results = keyword_results

        # Re-rank by importance
        results = self._rerank_by_importance(results, catalog)

        return results[:k]

    def _reciprocal_rank_fusion(self, list1, list2, k=60):
        """
        RRF: Standard technique for merging ranked lists

        Score = sum(1 / (k + rank)) for each list

        Reference: "Reciprocal Rank Fusion outperforms Condorcet
        and individual Rank Learning Methods" (Cormack et al., 2009)
        """
        scores = {}

        # Add scores from list 1
        for rank, item in enumerate(list1):
            item_id = item['id'] if 'id' in item else item['api_id']
            scores[item_id] = scores.get(item_id, 0) + 1 / (k + rank + 1)

        # Add scores from list 2
        for rank, item in enumerate(list2):
            item_id = item['id'] if 'id' in item else item['api_id']
            scores[item_id] = scores.get(item_id, 0) + 1 / (k + rank + 1)

        # Sort by RRF score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [{"id": item_id, "rrf_score": score} for item_id, score in ranked]

    def _rerank_by_importance(self, results, catalog):
        """
        Final re-ranking combining:
        - Relevance score (from search)
        - Importance score (from API Completeness Agent)

        Final score = relevance * importance
        """
        for result in results:
            api_data = catalog[result['id']]
            result['importance_score'] = api_data['importance_score']
            result['final_score'] = (
                result.get('rrf_score', result.get('relevance_score', 0)) *
                result['importance_score']
            )

        return sorted(results, key=lambda x: x['final_score'], reverse=True)
```

### Recommendation

**Start with Hybrid (keyword + optional vectors)**

```python
# In DocuMentorServer.__init__

# Make vector search optional
self.retrieval = HybridRetrieval(
    use_vectors=os.getenv("DOCUMENTOR_USE_VECTORS", "false").lower() == "true"
)
```

**Benefits**:
- Works out-of-the-box with keyword search (no dependencies)
- Users can opt-in to vector search for better accuracy
- Graceful degradation if embedding model unavailable

---

## Integration with Stackbench

### Standalone vs. Integration Modes

The README.LLM system offers two operational modes:

#### Mode 1: Standalone (Recommended)

**Use Case**: Generate README.LLM directly from any documentation, no validation required

**Advantages**:
- ✅ **Fast**: Single-pass generation, no multi-agent validation pipeline
- ✅ **Flexible**: Works with any library documentation
- ✅ **Independent**: No dependency on Stackbench validation results
- ✅ **Multi-language**: Built-in support from day one

**Trade-offs**:
- ❌ **No validation**: Assumes documentation is accurate
- ❌ **All examples included**: Cannot filter by working/broken
- ❌ **No quality scoring**: No clarity or accuracy metrics

**When to use**:
- Quick README.LLM generation for any library
- Testing MCP server functionality
- Documentation doesn't need validation
- Multi-language documentation

#### Mode 2: Integration (Maximum Quality)

**Use Case**: Generate README.LLM from Stackbench validation results

**Advantages**:
- ✅ **Validated APIs**: Only accurate signatures included
- ✅ **Working examples**: Code validation filters broken examples
- ✅ **Quality scored**: Importance scores and clarity ratings
- ✅ **Comprehensive**: Detects undocumented/deprecated APIs

**Trade-offs**:
- ❌ **Slower**: Requires full Stackbench validation pipeline first
- ❌ **Python only**: Currently limited by Stackbench language support
- ❌ **More complex**: Two-stage workflow

**When to use**:
- Maximum accuracy required (production use)
- Already running Stackbench validation
- Need quality metrics and coverage reports
- Python libraries (for now)

#### Comparison Table

| Feature | Standalone Mode | Integration Mode |
|---------|----------------|------------------|
| Speed | Fast (~5 min) | Slow (~30 min) |
| Validation | None | Full (4 agents) |
| Examples | All | Validated only |
| Languages | Python/TS/Go/Rust | Python only |
| API accuracy | Introspection | Validated |
| Quality metrics | No | Yes |
| Dependencies | None | Stackbench run |
| Complexity | Simple | Advanced |

**Recommendation**: Start with **Standalone mode** for quick iteration, use **Integration mode** for production-quality README.LLM with validation guarantees.

---

### New CLI Commands

#### Standalone Mode (No Stackbench Run Required)

```bash
# Stage 1: Generate README.LLM directly from documentation
stackbench readme-llm generate \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --docs-path docs/src \
  --library lancedb \
  --version 0.25.2 \
  --languages python typescript \  # Optional: Auto-detect if omitted
  --output-format both             # monolithic, knowledge_base, or both

# Local documentation (skip cloning)
stackbench readme-llm generate \
  --docs-path /path/to/local/docs \
  --library lancedb \
  --version 0.25.2 \
  --output-format both

# Multi-language documentation
stackbench readme-llm generate \
  --repo https://github.com/example/polyglot-lib \
  --docs-path docs \
  --library polyglot \
  --version 1.0.0 \
  --languages python typescript go \  # Explicit languages
  --output-format both

# Optional: Generate embeddings for vector search
stackbench readme-llm generate \
  --repo https://github.com/lancedb/lancedb \
  --docs-path docs/src \
  --library lancedb \
  --version 0.25.2 \
  --output-format both \
  --generate-embeddings  # Requires sentence-transformers
```

#### Integration Mode (From Stackbench Run)

```bash
# Generate from existing Stackbench validation run
stackbench readme-llm generate \
  --from-run abc-123-def \
  --output-format both

# This reuses Stackbench's validated data:
# - Extraction results → API catalog
# - Code validation → Validated examples only
# - API completeness → Importance scores
# - Clarity scores → Prioritization

# Note: Standalone mode is recommended for most use cases
# Integration mode is useful if you already have Stackbench validation results
```

#### Stage 2: Start MCP Server

```bash
# Start DocuMentor MCP server
stackbench mcp serve \
  --knowledge-base data/abc-123-def/readme_llm/knowledge_base/ \
  --port 3000 \
  --use-vectors  # Optional: enable semantic search

# Analyze feedback and suggest improvements
stackbench mcp analyze-feedback \
  --knowledge-base data/abc-123-def/readme_llm/knowledge_base/ \
  --show-top-issues 10 \
  --output-report feedback_report.json
```

#### Full Standalone Workflow Example

```bash
# 1. Generate README.LLM directly from GitHub repo
stackbench readme-llm generate \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --docs-path docs/src \
  --library lancedb \
  --version 0.25.2 \
  --output-format both \
  --generate-embeddings

# Output:
# → data/<run-id>/readme_llm/README.LLM
# → data/<run-id>/readme_llm/knowledge_base/
# → data/<run-id>/readme_llm/knowledge_base/embeddings/

# 2. Start MCP server
stackbench mcp serve \
  --knowledge-base data/<run-id>/readme_llm/knowledge_base/ \
  --use-vectors

# 3. Use with Claude Code or other AI tools
# The MCP server provides 4 tools:
# - get_library_overview
# - find_api
# - get_examples
# - report_issue

# 4. Analyze feedback after usage
stackbench mcp analyze-feedback \
  --knowledge-base data/<run-id>/readme_llm/knowledge_base/ \
  --output-report feedback_report.json

# 5. Iterate: Fix docs, regenerate, restart server
```

#### Optional: Combined with Stackbench Validation

```bash
# For maximum quality: Run Stackbench validation first, then README.LLM
stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --docs-path docs/src \
  --include-folders python \
  --library lancedb \
  --version 0.25.2

# Generate README.LLM from validated data
stackbench readme-llm generate \
  --from-run <run-id> \
  --output-format both

# This gives you:
# 1. Validated API signatures (Stackbench)
# 2. Working examples only (Code Validation)
# 3. Structured README.LLM (Generator)
# 4. Smart MCP server (Stage 2)
```

### New Directory Structure

```
stackbench-v3/
├── stackbench/
│   ├── agents/                                 # Core validation agents (unchanged)
│   │   ├── extraction_agent.py
│   │   ├── api_completeness_agent.py
│   │   ├── api_validation_agent.py
│   │   ├── code_validation_agent.py
│   │   └── clarity_agent.py
│   ├── introspection_templates/               # REUSED by readme_llm
│   │   ├── python_introspect.py              # Existing template
│   │   ├── typescript_introspect.ts           # Future
│   │   └── go_introspect.go                  # Future
│   ├── readme_llm/                            # NEW: Standalone system
│   │   ├── __init__.py
│   │   ├── README.md                          # System documentation
│   │   ├── schemas.py                         # Pydantic models
│   │   ├── readme_llm_generator_agent.py     # Main orchestration agent
│   │   ├── extractors/                        # Code and language detection
│   │   │   ├── __init__.py
│   │   │   ├── language_detector.py          # Auto-detect languages
│   │   │   ├── code_extractor.py             # Extract code blocks
│   │   │   └── snippet_resolver.py           # MkDocs/RST includes
│   │   ├── introspection/                     # Wrapper for templates
│   │   │   ├── __init__.py
│   │   │   └── runner.py                     # Run introspection templates
│   │   ├── matchers/                          # Link examples to APIs
│   │   │   ├── __init__.py
│   │   │   └── api_matcher.py                # Example-to-API matching
│   │   ├── formatters/                        # Output generation
│   │   │   ├── __init__.py
│   │   │   ├── readme_llm_formatter.py       # XML format per paper
│   │   │   └── knowledge_base_builder.py     # JSON for MCP server
│   │   └── utils/                             # Utilities
│   │       ├── __init__.py
│   │       └── file_scanner.py               # Recursive doc scanning
│   ├── mcp_servers/
│   │   ├── __init__.py
│   │   ├── documentor_server.py               # NEW: Stage 2 MCP server
│   │   ├── retrieval/
│   │   │   ├── __init__.py
│   │   │   ├── keyword_search.py              # NEW
│   │   │   ├── vector_search.py               # NEW
│   │   │   └── hybrid_search.py               # NEW
│   │   └── schemas.py                         # MCP tool schemas
│   ├── schemas/
│   │   ├── ...                                # Existing schemas
│   │   └── readme_llm_schemas.py              # Knowledge base schemas (if shared)
│   └── cli.py                                  # Add mcp & readme-llm commands
├── data/
│   └── <run_id>/
│       ├── repository/
│       ├── results/
│       │   ├── extraction/
│       │   ├── api_completeness/
│       │   ├── api_validation/
│       │   ├── code_validation/
│       │   └── clarity_validation/
│       └── readme_llm/                         # NEW
│           ├── README.LLM                      # Monolithic (paper format)
│           ├── knowledge_base/                 # Structured for MCP
│           │   ├── index.json
│           │   ├── library_overview.json
│           │   ├── api_catalog/
│           │   ├── examples_db/
│           │   ├── embeddings/                 # Optional
│           │   └── metadata.json
│           └── feedback/                       # Continuous improvement
│               └── issues.jsonl
```

### Schema Definitions

#### Standalone System Schemas

```python
# stackbench/readme_llm/schemas.py

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from pathlib import Path

class CodeExample(BaseModel):
    """
    Extracted code example from documentation

    Used during extraction phase before matching to APIs
    """
    example_id: str  # Generated hash or sequential ID
    code: str
    language: str  # python, typescript, javascript, go, rust
    source_file: str  # Path to documentation file
    line_number: int  # Location in source file
    is_complete: bool  # Full program vs snippet
    is_snippet: bool  # True if from external file (MkDocs --8<--)
    apis_mentioned: List[str]  # Detected API calls (may be incomplete)

    class Config:
        json_schema_extra = {
            "example": {
                "example_id": "quickstart_ex1",
                "code": "import lancedb\ndb = lancedb.connect('./my_db')",
                "language": "python",
                "source_file": "docs/quickstart.md",
                "line_number": 42,
                "is_complete": True,
                "is_snippet": False,
                "apis_mentioned": ["lancedb.connect"]
            }
        }

class Parameter(BaseModel):
    """Function/method parameter"""
    name: str
    type: str
    required: bool
    default: Optional[str] = None
    description: str

class IntrospectionResult(BaseModel):
    """
    Result from running introspection template

    Output of stackbench/introspection_templates/<language>_introspect.py
    """
    language: str
    library_name: str
    library_version: str
    apis: List[Dict]  # Raw API data from introspection
    timestamp: str
    introspection_method: str  # "inspect.signature", "typescript-parser", etc.

class APIEntry(BaseModel):
    """
    API catalog entry for knowledge base

    Enhanced with examples and metadata
    """
    api_id: str  # Fully qualified name (e.g., "lancedb.connect")
    language: str  # python, typescript, javascript, go, rust
    signature: str  # Full function signature
    description: str
    parameters: List[Parameter]
    returns: Optional[Dict] = None
    examples: List[str]  # References to example IDs
    importance_score: float = Field(ge=0.0, le=1.0, default=0.5)
    tags: List[str]  # ["connection", "initialization", "database"]
    related_apis: List[str]  # Other APIs often used together
    search_keywords: List[str]  # For keyword search
    source: Literal["introspection", "documentation", "hybrid"] = "introspection"

    class Config:
        json_schema_extra = {
            "example": {
                "api_id": "lancedb.connect",
                "language": "python",
                "signature": "connect(uri: str, **kwargs) -> Connection",
                "description": "Connect to a LanceDB instance",
                "parameters": [
                    {
                        "name": "uri",
                        "type": "str",
                        "required": True,
                        "description": "Path or URI to database"
                    }
                ],
                "returns": {
                    "type": "Connection",
                    "description": "Connection object"
                },
                "examples": ["quickstart_ex1", "connection_ex2"],
                "importance_score": 0.95,
                "tags": ["connection", "initialization"],
                "related_apis": ["Connection.close"],
                "search_keywords": ["connect", "database", "initialize"],
                "source": "introspection"
            }
        }

class ExampleEntry(BaseModel):
    """
    Examples database entry for knowledge base

    Enhanced CodeExample with API matching and metadata
    """
    example_id: str
    title: str
    code: str
    language: str
    apis_used: List[str]  # After matching to introspected APIs
    use_case: str  # initialization, search, update, etc.
    complexity: Literal["beginner", "intermediate", "advanced"]
    tags: List[str]
    prerequisites: List[str]  # ["pip install lancedb"]
    expected_output: Optional[str] = None
    validated: bool  # True if from Stackbench validation, False if standalone
    execution_context: Dict  # version, timestamp, validation_method
    source_file: str
    line_number: int

    class Config:
        json_schema_extra = {
            "example": {
                "example_id": "quickstart_ex1",
                "title": "Connect to database and create table",
                "code": "import lancedb\ndb = lancedb.connect('./my_db')",
                "language": "python",
                "apis_used": ["lancedb.connect"],
                "use_case": "initialization",
                "complexity": "beginner",
                "tags": ["quickstart", "setup"],
                "prerequisites": ["pip install lancedb"],
                "expected_output": None,
                "validated": False,
                "execution_context": {
                    "library_version": "0.25.2",
                    "generation_method": "standalone",
                    "timestamp": "2025-01-15T10:30:00Z"
                },
                "source_file": "docs/quickstart.md",
                "line_number": 42
            }
        }

class LibraryOverview(BaseModel):
    """High-level library information"""
    name: str
    version: str
    languages: List[str]
    domain: Optional[str] = None  # "vector database", "web framework", etc.
    description: str
    architecture: Optional[str] = None
    key_concepts: List[str]
    quickstart_summary: str

class KnowledgeBase(BaseModel):
    """
    Complete knowledge base structure for MCP server

    Generated by both standalone and integration modes
    """
    library_overview: LibraryOverview
    api_catalog: Dict[str, Dict[str, APIEntry]]  # {language: {api_id: entry}}
    examples_db: Dict[str, Dict[str, ExampleEntry]]  # {language: {example_id: entry}}
    concept_graph: Optional[Dict] = None  # Future: relationship graph
    metadata: Dict  # generation_mode, timestamp, stats

    class Config:
        json_schema_extra = {
            "example": {
                "library_overview": {
                    "name": "lancedb",
                    "version": "0.25.2",
                    "languages": ["python"],
                    "domain": "vector database",
                    "description": "Fast vector database for AI apps",
                    "key_concepts": ["vector search", "ANN indexes", "columnar storage"],
                    "quickstart_summary": "Install, connect, create table, search"
                },
                "api_catalog": {
                    "python": {
                        "lancedb.connect": "... APIEntry object ..."
                    }
                },
                "examples_db": {
                    "python": {
                        "quickstart_ex1": "... ExampleEntry object ..."
                    }
                },
                "metadata": {
                    "generation_mode": "standalone",
                    "timestamp": "2025-01-15T10:30:00Z",
                    "total_apis": 42,
                    "total_examples": 87,
                    "languages": ["python"]
                }
            }
        }
```

#### Differences from Stackbench Schemas

The standalone system uses **distinct schemas** from Stackbench's validation schemas:

| Aspect | Stackbench Schemas | README.LLM Schemas |
|--------|-------------------|-------------------|
| Purpose | Validation results | Knowledge base structure |
| Focus | Accuracy, errors | Usability, retrieval |
| Language | Python only | Multi-language |
| Validation | Required | Optional |
| Examples | Validated only | All extracted |
| Metadata | Validation status | Search/ranking info |

**No namespace collision**: The two systems can coexist. Stackbench uses `stackbench/schemas/`, README.LLM uses `stackbench/readme_llm/schemas.py`.

---

## Continuous Improvement Loop

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Uses MCP Server                    │
│   • Queries APIs via find_api                               │
│   • Gets examples via get_examples                          │
│   • Reports issues via report_issue                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Feedback Logged (issues.jsonl)                 │
│   • Query that failed                                       │
│   • Which APIs were attempted                               │
│   • Error messages                                          │
│   • Context (previous tool calls)                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         Weekly/Monthly Analysis (mcp analyze-feedback)      │
│   • Top 10 failing queries → Add missing examples          │
│   • Common error patterns → Improve API descriptions        │
│   • Poor search results → Retune ranking weights            │
│   • API gaps → Add to Stackbench validation                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│      Update Documentation & Re-run Stackbench Pipeline      │
│   1. Fix documentation issues identified in feedback        │
│   2. Re-run: stackbench run ...                             │
│   3. Regenerate: stackbench readme-llm generate ...         │
│   4. Restart MCP server with updated knowledge base         │
└─────────────────────────────────────────────────────────────┘
                            ↓
                     [Improved Accuracy]
```

### Feedback Analysis Tool

```python
# stackbench/mcp_servers/feedback_analyzer.py

class FeedbackAnalyzer:
    """
    Analyze accumulated feedback to identify improvement opportunities

    Implements paper's iterative improvement concept [1, Section 2.1]
    """

    def analyze(self, feedback_path: str) -> Dict:
        """
        Analyze issues.jsonl and generate improvement recommendations
        """
        issues = self._load_issues(feedback_path)

        analysis = {
            "summary": self._generate_summary(issues),
            "top_failing_queries": self._identify_top_failures(issues),
            "missing_examples": self._identify_missing_examples(issues),
            "unclear_apis": self._identify_unclear_apis(issues),
            "search_quality": self._analyze_search_quality(issues),
            "recommendations": self._generate_recommendations(issues)
        }

        return analysis

    def _identify_top_failures(self, issues: List[dict]) -> List[dict]:
        """
        Find most common failing queries
        """
        query_counts = {}
        for issue in issues:
            query = issue['query']
            query_counts[query] = query_counts.get(query, 0) + 1

        sorted_queries = sorted(
            query_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {"query": q, "count": c, "recommendation": self._suggest_fix(q, issues)}
            for q, c in sorted_queries[:10]
        ]

    def _suggest_fix(self, query: str, issues: List[dict]) -> str:
        """
        Suggest specific fix based on issue patterns
        """
        related_issues = [i for i in issues if i['query'] == query]

        error_types = [i['issue_type'] for i in related_issues]
        most_common = max(set(error_types), key=error_types.count)

        if most_common == 'missing_example':
            return f"Add example for: {query}"
        elif most_common == 'unclear_docs':
            apis = [api for i in related_issues for api in i.get('apis_tried', [])]
            return f"Improve description for: {', '.join(set(apis))}"
        elif most_common == 'error':
            return f"Validate documentation for: {query}"
        else:
            return "Investigate further"
```

### Report Generation

```bash
$ stackbench mcp analyze-feedback \
    --knowledge-base data/abc-123/readme_llm/knowledge_base/ \
    --output-report feedback_report.json

Feedback Analysis Report
========================

Summary:
- Total issues: 234
- Unique queries: 87
- Time period: 2025-01-01 to 2025-01-15

Top Failing Queries:
1. "How do I update vectors in a table?" (23 failures)
   → Recommendation: Add example for table update operations

2. "Filter search results by metadata" (18 failures)
   → Recommendation: Improve description for Table.search, add filtering example

3. "Delete table from database" (15 failures)
   → Recommendation: Add example for: delete table

Missing Examples (15 gaps identified):
- Table update operations
- Metadata filtering
- Index configuration
- ...

Search Quality Issues:
- 12 queries returned low-relevance results
- Suggested: Retune importance weights for search APIs

Recommendations:
✓ Add 15 missing examples to documentation
✓ Improve descriptions for 8 APIs
✓ Re-validate 3 APIs (potential signature mismatches)
✓ Retune search weights based on query patterns
```

---

## Implementation Roadmap

### Phase 1: Standalone System Foundation (3 weeks)

**Week 1: Core Extraction Components**
- [ ] Create `stackbench/readme_llm/` directory structure
- [ ] Implement schemas.py with all Pydantic models
- [ ] Build LanguageDetector (auto-detect languages from code blocks)
- [ ] Build CodeExampleExtractor (regex + parsing)
  - [ ] Standard markdown code blocks
  - [ ] MkDocs snippet resolution (`--8<--`)
  - [ ] reStructuredText literalinclude
- [ ] Build FileScanner (recursive doc directory scanning)
- [ ] Write extraction tests

**Week 2: Introspection & Matching**
- [ ] Build IntrospectionRunner (wrapper for templates)
  - [ ] Reuse `stackbench/introspection_templates/python_introspect.py`
  - [ ] Create isolated environments (venv, npm)
  - [ ] Parse introspection output
- [ ] Build APIExampleMatcher
  - [ ] Import detection (import X, from Y import Z)
  - [ ] API call detection (X.method(), function())
  - [ ] Bi-directional linking (API↔Examples)
- [ ] Add complexity inference (beginner/intermediate/advanced)
- [ ] Write introspection and matching tests

**Week 3: Output Generation & CLI**
- [ ] Build ReadMeLLMFormatter (XML format per paper)
  - [ ] Rules section
  - [ ] Library description
  - [ ] Context sections (interleaved format)
- [ ] Build KnowledgeBaseBuilder (JSON for MCP)
  - [ ] API catalog structure
  - [ ] Examples database
  - [ ] Library overview
- [ ] Implement ReadMeLLMGeneratorAgent (orchestration)
- [ ] Add CLI command: `stackbench readme-llm generate`
  - [ ] Standalone mode (primary)
  - [ ] Integration mode (from Stackbench run)
- [ ] End-to-end tests with sample library

**Deliverable**: Working standalone README.LLM generator for Python libraries

---

### Phase 2: MCP Server Core (3 weeks)

**Week 1: Tools 1 & 2 (Overview + find_api)**
- [ ] Set up MCP server boilerplate
- [ ] Implement `get_library_overview` tool
- [ ] Implement keyword-based retrieval
- [ ] Implement `find_api` tool
- [ ] Add usage logging
- [ ] Write integration tests

**Week 2: Tool 3 (get_examples)**
- [ ] Implement example matching algorithm
- [ ] Build task similarity scoring
- [ ] Implement `get_examples` tool
- [ ] Add complexity and API filtering
- [ ] Write example retrieval tests

**Week 3: Tool 4 (report_issue)**
- [ ] Set up feedback database (JSONL)
- [ ] Implement `report_issue` tool
- [ ] Build suggestion generation
- [ ] Add session context tracking
- [ ] Implement feedback analyzer
- [ ] Add CLI: `stackbench mcp analyze-feedback`

**Deliverable**: Working MCP server with all 4 tools

---

### Phase 3: Advanced Search (2 weeks)

**Week 1: Vector Search Integration**
- [ ] Add sentence-transformers dependency (optional)
- [ ] Implement VectorRetrieval class
- [ ] Build embedding generation pipeline
- [ ] Add embedding storage and loading
- [ ] Integrate with knowledge base generator
- [ ] Add flag: `--generate-embeddings`

**Week 2: Hybrid Search & Optimization**
- [ ] Implement hybrid retrieval (RRF fusion)
- [ ] Build re-ranking with importance scores
- [ ] Optimize search performance
- [ ] Add caching for frequently accessed APIs
- [ ] Benchmark search quality
- [ ] Tune ranking parameters

**Deliverable**: Production-ready retrieval with semantic search

---

### Phase 4: Multi-Language Support (2 weeks)

**Week 1: TypeScript/JavaScript Support**
- [ ] Create `typescript_introspect.ts` template
  - [ ] Use typescript-parser or similar
  - [ ] Extract function/class signatures
  - [ ] Handle type definitions
- [ ] Update CodeExampleExtractor for TS/JS patterns
- [ ] Update APIExampleMatcher for import detection
  - [ ] ES6 imports (import X from 'Y')
  - [ ] CommonJS requires (const X = require('Y'))
- [ ] Test with popular libraries (e.g., Express, React)

**Week 2: Go & Rust Support**
- [ ] Create `go_introspect.go` template
  - [ ] Use go/parser package
  - [ ] Extract exported functions/types
- [ ] Create `rust_introspect.rs` template
  - [ ] Use syn crate
  - [ ] Extract public functions/structs
- [ ] Update extractors and matchers for Go/Rust patterns
- [ ] Add language-specific README.LLM formatting
- [ ] Cross-language testing

**Deliverable**: Full multi-language README.LLM generation (Python, TS, JS, Go, Rust)

---

### Phase 5: Analytics & Polish (1 week)

- [ ] Build comprehensive feedback analysis
- [ ] Create visualization for feedback trends
- [ ] Add automated improvement recommendations
- [ ] Write end-to-end documentation
- [ ] Create example walkthroughs for each language
  - [ ] Python: LanceDB
  - [ ] TypeScript: Express.js or similar
  - [ ] Go: Popular library
- [ ] Performance optimization
- [ ] Final testing and bug fixes
- [ ] Integration testing with Stackbench validation (optional mode)

**Deliverable**: Production-ready multi-language ReadMe.LLM + MCP system

---

## Success Metrics

### Quantitative Metrics

Following the paper's evaluation approach [1, Section 3]:

1. **Code Generation Success Rate**
   - Baseline (no context): Expect ~30%
   - With README.LLM: Target 80-100%
   - Measure across multiple LLMs (Claude, GPT-4, etc.)

2. **Search Accuracy** (MCP Server)
   - Top-1 Accuracy: % of queries where best result is in position 1
   - Top-3 Accuracy: % of queries with relevant API in top 3
   - Mean Reciprocal Rank (MRR)

3. **Example Relevance**
   - % of examples that solve user's stated task
   - User feedback ratings (implicit via report_issue)

4. **Error Reduction**
   - % decrease in reported issues over time
   - Improvement in search quality scores

5. **Response Time**
   - API lookup latency (target: <100ms)
   - Example retrieval latency (target: <200ms)
   - MCP server overhead

### Qualitative Metrics

1. **Documentation Coverage**
   - % of APIs with examples
   - % of use cases covered
   - Completeness score from API Completeness Agent

2. **Feedback Quality**
   - Actionability of reported issues
   - Time to resolve common issues
   - Documentation improvement velocity

### Benchmark Against Paper

| Metric | ReadMe.LLM Paper [1] | Our Target |
|--------|---------------------|------------|
| Baseline success | 30% | 30-40% |
| With human docs | 20-40% | N/A (skip) |
| With LLM docs | 80-100% | 80-100% |
| Example coverage | Manual | Automated |
| Validation | Manual testing | Stackbench validation |

---

## Future Enhancements

### Short-term (Next 6 months)

1. **Enhanced Language Support**
   - ✅ Multi-language (Python, TS, JS, Go, Rust) - Now in Phase 4
   - Java, C#, Ruby support
   - Language-specific best practices in README.LLM
   - Cross-language example matching

2. **Auto-update Detection**
   - Monitor library releases
   - Trigger automatic re-validation
   - Update README.LLM and knowledge base

3. **Enhanced Analytics**
   - Query clustering to identify patterns
   - A/B testing different README.LLM formats
   - User journey analysis

### Long-term (1+ year)

1. **Active Learning Loop**
   - Use feedback to improve ranking models
   - Fine-tune embeddings on library-specific data
   - Personalized recommendations

2. **Cross-library Reasoning**
   - "Users who used API X also needed API Y"
   - Suggest alternative libraries
   - Migration guides between versions

3. **AI-powered Documentation Generation**
   - LLM-generated descriptions (validated by humans)
   - Automatic example synthesis
   - Code pattern detection

---

## Open Questions

1. **Embedding Model Selection**
   - all-MiniLM-L6-v2 (80MB, fast) vs. all-mpnet-base-v2 (420MB, more accurate)?
   - Domain-specific fine-tuning worth it?

2. **Example Selection Strategy**
   - How many examples per API?
   - Simple vs. complex example ratio?
   - Full programs vs. snippets?

3. **Monolithic vs. Modular**
   - Should README.LLM be split by module/package?
   - Single large context vs. multiple smaller contexts?

4. **Update Frequency**
   - How often to regenerate README.LLM?
   - Delta updates vs. full regeneration?

5. **MCP Server Scaling**
   - Single server for all libraries?
   - Per-library servers?
   - Multi-tenant architecture?

---

## References

[1] Wijaya, S., Bolano, J., Gomez Soteres, A., Kode, S., Huang, Y., & Sahai, A. (2025). ReadMe.LLM: A Framework to Help LLMs Understand Your Library. *arXiv preprint arXiv:2504.09798v3*.

**Key Sections Referenced**:
- Section 1: Challenge and motivation for LLM-oriented docs
- Section 2: ReadMe.LLM structure (Rules, Description, Code Snippets)
- Section 2.1: Developer workflow and iterative improvement
- Section 3: Experimental results (30% → 100% success)
- Section 3.1.1: Supervision case study findings
- Section 4: Discussion on XML tags and prompt engineering
- Appendix B: Instructions for creating ReadMe.LLM
- Appendix C: Full ReadMe.LLM examples

**Paper URL**: https://arxiv.org/abs/2504.09798v3

---

## Appendix A: Example README.LLM Output

**Sample generated README.LLM for LanceDB** (abbreviated):

```xml
<ReadMe.LLM>

<rules>
Rule number 1: When you are unsure about something, ask the user what information you need.
Rule number 2: Reuse LanceDB functions and code when applicable.
Rule number 3: Consider library dependencies when generating code solutions.
Rule number 4: All examples provided have been validated to work with LanceDB version 0.25.2.
</rules>

<context_description>
The context will be for the LanceDB library. LanceDB is a vector database built on the Lance columnar format, designed for AI applications requiring fast similarity search. The context is organized into different numbered sections using XML tags. Within each section, there is a description, function signature, and validated examples.
</context_description>

<context_1>
<context_1_description>
The lancedb.connect function establishes a connection to a LanceDB instance. It can connect to local directories or remote URIs, creating the database if it doesn't exist. This is the entry point for all LanceDB operations.
</context_1_description>

<context_1_function>
lancedb.connect(uri: str, **kwargs) -> DBConnection

Parameters:
- uri (str, required): Path to local directory or remote URI for the database
- **kwargs: Additional connection options

Returns:
DBConnection - Connection object to interact with the database
</context_1_function>

<context_1_example>
import lancedb

# Connect to local database (creates if doesn't exist)
db = lancedb.connect("./my_lancedb")

# Connect to remote database
db = lancedb.connect("s3://my-bucket/lancedb")
</context_1_example>
</context_1>

<context_2>
<context_2_description>
The DBConnection.create_table method creates a new table in the database from various data sources including pandas DataFrames, PyArrow tables, or iterators. Tables are the primary structure for storing and querying vector data.
</context_2_description>

<context_2_function>
DBConnection.create_table(
    name: str,
    data: Union[pd.DataFrame, pa.Table, Iterator],
    schema: Optional[pa.Schema] = None,
    mode: str = "create"
) -> Table

Parameters:
- name (str, required): Name for the new table
- data (DataFrame|Table|Iterator, required): Data to populate the table
- schema (pa.Schema, optional): Explicit schema definition
- mode (str, optional): Creation mode - "create", "overwrite", or "append"

Returns:
Table - The created table object
</context_2_function>

<context_2_example>
import lancedb
import pandas as pd

# Create from pandas DataFrame
db = lancedb.connect("./my_lancedb")
data = pd.DataFrame({
    "vector": [[1.0, 2.0], [3.0, 4.0]],
    "item": ["a", "b"]
})
table = db.create_table("my_vectors", data)

# Validated on version 0.25.2
</context_2_example>
</context_2>

<!-- Additional context sections for top 50 APIs... -->

</ReadMe.LLM>
```

---

## Appendix B: MCP Server Usage Example

**Sample agent interaction with DocuMentor MCP server**:

```
Agent: I need to search for similar vectors in LanceDB

MCP Call: get_library_overview(aspect="quickstart")
Response:
  ## Quick Start
  1. Install: `pip install lancedb`
  2. Connect: `db = lancedb.connect("./my_db")`
  3. Create table: `table = db.create_table("vectors", data)`
  4. Search: `results = table.search([1.0, 2.0]).limit(5)`

Agent: How do I search for vectors?

MCP Call: find_api(query="search for similar vectors")
Response:
  ### 1. Table.search
  **Signature:** `search(query: List[float], limit: int = 10) -> LanceQueryBuilder`
  **Description:** Search for vectors similar to the query vector
  **Parameters:**
    - query (List[float], required): Query vector
    - limit (int, optional): Maximum results to return
  **Relevance:** 0.95 | **Importance:** 0.92

Agent: Can you show me an example?

MCP Call: get_examples(
  task_description="search for similar vectors",
  apis_involved=["Table.search"]
)
Response:
  ### Example 1: Basic vector search
  **Code:**
  ```python
  import lancedb

  db = lancedb.connect("./my_db")
  table = db.open_table("vectors")

  # Search for similar vectors
  results = table.search([0.1, 0.2, 0.3]).limit(5).to_list()
  ```
  ✓ *Validated on version 0.25.2*

Agent: [Tries the code, gets error]

MCP Call: report_issue(
  query="search for similar vectors",
  apis_tried=["Table.search"],
  error_message="AttributeError: 'LanceQueryBuilder' has no attribute 'to_list'",
  issue_type="error"
)
Response:
  Thank you for reporting!
  **Suggestions:**
  - Try: results.to_arrow() or results.to_pandas()
  - Check version compatibility
  Issue logged for documentation improvement.
```

**Result**: Feedback loop identifies that example needs correction, improving documentation quality over time.

---

## Appendix C: Integration with Existing Stackbench Agents

**Data flow from existing agents to README.LLM generator**:

```
Extraction Agent
├─ APIs with signatures → API Catalog
├─ Code examples → Examples DB (filtered by validation)
└─ Descriptions → Context sections

API Completeness Agent
├─ Importance scores → API ranking in README.LLM
├─ Documented APIs → Coverage metadata
└─ Undocumented APIs → Gaps report

API Validation Agent
├─ Validated signatures → Guaranteed accuracy
└─ Validation errors → Exclude from README.LLM

Code Validation Agent
├─ Passed examples → Include in Examples DB
├─ Failed examples → Exclude from README.LLM
└─ Execution metadata → "Validated on version X.Y.Z"

Clarity Validation Agent
├─ Clarity scores → Prioritize clear descriptions
├─ Issue locations → Improve before README.LLM
└─ Suggestions → Enhance context sections
```

---

**Document Version**: 2.0
**Last Updated**: 2025-11-03
**Authors**: Stackbench Team
**Status**: Planning Document - Standalone Architecture

**Major Changes in v2.0**:
- ✅ Standalone system architecture under `stackbench/readme_llm/`
- ✅ Multi-language support (Python, TypeScript, JavaScript, Go, Rust)
- ✅ Reuses existing introspection templates
- ✅ Comprehensive code extraction (regex + parsing)
- ✅ MkDocs snippet resolution
- ✅ Two operational modes (Standalone + Integration)
- ✅ Updated schemas independent of Stackbench validation
- ✅ Extended implementation roadmap (11 weeks → 5 phases)
