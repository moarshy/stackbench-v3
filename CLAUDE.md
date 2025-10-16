# Stackbench - AI-Driven Documentation Quality Validation

## Motivation

### The Documentation Problem

Documentation is the bridge between a library and its users. Yet, it's often the weakest link in the software development process. Developers frequently encounter:

- **Broken Code Examples** - Copy-pasting examples from docs that fail with syntax or runtime errors
- **Outdated API References** - Function signatures that don't match the actual implementation
- **Missing Parameters** - Required arguments omitted from documentation
- **Phantom APIs** - Documentation for methods that don't exist or were removed
- **Deprecated Patterns** - Tutorials teaching old APIs without migration guidance

These issues waste developer time, erode trust, and create frustration. A single broken example can cost hundreds of developers hours of debugging.

### Why Existing Solutions Fall Short

Traditional documentation tools focus on *generating* documentation from code (JSDoc, Sphinx, etc.) but don't *validate* that handwritten documentation is accurate. Code review catches some issues, but humans miss subtle bugs:

- A parameter with the wrong default value
- An optional parameter marked as required
- An example missing an import statement
- A tutorial using a deprecated method

### The AI Solution

Stackbench uses Claude Code agents to systematically validate documentation quality at scale. By treating documentation validation as an agentic task, we can:

1. **Extract structured data** from unstructured markdown
2. **Validate API signatures** through dynamic code introspection
3. **Execute code examples** in isolated environments
4. **Provide actionable feedback** on what's broken and why

This approach combines the best of static analysis (fast, deterministic) with dynamic testing (catches runtime issues) and AI reasoning (handles ambiguity).

## Architecture

### Three-Agent Pipeline

Stackbench uses a pipeline of specialized Claude Code agents:

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTRACTION AGENT                         │
│  • Reads markdown documentation files                       │
│  • Extracts API signatures (function names, parameters)     │
│  • Extracts code examples (executable snippets)             │
│  • Outputs structured JSON (validated via hooks)            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              API SIGNATURE VALIDATION AGENT                 │
│  • Installs target library in isolated environment          │
│  • Uses Python introspection to get actual signatures       │
│  • Compares documented vs actual parameters                 │
│  • Flags: missing params, wrong types, wrong defaults       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              CODE EXAMPLE VALIDATION AGENT                  │
│  • Creates isolated test environment per example            │
│  • Executes code snippets                                   │
│  • Catches: syntax errors, runtime errors, import issues    │
│  • Reports: success/failure with detailed error messages    │
└─────────────────────────────────────────────────────────────┘
```

### Parallel Processing

The extraction phase processes multiple documents concurrently using worker pools:

- **Default: 5 workers** - Configurable via `--num-workers`
- Each worker runs an independent Claude Code agent
- Results are validated and aggregated
- Enables processing large documentation sets efficiently

### Hook System

Stackbench's innovation is its use of **programmatic Python hooks** via Claude Code:

#### Validation Hooks (PreToolUse)
Run before the agent writes JSON output files:
- Validate against Pydantic schemas
- Ensure required fields are present
- Check data types and nested structures
- **Block invalid writes** - Agent must fix issues before proceeding

#### Logging Hooks (PreToolUse + PostToolUse)
Capture complete execution trace:
- Every tool call (Read, Write, Bash, etc.)
- Input parameters and output results
- Timestamps and execution order
- Errors and failures
- Output format: Human-readable `.log` + machine-readable `.jsonl`

This ensures **data quality by design** - invalid outputs never hit disk.

## What Makes This Powerful

### 1. Dynamic Validation, Not Static Analysis

Stackbench doesn't just parse code - it **runs it**:

```python
# Static analysis would miss this:
def connect(host, port=8080):
    ...

# Docs say:
client.connect("localhost")  # Works!

# But what if the actual signature changed to:
def connect(host, port, timeout=30):  # port is now required!
    ...

# Docs say:
client.connect("localhost")  # Runtime error!
```

Stackbench catches this by actually calling `inspect.signature()` on the imported function.

### 2. Context-Aware Extraction

Claude Code understands documentation conventions:

```markdown
## Quickstart

First, install the library:

\`\`\`bash
pip install lancedb
\`\`\`

Then connect to a database:

\`\`\`python
import lancedb
db = lancedb.connect("./data")
\`\`\`
```

The agent understands:
- The bash block is an installation instruction (not a code example)
- The Python block is executable code
- `import lancedb` is a dependency
- `lancedb.connect` is an API signature to validate

### 3. Self-Healing Through Feedback

Hooks provide immediate feedback:

```
❌ Validation Hook Error:
   File: quickstart_analysis.json
   Issue: Missing required field 'param_types' in signature #3

Agent Response:
   "I see the issue - I forgot to extract parameter types.
    Let me re-analyze that function signature..."
```

The agent learns from validation errors and fixes them in the next iteration.

### 4. Audit Trail

Every agent run produces:
- **Extraction outputs** - Structured JSON of what was found
- **Validation outputs** - Detailed pass/fail results
- **Agent logs** - Human-readable execution trace
- **Tools logs** - Machine-readable JSONL for analysis

This enables:
- Debugging agent behavior
- Tracking down validation failures
- Analyzing patterns (e.g., "90% of errors are missing imports")
- Building training data for future improvements

## Implementation Details

### Technology Stack

**Core:**
- Python 3.11+ (asyncio for concurrency)
- Claude Code CLI (agent execution)
- Claude Agent SDK (programmatic hooks)

**CLI:**
- Typer (command-line interface)
- Rich (beautiful terminal output)

**Frontend:**
- React 19 + TypeScript
- Vite (build tool)
- Tailwind CSS (styling)

**Data Validation:**
- Pydantic (schema validation)
- JSON + JSONL (structured outputs)

### Key Design Decisions

#### Why Claude Code?

1. **Tool use** - Can read files, write JSON, execute bash commands
2. **Long context** - Can process entire documentation pages
3. **Code understanding** - Can distinguish between code examples and prose
4. **Reasoning** - Can handle ambiguous cases ("Is this a code example or pseudocode?")

#### Why Hooks?

Alternative: Prompt the agent to validate its own output
- ❌ Unreliable - Agent might skip validation
- ❌ Slow - Requires extra turns
- ❌ Verbose - Long prompts

Hooks approach:
- ✅ Deterministic - Always runs
- ✅ Fast - Runs in-line
- ✅ Clean - Separation of concerns

#### Why Three Agents?

Why not one agent that does everything?

1. **Specialization** - Each agent has a focused prompt and tool set
2. **Resumability** - Can re-run validation without re-extracting
3. **Parallelism** - Extraction can process multiple docs concurrently
4. **Debugging** - Easier to trace issues to a specific stage

### Data Flow

```
INPUT: GitHub Repository
    ↓
1. Clone repo to data/<run_id>/repository/
    ↓
2. Find all markdown files in --include-folders
    ↓
3. For each document (parallel):
   Extract Agent → data/<run_id>/results/extraction/<doc>_analysis.json
    ↓
4. For each extraction file (sequential):
   API Validation Agent → data/<run_id>/results/api_validation/<doc>_validation.json
    ↓
5. For each extraction file (sequential):
   Code Validation Agent → data/<run_id>/results/code_validation/<doc>_validation.json
    ↓
OUTPUT: Summary statistics + detailed JSON reports
```

## Use Cases

### Library Maintainers

**Problem:** Documentation drift - code evolves but docs don't
**Solution:** Run Stackbench in CI/CD pipeline
- Fail builds if accuracy drops below threshold
- Get detailed reports on what broke
- Prioritize fixes (API mismatches > missing examples)

### Technical Writers

**Problem:** Can't test code examples across multiple languages/versions
**Solution:** Validate examples against actual library
- Catch typos and syntax errors
- Ensure examples work with specified version
- Get feedback on incomplete examples (missing imports)

### Developer Relations

**Problem:** Users report broken docs, but which ones?
**Solution:** Continuous monitoring
- Track documentation quality metrics over time
- Identify high-traffic pages with low accuracy
- Measure impact of documentation updates

### Open Source Communities

**Problem:** Contributors submit docs without testing examples
**Solution:** Automated PR checks
- Validate new documentation before merge
- Provide actionable feedback to contributors
- Maintain documentation quality standards

## Roadmap

### Currently Implemented (v0.1)

**3 Agents:**
1. ✅ Extraction Agent
2. ✅ API Signature Validation Agent
3. ✅ Code Example Validation Agent

**Infrastructure:**
- ✅ Parallel extraction with workers (configurable, default 5)
- ✅ Programmatic validation hooks (PreToolUse)
- ✅ Logging hooks (PreToolUse + PostToolUse)
- ✅ CLI with rich output
- ✅ Web interface (basic)

**Features from [7-feature plan](docs/0-plan.md):**
- ✅ API Signature Accuracy (Tier 1)
- ✅ Code Example Validation (Tier 1)
- 🚧 Non-Existent APIs (Tier 1) - Partially implemented (detects documented APIs that don't exist, but not missing docs for existing APIs)

### Planned Agents & Features

**Additional Agents** (Not yet implemented):
- Deprecated API Detection Agent
- Missing Coverage Agent
- Consistency Checker Agent
- Accessibility Validator Agent
- Real-World Patterns Agent

**Tier 2: High Value**
4. **Deprecated API Usage** - Detect `@deprecated` in code, flag docs that still use old APIs
5. **Missing API Coverage** - Find APIs in codebase without documentation

**Tier 3: Quality Improvements**
6. **Accessibility & Clarity** - Broken links, missing alt text, ambiguous references
7. **Consistency Issues** - Mixed naming conventions, inconsistent terminology

**Tier 4: Advanced**
8. **Real-World Integration Gaps** - Missing error handling, security patterns, production considerations

### Walkthrough-Based Validation System (Planned)

A new **standalone system** for validating documentation through interactive, step-by-step execution:

**Architecture:**
- **Generate Agent**: Converts tutorial docs into structured walkthrough JSON with step-by-step instructions
- **Audit Agent**: Actually follows the walkthrough like a real developer, executing each step
- **MCP Server**: Supplies steps one-by-one via stdio, preventing the agent from skipping ahead
- **Gap Detection**: Identifies 6 categories of issues:
  - Clarity gaps (vague instructions, missing context)
  - Prerequisite gaps (missing dependencies, undeclared requirements)
  - Logical flow gaps (steps reference undefined resources)
  - Execution gaps (commands fail, syntax errors)
  - Completeness gaps (missing verification steps)
  - Cross-reference gaps (should link to other docs)

**Why It's Powerful:**
- **Dynamic execution**: Agent experiences documentation like a real user would
- **Controlled testing**: MCP server enforces sequential step execution
- **Actionable feedback**: "At step 3, command failed because X was missing"
- **Complements current system**: Static analysis catches API errors, walkthroughs catch tutorial issues

**CLI Commands:**
```bash
# Generate from existing core pipeline run (reuses cloned repo)
stackbench walkthrough generate \
  --from-run <uuid> \
  --doc-path docs/quickstart.md \
  --library <name> \
  --version <version>

# Generate fresh (clones new repo)
stackbench walkthrough generate \
  --repo <url> \
  --branch main \
  --doc-path docs/quickstart.md \
  --library <name> \
  --version <version>

# Audit a walkthrough by executing it
stackbench walkthrough audit \
  --walkthrough data/<uuid>/walkthroughs/wt_*/walkthrough.json \
  --library <name> \
  --version <version>

# Full pipeline (clone + generate + audit)
stackbench walkthrough run \
  --repo <url> \
  --branch main \
  --doc-path docs/quickstart.md \
  --library <name> \
  --version <version>
```

**Directory Structure:**
All walkthroughs live under `data/<uuid>/walkthroughs/wt_*/` where `<uuid>` is either from an existing core pipeline run or a new walkthrough-only run. This ensures the audit agent has access to the full repository context.

See [local-docs/walkthrough-validation-plan.md](local-docs/walkthrough-validation-plan.md) for full design details.

### Technical Improvements

- **Caching** - Don't re-extract unchanged docs
- **Incremental validation** - Only validate changed sections
- **Multi-language support** - TypeScript, JavaScript, Go, Rust
- **LLM-as-judge** - Use Claude to assess "clarity" and "completeness"
- **Auto-fix mode** - Agent proposes documentation fixes
- **GitHub App** - Automated PR comments with validation results

## Contributing

### Project Structure

```
stackbench-v3/
├── stackbench/           # Python package
│   ├── agents/          # Extraction, API validation, Code validation
│   ├── hooks/           # Validation hooks, Logging hooks, Hook manager
│   ├── pipeline/        # Pipeline orchestration
│   ├── repository/      # Git repository management
│   ├── schemas/         # Pydantic models
│   └── cli.py           # CLI entry point
├── frontend/            # React web interface
├── docs/                # Project documentation
├── tests/               # Test suite
└── data/                # Output directory (gitignored)
```

### Development Setup

```bash
# Python backend
uv sync --all-extras
uv run pytest

# Frontend
cd frontend
bun install
bun run dev
```

### Adding a New Agent

1. Create agent class in `stackbench/agents/`
2. Define input/output schemas in `stackbench/schemas/`
3. Create validation hook in `stackbench/hooks/validation.py`
4. Update `HookManager` to include new validation hook
5. Integrate into pipeline in `stackbench/pipeline/runner.py`
6. Add tests
7. Update documentation

### Testing Philosophy

- **Unit tests** - Schema validation, hook behavior
- **Integration tests** - End-to-end pipeline with sample repos
- **Agent tests** - Validate agent outputs against known-good examples

## Learn More

- **Hooks Deep Dive:** `stackbench/hooks/README.md`
- **Feature Plan:** `docs/0-plan.md`
- **Claude Code Docs:** https://docs.claude.com/en/docs/claude-code
- **Claude Agent SDK:** https://docs.claude.com/en/docs/claude-code/agent-sdk

## License

[To be determined]

## Acknowledgments

Built with:
- Claude Code (AI agent execution)
- Anthropic Claude API (language model)
- Rich ecosystem of Python open source tools

Inspired by the frustration of broken documentation across the software industry.
