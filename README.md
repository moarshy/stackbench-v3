# Stackbench

An AI-powered tool that validates documentation quality by checking if code examples work, API signatures match actual implementations, and tutorials are followable from start to finish.

## What It Does

Stackbench uses Claude Code agents to automatically validate documentation through two complementary systems:

### Core Validation Pipeline

1. **Extraction** - Analyzes markdown documentation to extract API signatures and code examples
2. **API Completeness & Deprecation** (3-Stage Pipeline with MCP!) - Analyzes documentation coverage:
   - **Stage 1**: Library introspection via Bash (`pip install` + `python_introspect.py`) → `api_surface.json`
   - **Stage 2**: Fast deterministic script scans ALL .md files (~2s), MCP scores APIs → `documented_apis.json` + `undocumented_apis.json`
   - **Stage 3**: MCP calculates metrics and prioritizes → `completeness_analysis.json`
   - **Performance**: ~7s for 118 APIs (5-10x faster than LLM matching)
   - Identifies deprecated APIs still taught in documentation
   - Ranks undocumented APIs by importance (0-10 scale based on heuristics)
   - Output: 4 JSON files in `results/api_completeness/`
3. **API Signature Validation** - Validates that documented function signatures match actual library implementations
4. **Code Example Validation** - Tests that code examples actually run without errors
5. **Clarity Validation** (with MCP!) - LLM-as-judge system that evaluates documentation from a user experience perspective:
   - Uses MCP server for deterministic scoring calculations
   - Scores 5 dimensions on 0-10 scale (instruction clarity, logical flow, completeness, consistency, prerequisites)
   - Identifies unclear instructions, missing prerequisites, logical gaps, and broken links
   - Provides actionable suggestions with precise line numbers
   - Pre-processes MkDocs Material snippet includes for efficiency

### Walkthrough Validation System (Fully Implemented!)

A standalone system that validates tutorial quality through step-by-step execution:

1. **Generate Walkthroughs** - Converts tutorial documentation into structured step-by-step walkthroughs with 4 content fields per step (contentForUser, contextForAgent, operationsForAgent, introductionForAgent)
2. **MCP Server** - Supplies steps one-by-one via stdio protocol, preventing the agent from skipping ahead and simulating real user experience
3. **Audit Walkthroughs** - Claude Code agent actually follows the tutorial like a real developer, executing each step sequentially
4. **Gap Detection** - Identifies 6 categories of issues:
   - **Clarity gaps**: Vague instructions, missing context
   - **Prerequisite gaps**: Missing dependencies, undeclared requirements
   - **Logical flow gaps**: Steps reference undefined resources
   - **Execution gaps**: Commands fail, syntax errors
   - **Completeness gaps**: Missing verification steps
   - **Cross-reference gaps**: Should link to other docs

Each process uses Claude Code with intelligent hooks that validate outputs and log execution details.

## How to Run

### Core Validation Pipeline

```bash
# Install dependencies
uv sync

# Run validation on a repository (latest commit)
uv run stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --docs-path docs/src \
  --include-folders python \
  --library lancedb \
  --version 0.25.2 \
  --num-workers 5
```

**Key parameters:**
- `--docs-path` **(required)** - Base documentation directory (e.g., `docs/src`)
- `--include-folders` *(optional)* - Comma-separated folders relative to docs-path (e.g., `python,javascript`)
- `--num-workers` *(default: 5)* - Number of parallel workers for concurrent document processing
- `--commit` *(optional)* - Specific commit hash (if omitted, resolves from branch HEAD automatically)
- `--force` *(optional)* - Bypass cache and force re-analysis

### Version Tracking & Comparison

Stackbench tracks **two independent versions**:
1. **Documentation Version** - Which git commit of the docs are we analyzing?
2. **Library Version** - Which version of the library should we test against?

This enables powerful validation scenarios:

```bash
# Scenario 1: Test latest docs against LanceDB 0.25.2
uv run stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --docs-path docs/src \
  --include-folders python \
  --library lancedb \
  --version 0.25.2

# Scenario 2: Pin to specific commit for reproducibility
uv run stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --commit fe25922 \
  --docs-path docs/src \
  --include-folders python \
  --library lancedb \
  --version 0.25.2

# Scenario 3: Test old docs against newer library (check breaking changes)
uv run stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --commit abc123 \  # Old docs from earlier release
  --docs-path docs/src \
  --include-folders python \
  --library lancedb \
  --version 0.25.2  # Test against 0.25.2

# Scenario 4: Force re-analysis (bypass cache)
uv run stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --docs-path docs/src \
  --include-folders python \
  --library lancedb \
  --version 0.25.2 \
  --force
```

**Smart Caching:**
- Identical runs (same repo + commit + docs-path + library + version) are cached
- Second run completes instantly using cached results
- Cache key: `{repo}:{commit}:{docs_path}:{library_name}:{library_version}`
- Use `--force` to bypass cache and re-run analysis

**Version Comparison** *(UI coming soon)*:
- Track documentation quality over time
- Compare v0.25.0 → v0.26.0 to see if quality improved
- Identify new issues introduced or resolved

### Walkthrough Validation

```bash
# Option 1: Generate from existing core pipeline run (reuses cloned repo)
uv run stackbench walkthrough generate \
  --from-run 22c09315-1385-4ad6-a2ff-1e631a482107 \
  --doc-path docs/quickstart.md \
  --library lancedb \
  --version 0.25.2
# Output: data/22c09315-1385.../walkthroughs/wt_xyz789/

# Option 2: Generate fresh (clones new repo)
uv run stackbench walkthrough generate \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --doc-path docs/quickstart.md \
  --library lancedb \
  --version 0.25.2
# Output: data/<new-uuid>/walkthroughs/wt_xyz789/

# Audit a walkthrough by executing it step-by-step
uv run stackbench walkthrough audit \
  --walkthrough data/22c09315-1385.../walkthroughs/wt_xyz789/walkthrough.json \
  --library lancedb \
  --version 0.25.2

# Full pipeline: clone + generate + audit in one command
uv run stackbench walkthrough run \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --doc-path docs/quickstart.md \
  --library lancedb \
  --version 0.25.2
```

**Directory Structure:**
- Core pipeline + walkthroughs: `data/<uuid>/repository/` and `data/<uuid>/walkthroughs/wt_*/`
- Walkthrough-only run: `data/<new-uuid>/repository/` and `data/<new-uuid>/walkthroughs/wt_*/`

**What makes walkthroughs powerful:**
- **Dynamic execution**: Agent actually executes each step (doesn't just read)
- **MCP-controlled pacing**: Server delivers one step at a time, can't skip ahead
- **Real experience**: Identifies gaps through actual execution ("At step 3, command failed because X was missing")
- **6 gap categories**: clarity, prerequisites, logical flow, execution errors, completeness, cross-references
- **Complements core pipeline**: Static analysis catches API errors, walkthroughs catch tutorial issues
- **Full repository context**: Audit agent can install library, run commands, access example files
- **Structured reporting**: Each gap includes step number, severity (critical/warning/info), description, and suggested fix

**Real example**: See `local-docs/demo-nextjs-walkthrough.json` for a production walkthrough with 10 steps covering Next.js setup, development server, hot reload, and configuration.

### Web Interface

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
bun install

# Start development server
bun run dev
```

The web UI will be available at `http://localhost:5173`

## Key Features

### Hooks System

Stackbench uses programmatic Python hooks (via Claude Code) to ensure data quality:

- **Validation Hooks** - Block invalid JSON outputs before they're written
- **Logging Hooks** - Capture all tool calls and results for debugging

For details, see `stackbench/hooks/README.md`

### MCP Server for Walkthroughs

The walkthrough system uses an MCP (Model Context Protocol) server to control step-by-step execution:

- **Controlled pacing** - Agent receives one step at a time (can't skip ahead)
- **State tracking** - Server knows exactly what's been completed
- **Gap reporting** - Structured feedback on documentation issues

For details, see `stackbench/walkthroughs/README.md`

## Requirements

- Python 3.11+
- Node.js 20+ (for frontend)
- UV (Python package manager)
- Bun or npm (for frontend)
- Claude Code CLI (for AI agent execution)

## Learn More

- **Main Documentation**: `CLAUDE.md` - Comprehensive overview of architecture and design
- **Feature Plan**: `docs/0-plan.md` - Detailed feature roadmap
- **Hooks Deep Dive**: `stackbench/hooks/README.md` - Hook system details

**Walkthrough System:**
- **Architecture Design**: `local-docs/walkthrough-validation-plan.md` - Original design document
- **Module Documentation**: `stackbench/walkthroughs/README.md` - Implementation guide
- **Real Example**: `local-docs/demo-nextjs-walkthrough.json` - Production walkthrough with 10 steps
- **MCP Server Guide**: `stackbench/walkthroughs/mcp_server.py` - Step delivery protocol
