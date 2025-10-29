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

Stackbench uses Claude Code agents to systematically validate documentation quality at scale through two complementary systems:

**Core Validation Pipeline:**
1. **Extract structured data** from unstructured markdown
2. **Validate API signatures** through dynamic code introspection
3. **Execute code examples** in isolated environments
4. **Assess clarity** using LLM-as-judge scoring
5. **Provide actionable feedback** on what's broken and why

**Walkthrough Validation System:**
1. **Generate step-by-step tutorials** from documentation
2. **Execute tutorials dynamically** like a real developer following them
3. **Identify gaps through actual execution** (missing prerequisites, logical flow issues, broken commands)
4. **Report contextual issues** ("At step 3, couldn't complete because X was missing")

This approach combines static analysis (fast, deterministic), dynamic testing (catches runtime issues), AI reasoning (handles ambiguity), and experiential validation (simulates real user experience).

## Architecture

### Five-Agent Pipeline

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
│         API COMPLETENESS & DEPRECATION AGENT (MCP)          │
│  • MCP server: introspects library (pip + inspect module)   │
│  • MCP server: calculates importance scores (heuristics)    │
│  • Agent: reads extraction files, matches APIs to docs      │
│  • Agent: calls MCP for deterministic calculations          │
│  • Outputs: coverage %, undocumented APIs, deprecated APIs  │
│  • Output: results/api_completeness/completeness_analysis.json │
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
                            ↓
┌─────────────────────────────────────────────────────────────┐
│      DOCUMENTATION CLARITY VALIDATION AGENT (MCP)           │
│  • LLM-as-judge system for user experience quality          │
│  • MCP server: deterministic scoring calculations           │
│  • Pre-processes MkDocs Material snippet includes           │
│  • Evaluates: instruction clarity, logical flow, prereqs    │
│  • Scores 5 dimensions on 0-10 scale with rubric            │
│  • Flags: unclear steps, missing prereqs, logical gaps      │
│  • Provides: actionable suggestions with line numbers       │
└─────────────────────────────────────────────────────────────┘
```

### Parallel Processing

Both the extraction and clarity validation phases process multiple documents concurrently using worker pools:

- **Default: 5 workers** - Configurable via `--num-workers`
- Each worker runs an independent Claude Code agent
- Results are validated and aggregated
- Enables processing large documentation sets efficiently
- Clarity validation processed 7 LanceDB docs in ~3 minutes with 5 workers

### Versioning & Caching System

Stackbench tracks **two independent versions** that work together:

**1. Documentation Version (Git Commit Hash)**
- Which commit of the *documentation repository* are we analyzing?
- Specified via `--commit` (optional) or auto-resolved from `--branch` HEAD
- Stored as `doc_commit_hash` in metadata
- Example: Docs at commit `fe25922` from the LanceDB repo

**2. Library Version**
- Which version of the *actual library* should validation agents install and test against?
- Specified via `--library lancedb --version 0.25.2`
- Stored as `library_name` and `library_version` in metadata
- Example: Install `lancedb==0.25.2` in Python environment for testing

**Why This Matters:**

These versions are independent, enabling powerful validation scenarios:

```bash
# Same docs, different library → Test docs against multiple library versions
stackbench run --commit abc123 --docs-path docs/src --include-folders python --library lancedb --version 0.25.2
stackbench run --commit abc123 --docs-path docs/src --include-folders python --library lancedb --version 0.26.0

# Same library, different docs → Track doc quality improvements
stackbench run --commit def456 --docs-path docs/src --include-folders python --library lancedb --version 0.25.2
stackbench run --commit ghi789 --docs-path docs/src --include-folders python --library lancedb --version 0.25.2

# Both different → Full version comparison
stackbench run --commit abc123 --docs-path docs/src --include-folders python --library lancedb --version 0.25.2
stackbench run --commit def456 --docs-path docs/src --include-folders python --library lancedb --version 0.25.2
```

**Smart Caching (JSON-based):**

Cache key format:
```
{repo_url}:{doc_commit_hash}:{docs_path}:{library_name}:{library_version}
```

Behavior:
- Before running: Check if exact match exists in `data/runs.json`
- Cache hit: Return cached results instantly (no re-analysis)
- Cache miss: Run full pipeline, register in cache
- Force mode: `--force` flag bypasses cache

Implementation:
- `stackbench/cache/manager.py` - JSON-based cache operations
- `data/runs.json` - Index of all completed runs
- Metadata includes: run_id, timestamps, status, all version info

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

### 4. LLM-as-Judge for Clarity

The clarity validation agent uses Claude itself to evaluate documentation from a user experience perspective:

**What it catches that static analysis misses:**
```markdown
## Configuration

To configure the database, create a config file:

\`\`\`python
config = lancedb.Config.from_file('config.yaml')
db = lancedb.connect(config=config)
\`\`\`
```

**Clarity Agent identifies:**
- ❌ **Logical gap** - "Step references config.yaml but file was never created"
- ❌ **Missing prerequisite** - "No explanation of config.yaml format or required fields"
- **Suggestion:** "Add Step 1b: Create config.yaml with fields: host, port, database_name"

**Multi-dimensional scoring (0-10 scale):**
```json
{
  "instruction_clarity": 6.0,      // Are steps clear and actionable?
  "logical_flow": 5.0,             // Do steps build on each other?
  "completeness": 6.5,             // All prerequisites mentioned?
  "consistency": 8.0,              // Terminology consistent?
  "prerequisite_coverage": 5.0,    // Prerequisites upfront?
  "overall_score": 6.1
}
```

**Granular location reporting:**
Every issue includes section name, line number, and step number:
> "Step 3 at line 45 in 'Configuration' section references config.yaml not created in Step 1"

**Smart optimizations:**
- Pre-processes MkDocs Material `--8<--` snippet includes before sending to Claude
- Reduces API calls by resolving deterministic patterns programmatically
- Falls back to agent tool use for complex cases

**Context integration:**
Reads results from API signature and code validation agents to correlate issues:
> "This code example failed API validation AND has unclear instructions (double problem)"

### 5. Dynamic Tutorial Execution via Walkthroughs

The walkthrough system takes validation beyond static analysis by **actually following tutorials step-by-step**:

**How it works:**
```
1. Generate Agent reads tutorial docs
   ↓ Extracts 10 logical steps
2. MCP Server loads walkthrough JSON
   ↓ Delivers steps one-by-one
3. Audit Agent executes each step
   ↓ Reports gaps as they occur
4. Gap report generated
```

**What it catches that other systems miss:**

Example tutorial:
```markdown
## Quick Start

1. Install the library: `pip install lancedb`
2. Import and connect:
   ```python
   import lancedb
   db = lancedb.connect("./my_database")
   ```
3. Query your data:
   ```python
   results = db.open_table("my_table").search([1.0, 2.0]).limit(5)
   ```
```

**Walkthrough Audit Agent identifies:**
- ❌ **Logical flow gap (critical)** - "Step 3 references table 'my_table' but no step shows creating it"
- ❌ **Completeness gap (warning)** - "No verification step to confirm database created successfully"
- ❌ **Execution gap (critical)** - "Step 3 fails with 'table not found' error"
- **Suggestion:** "Add Step 2b: Create table with schema before querying"

**Why MCP Server is key:**
- **Enforces sequential execution** - Agent can't skip ahead or see all steps
- **Simulates real user experience** - Discovers gaps through actual execution
- **State tracking** - Server knows exactly which steps completed
- **Structured gap reporting** - 6 categories (clarity, prerequisite, logical_flow, execution, completeness, cross_reference)

**Real example:**
The `demo-nextjs-walkthrough.json` contains 10 steps covering Next.js setup. When audited, the agent:
1. Verifies Node.js 18.18+ installed
2. Runs `npx create-next-app@latest`
3. Explores project structure
4. Starts dev server on localhost:3000
5. Makes first code edit and sees hot reload
6. Tests all npm scripts (dev, build, start, lint)

Each step provides:
- `contentForUser`: What the user reads
- `contextForAgent`: Background knowledge
- `operationsForAgent`: Exact commands to run
- `introductionForAgent`: Purpose and goals

### 6. Audit Trail

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

#### Why Four Agents?

Why not one agent that does everything?

1. **Specialization** - Each agent has a focused prompt and tool set
2. **Resumability** - Can re-run validation without re-extracting
3. **Parallelism** - Extraction and clarity validation process multiple docs concurrently
4. **Debugging** - Easier to trace issues to a specific stage
5. **Context integration** - Clarity agent can read results from API/code validation to correlate issues

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
4. API Completeness Agent (3-stage pipeline after all extractions complete):
   • Stage 1 (Introspection): Installs library via pip, runs introspection template → api_surface.json
   • Stage 2 (Matching): Fast script scans ALL .md files, MCP scores APIs → documented_apis.json + undocumented_apis.json
   • Stage 3 (Analysis): MCP calculates metrics and prioritizes → completeness_analysis.json
   • Performance: ~7s for 118 APIs (5-10x faster than LLM matching)
   → data/<run_id>/results/api_completeness/{api_surface, documented_apis, undocumented_apis, completeness_analysis}.json
    ↓
5. For each extraction file (sequential):
   API Validation Agent → data/<run_id>/results/api_validation/<doc>_validation.json
    ↓
6. For each extraction file (sequential):
   Code Validation Agent → data/<run_id>/results/code_validation/<doc>_validation.json
    ↓
7. For each document (parallel):
   Clarity Validation Agent → data/<run_id>/results/clarity_validation/<doc>_clarity.json
   • Uses MCP server for deterministic scoring calculations
   • Reads extraction metadata, original markdown, and optionally API/code validation results
    ↓
OUTPUT: Summary statistics + detailed JSON reports + clarity scores + coverage metrics
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

**Core Pipeline - 4 Agents:**
1. ✅ Extraction Agent
2. ✅ API Signature Validation Agent
3. ✅ Code Example Validation Agent
4. ✅ Documentation Clarity Validation Agent (LLM-as-judge)

**Walkthrough System - 2 Agents + MCP Server:**
5. ✅ Walkthrough Generate Agent
6. ✅ Walkthrough Audit Agent
7. ✅ MCP Server (stdio-based, step delivery)

**Infrastructure:**
- ✅ Parallel extraction with workers (configurable, default 5)
- ✅ Parallel clarity validation with workers (configurable, default 5)
- ✅ Programmatic validation hooks (PreToolUse)
- ✅ Logging hooks (PreToolUse + PostToolUse)
- ✅ CLI with rich output (includes clarity scores and issue counts)
- ✅ Web interface (basic)
- ✅ MkDocs Material snippet preprocessing (optimization for clarity agent)
- ✅ MCP server for controlled walkthrough execution
- ✅ Gap detection across 6 categories

**Features from [7-feature plan](docs/0-plan.md):**
- ✅ API Signature Accuracy (Tier 1)
- ✅ Code Example Validation (Tier 1)
- ✅ Accessibility & Clarity (Tier 3) - **Fully implemented!**
  - Instruction clarity scoring (0-10 rubric)
  - Logical flow analysis (step dependencies)
  - Prerequisite coverage validation
  - Consistency checking (terminology, code style)
  - Technical accessibility (broken links, alt text, code block languages)
  - Granular location reporting (section, line, step number)
  - Actionable suggestions for improvement
- 🚧 Non-Existent APIs (Tier 1) - Partially implemented (detects documented APIs that don't exist, but not missing docs for existing APIs)

### Planned Agents & Features

**Additional Agents** (Not yet implemented):
- Deprecated API Detection Agent
- Missing Coverage Agent
- Real-World Patterns Agent

**Tier 2: High Value**
4. **Deprecated API Usage** - Detect `@deprecated` in code, flag docs that still use old APIs
5. **Missing API Coverage** - Find APIs in codebase without documentation

**Tier 4: Advanced**
6. **Real-World Integration Gaps** - Missing error handling, security patterns, production considerations

### Walkthrough-Based Validation System ✅ Implemented

A **standalone system** that validates documentation through interactive, step-by-step execution - now fully operational!

**Architecture:**
- **Generate Agent** (`walkthrough_generate_agent.py`): Converts tutorial docs into structured walkthrough JSON with step-by-step instructions
  - Extracts 4 content fields per step: contentForUser, contextForAgent, operationsForAgent, introductionForAgent
  - Validates output against WalkthroughExport schema via hooks
  - Logs all operations for debugging

- **Audit Agent** (`walkthrough_audit_agent.py`): Actually follows the walkthrough like a real developer, executing each step
  - Connects to MCP server for step delivery
  - Executes operations (bash commands, file operations)
  - Reports gaps through MCP tools
  - Generates comprehensive AuditResult JSON

- **MCP Server** (`mcp_server.py`): Supplies steps one-by-one via stdio, preventing the agent from skipping ahead
  - Tools: `start_walkthrough()`, `next_step()`, `walkthrough_status()`, `report_gap()`
  - Maintains WalkthroughSession state
  - Enforces sequential execution (can't skip steps)

- **Gap Detection**: Identifies 6 categories of issues:
  - **Clarity gaps**: Vague instructions, missing context
  - **Prerequisite gaps**: Missing dependencies, undeclared requirements
  - **Logical flow gaps**: Steps reference undefined resources
  - **Execution gaps**: Commands fail, syntax errors
  - **Completeness gaps**: Missing verification steps
  - **Cross-reference gaps**: Should link to other docs

**Why It's Powerful:**
- **Dynamic execution**: Agent experiences documentation like a real user would
- **Controlled testing**: MCP server enforces sequential step execution (can't skip ahead)
- **Actionable feedback**: "At step 3, command failed because X was missing"
- **Complements core pipeline**: Static analysis catches API errors, walkthroughs catch tutorial issues
- **Granular reporting**: Each gap includes step number, severity, description, and suggested fix

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
```
data/<uuid>/walkthroughs/wt_<walkthrough-uuid>/
├── wt_<uuid>.json                      # Generated walkthrough
├── wt_<uuid>_audit.json               # Audit results (gaps found)
├── agent_logs/
│   ├── generate.log                    # Human-readable generation logs
│   ├── generate_tools.jsonl            # Tool call trace (generation)
│   ├── audit.log                       # Human-readable audit logs
│   └── audit_tools.jsonl               # Tool call trace (audit)
└── validation_logs/
    └── walkthrough_generation_validation_calls.txt
```

**Real Example:**
See `local-docs/demo-nextjs-walkthrough.json` for a production walkthrough with 10 steps covering Next.js setup, development server, first edits, and configuration.

**Implementation Details:**
See [local-docs/walkthrough-validation-plan.md](local-docs/walkthrough-validation-plan.md) for architecture design and [stackbench/walkthroughs/README.md](stackbench/walkthroughs/README.md) for module documentation.

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
│   ├── agents/          # Core validation agents
│   │   ├── extraction_agent.py
│   │   ├── api_completeness_agent.py        # Coverage & deprecation (uses Bash + MCP)
│   │   ├── api_validation_agent.py
│   │   ├── code_validation_agent.py
│   │   └── clarity_agent.py
│   ├── introspection_templates/  # Language-specific introspection scripts ✨
│   │   └── python_introspect.py              # Python API discovery (inspect module)
│   ├── mcp_servers/     # MCP servers for deterministic operations ✨
│   │   ├── __init__.py
│   │   ├── api_completeness_server.py       # Importance scoring & metrics (no introspection)
│   │   └── clarity_scoring_server.py        # Deterministic clarity scoring
│   ├── walkthroughs/    # Walkthrough validation system ✨
│   │   ├── __init__.py
│   │   ├── schemas.py                      # Walkthrough data models
│   │   ├── walkthrough_generate_agent.py   # Generate walkthroughs from docs
│   │   ├── walkthrough_audit_agent.py      # Execute walkthroughs
│   │   ├── mcp_server.py                   # MCP server for step delivery
│   │   └── README.md                       # Module documentation
│   ├── cache/           # Caching system ✨
│   │   ├── __init__.py
│   │   └── manager.py               # JSON-based cache operations
│   ├── hooks/           # Validation hooks, Logging hooks, Hook manager
│   │   ├── validation.py            # All validation schemas (core + walkthrough + completeness)
│   │   └── manager.py               # Routes all agents to hooks
│   ├── pipeline/        # Pipeline orchestration
│   │   └── runner.py                # Core pipeline with caching integration + completeness
│   ├── repository/      # Git repository management (commit resolution)
│   ├── schemas/         # Pydantic models (core pipeline + API completeness)
│   └── cli.py           # CLI entry point (core + walkthrough commands)
├── frontend/            # React web interface
├── docs/                # Project documentation
├── local-docs/          # Design documents and examples
│   ├── walkthrough-validation-plan.md      # Walkthrough architecture
│   └── demo-nextjs-walkthrough.json        # Real example (10 steps)
├── tests/               # Test suite
└── data/                # Output directory (gitignored)
    ├── runs.json                            # Cache index ✨
    └── <run_id>/
        ├── repository/                      # Cloned git repo
        ├── metadata.json                    # Enhanced with doc_commit_hash, docs_path
        ├── results/                         # Core pipeline results
        │   ├── extraction/
        │   ├── api_completeness/            # NEW: Coverage analysis
        │   │   └── completeness_analysis.json
        │   ├── api_validation/
        │   ├── code_validation/
        │   └── clarity_validation/
        ├── validation_logs/                 # Core pipeline logs
        │   ├── api_completeness_logs/       # NEW: Completeness agent logs
        │   └── clarity_logs/
        └── walkthroughs/                    # Walkthrough outputs ✨
            └── wt_<uuid>/
                ├── wt_<uuid>.json           # Generated walkthrough
                ├── wt_<uuid>_audit.json     # Audit results
                ├── agent_logs/              # Generation + audit logs
                └── validation_logs/         # Walkthrough validation
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
