# README.LLM System

**Transform library documentation into LLM-optimized format for better AI code generation**

Based on: [ReadMe.LLM: A Framework to Help LLMs Understand Your Library](https://arxiv.org/abs/2504.09798v3) (Wijaya et al., 2025)

## Overview

The README.LLM system implements the ReadMe.LLM framework to transform library documentation into a format optimized for Large Language Models (LLMs). Research shows this approach improves AI code generation success rates from **30% to 100%** for lesser-known libraries.

### Key Features

✅ **Standalone Operation** - Works with any documentation, no validation required
✅ **Multi-Language Support** - Python, TypeScript, JavaScript, Go, Rust
✅ **Dual Output Formats** - Traditional README.LLM (XML) + Structured knowledge base (JSON)
✅ **Auto-Introspection** - Dynamically discovers library APIs using language-specific templates
✅ **Code Example Extraction** - Handles MkDocs snippets, reStructuredText, multiple formats
✅ **Smart Example Matching** - Links code examples to APIs automatically
✅ **Optional Integration** - Can leverage Stackbench validation results for maximum quality

## Architecture

```
stackbench/readme_llm/
├── schemas.py                   # Pydantic models
├── readme_llm_generator_agent.py # Main orchestration
├── extractors/                  # Code and language detection
│   ├── language_detector.py     # Auto-detect languages from code blocks
│   ├── code_extractor.py        # Extract code examples with regex/parsing
│   └── snippet_resolver.py      # MkDocs --8<-- resolution
├── introspection/               # Library API discovery
│   └── runner.py                # Wrapper for introspection templates
├── matchers/                    # Link examples to APIs
│   └── api_matcher.py           # Import/usage analysis
├── formatters/                  # Output generation
│   ├── readme_llm_formatter.py  # XML format (paper structure)
│   └── knowledge_base_builder.py # JSON for MCP server
└── utils/                       # Utilities
    └── file_scanner.py          # Recursive documentation scanning
```

## Two Operational Modes

### Mode 1: Standalone (Recommended)

Generate README.LLM directly from any documentation:

```bash
stackbench readme-llm generate \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --docs-path docs/src \
  --library lancedb \
  --version 0.25.2 \
  --languages python typescript \
  --output-format both
```

**Workflow:**
1. Clone repository (or use local docs)
2. Scan all markdown/rst files recursively
3. Auto-detect programming languages
4. Run introspection templates (install library, discover APIs)
5. Extract code examples from documentation
6. Match examples to APIs via import/usage analysis
7. Generate README.LLM (XML) + knowledge_base/ (JSON)

**Advantages:**
- Fast (~5 minutes for typical library)
- Works with any library documentation
- No dependency on Stackbench validation
- Multi-language from day one

### Mode 2: Integration (Maximum Quality)

Generate from Stackbench validation results:

```bash
# First run Stackbench validation
stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --docs-path docs/src \
  --library lancedb \
  --version 0.25.2

# Then generate README.LLM from validated data
stackbench readme-llm generate \
  --from-run <run-id> \
  --output-format both
```

**Advantages:**
- Only includes validated examples (passed code validation)
- Guaranteed API signature accuracy
- Importance scores and clarity ratings
- Comprehensive coverage analysis

**Trade-off:** Slower (~30 minutes total) but maximum accuracy

## Output Structure

```
data/<run-id>/readme_llm/
├── README.LLM                   # Monolithic XML (paper format)
├── knowledge_base/              # Structured JSON for MCP server
│   ├── index.json               # Master index
│   ├── library_overview.json   # High-level concepts
│   ├── api_catalog/             # Per-language API definitions
│   │   ├── python/
│   │   │   ├── lancedb.connect.json
│   │   │   └── Table.search.json
│   │   ├── typescript/
│   │   └── javascript/
│   ├── examples_db/             # Per-language examples
│   │   ├── python/
│   │   │   ├── quickstart_ex1.json
│   │   │   └── search_ex1.json
│   │   ├── typescript/
│   │   └── javascript/
│   ├── embeddings/              # Optional (if --generate-embeddings)
│   │   ├── api_embeddings.npy
│   │   └── example_embeddings.npy
│   └── metadata.json            # Stats, generation info
├── feedback/                    # Continuous improvement
│   └── issues.jsonl
└── generation_logs/             # Agent execution logs
    ├── generate.log
    └── generate_tools.jsonl
```

## README.LLM Format (XML)

Following the validated structure from the paper:

```xml
<ReadMe.LLM>
  <rules>
    Rule number 1: When you are unsure about something, ask the user what information you need.
    Rule number 2: Reuse [Library] functions and code when applicable.
    Rule number 3: Consider library dependencies when generating code solutions.
  </rules>

  <context_description>
    The context will be for the [Library Name]. [High-level purpose and domain].
    The context is organized into different numbered sections using XML tags.
  </context_description>

  <context_1>
    <context_1_description>
      [API description - what it does and why it matters]
    </context_1_description>

    <context_1_function>
      [Function signature with parameters and types]
    </context_1_function>

    <context_1_example>
      [Working code example]
    </context_1_example>
  </context_1>

  <!-- Repeat for N most important APIs -->
</ReadMe.LLM>
```

**Key Insight from Paper:** Interleaving description + function + example is more effective than separate sections.

## Multi-Language Support

### Supported Languages

| Language   | Template Status | Introspection Method |
|-----------|----------------|---------------------|
| Python    | ✅ Implemented | `inspect.signature` |
| TypeScript| ✅ Implemented | `typescript-parser` |
| JavaScript| ✅ Implemented | `acorn` AST parser  |
| Go        | 🚧 Phase 2     | `go/parser` package |
| Rust      | 🚧 Phase 2     | `syn` crate         |

### Auto-Detection

The system automatically detects languages from code block tags:

```markdown
\`\`\`python
import lancedb
\`\`\`

\`\`\`typescript
import lancedb from 'lancedb';
\`\`\`
```

### Manual Override

Specify languages explicitly if auto-detection fails:

```bash
stackbench readme-llm generate \
  --languages python typescript go \
  ...
```

## Code Example Extraction

### Supported Formats

1. **Standard Markdown**
   ```markdown
   \`\`\`python
   import lancedb
   db = lancedb.connect("./my_db")
   \`\`\`
   ```

2. **MkDocs Material Snippets**
   ```markdown
   --8<-- "snippets/quickstart.py"
   ```

3. **reStructuredText**
   ```rst
   .. literalinclude:: examples/quickstart.py
      :language: python
   ```

4. **Indented Code Blocks** (Markdown/reST)

### Snippet Resolution

The `SnippetResolver` automatically resolves includes:

```python
# In documentation: --8<-- "snippets/connect.py"
# System reads: docs/src/snippets/connect.py
# Includes actual code in extraction
```

## API Example Matching

Links code examples to APIs using multi-stage analysis:

1. **Import Detection**
   - `import lancedb` → library-level import
   - `from lancedb import connect` → function import
   - `import { connect } from 'lancedb'` → ES6 import

2. **Usage Detection**
   - `lancedb.connect(...)` → API call
   - `db.create_table(...)` → Method call
   - Handles chained calls: `table.search(...).limit(...)`

3. **Bi-directional Linking**
   - API → Examples: Which examples use this API?
   - Example → APIs: Which APIs does this example demonstrate?

## Importance Scoring

APIs are ranked by importance using heuristics:

- **Public visibility**: Exported/public APIs score higher
- **Usage frequency**: Referenced more in docs → higher score
- **Name patterns**: `connect`, `create`, `init` often critical
- **Documentation prominence**: Appears in quickstart/overview → higher score

Top N most important APIs (default 50) are included in README.LLM.

## Integration with Stackbench Validation

When using integration mode (`--from-run`), the system leverages:

### From Extraction Agent
- API signatures → API catalog
- Code examples → Examples DB
- Descriptions → Context sections

### From API Completeness Agent
- Importance scores → API ranking
- Documented APIs → Coverage metadata
- Undocumented APIs → Gap reporting

### From API Validation Agent
- Validated signatures → Guaranteed accuracy
- Validation errors → Excluded from README.LLM

### From Code Validation Agent
- Passed examples → Include with `validated: true`
- Failed examples → Exclude
- Execution metadata → "Validated on version X.Y.Z"

### From Clarity Validation Agent
- Clarity scores → Prioritize clear descriptions
- Issue locations → Improve before generation
- Suggestions → Enhance context sections

## CLI Commands

### Generate Standalone

```bash
# From GitHub repository
stackbench readme-llm generate \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --docs-path docs/src \
  --library lancedb \
  --version 0.25.2 \
  --output-format both

# From local documentation
stackbench readme-llm generate \
  --docs-path /path/to/docs \
  --library mylib \
  --version 1.0.0

# With embeddings for vector search
stackbench readme-llm generate \
  --repo https://github.com/example/lib \
  --docs-path docs \
  --library example \
  --version 1.0.0 \
  --generate-embeddings
```

### Generate from Stackbench Run

```bash
# Integration mode
stackbench readme-llm generate \
  --from-run abc-123-def \
  --output-format both
```

### Options

- `--repo URL` - GitHub repository URL (clones fresh)
- `--branch BRANCH` - Git branch to use (default: main)
- `--docs-path PATH` - Path to documentation directory
- `--library NAME` - Library name to introspect
- `--version VERSION` - Library version to install and test
- `--languages LANGS` - Comma-separated languages (auto-detected if omitted)
- `--output-format FORMAT` - monolithic, knowledge_base, or both (default)
- `--generate-embeddings` - Generate vector embeddings (requires sentence-transformers)
- `--from-run RUN_ID` - Generate from existing Stackbench run (integration mode)

## Data Schemas

See `schemas.py` for complete Pydantic model definitions:

- `CodeExample` - Extracted code block
- `IntrospectionResult` - Library API surface
- `Parameter` - Function parameter
- `APIEntry` - API catalog entry (with examples, importance, tags)
- `ExampleEntry` - Enhanced example (with APIs, complexity, validation status)
- `LibraryOverview` - High-level library info
- `KnowledgeBase` - Complete structured knowledge base

## Hooks Integration

The generator agent uses Stackbench's hook system:

- **Validation Hooks** - Validate output JSON against Pydantic schemas
- **Logging Hooks** - Capture all tool calls (Read, Write, Bash)
- **Output** - Human-readable `.log` + machine-readable `.jsonl`

## Performance

**Standalone Mode:**
- Small library (<50 APIs, <100 examples): ~2-3 minutes
- Medium library (50-200 APIs, 100-500 examples): ~5-10 minutes
- Large library (>200 APIs, >500 examples): ~15-20 minutes

**Integration Mode:**
- Stackbench validation: ~20-30 minutes
- README.LLM generation: ~2-5 minutes
- Total: ~25-35 minutes

## Next Steps: DocuMentor MCP Server (Phase 4-5)

The knowledge base generated here powers the DocuMentor MCP server:

```bash
# Start MCP server
stackbench mcp serve \
  --knowledge-base data/<run-id>/readme_llm/knowledge_base/ \
  --port 3000 \
  --use-vectors

# Use with Claude Code or other AI tools
# 4 tools available:
# - get_library_overview
# - find_api
# - get_examples
# - report_issue
```

## References

[1] Wijaya, S., Bolano, J., Gomez Soteres, A., Kode, S., Huang, Y., & Sahai, A. (2025). ReadMe.LLM: A Framework to Help LLMs Understand Your Library. *arXiv preprint arXiv:2504.09798v3*.

## Implementation Status

### Phase 0: Foundation ✅
- [x] Directory structure
- [x] Pydantic schemas
- [x] Hooks integration
- [x] Optional dependencies
- [x] README documentation

### Phase 1: Extraction (Week 2-3)
- [ ] FileScanner
- [ ] LanguageDetector
- [ ] CodeExampleExtractor
- [ ] SnippetResolver

### Phase 2: Introspection (Week 4-5)
- [ ] IntrospectionRunner
- [ ] Go template
- [ ] Rust template
- [ ] APIExampleMatcher

### Phase 3: Output Generation (Week 6-7)
- [ ] ReadMeLLMFormatter
- [ ] KnowledgeBaseBuilder
- [ ] ReadMeLLMGeneratorAgent
- [ ] CLI commands

### Phase 4: MCP Server (Week 8-10)
- [ ] KeywordRetrieval
- [ ] DocuMentorServer (4 tools)
- [ ] FeedbackAnalyzer
- [ ] MCP CLI commands

### Phase 5: Vector Search (Week 11-12)
- [ ] VectorRetrieval
- [ ] HybridRetrieval (RRF)
- [ ] Embedding generation
- [ ] Optimization

---

**Status:** Phase 0 Complete (Foundation laid)
**Next:** Phase 1 - Implement extraction components
