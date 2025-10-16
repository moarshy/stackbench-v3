# Stackbench

An AI-powered tool that validates documentation quality by checking if code examples work, API signatures match actual implementations, and tutorials are followable from start to finish.

## What It Does

Stackbench uses Claude Code agents to automatically validate documentation through two complementary systems:

### Core Validation Pipeline

1. **Extraction** - Analyzes markdown documentation to extract API signatures and code examples
2. **API Signature Validation** - Validates that documented function signatures match actual library implementations
3. **Code Example Validation** - Tests that code examples actually run without errors
4. **Clarity Validation** - Assesses documentation clarity and structure

### Walkthrough Validation System (New!)

A standalone system that validates tutorial quality through step-by-step execution:

1. **Generate Walkthroughs** - Converts tutorial documentation into structured step-by-step walkthroughs
2. **Audit Walkthroughs** - Claude Code agent actually follows the tutorial like a real developer
3. **Gap Detection** - Identifies missing prerequisites, unclear instructions, broken commands, and logical flow issues

Each process uses Claude Code with intelligent hooks that validate outputs and log execution details.

## How to Run

### Core Validation Pipeline

```bash
# Install dependencies
uv sync

# Run validation on a repository
uv run stackbench run \
  --repo https://github.com/lancedb/lancedb \
  --branch main \
  --include-folders docs/src/python \
  --library lancedb \
  --version 0.25.2 \
  --num-workers 5
```

The `--num-workers` flag (default: 5) controls parallel processing during extraction - multiple documents are analyzed concurrently by Claude Code agents.

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
- Agent actually executes each step (doesn't just read)
- Identifies gaps through real experience ("Step 3 failed because X was missing")
- 6 gap categories: clarity, prerequisites, logical flow, execution errors, completeness, cross-references
- Complements core validation (static analysis vs dynamic execution)
- Repository context: Audit agent can install library, run commands, access example files

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
- **Walkthrough System**: `local-docs/walkthrough-validation-plan.md` - Walkthrough validation design
- **Hooks Deep Dive**: `stackbench/hooks/README.md` - Hook system details
- **Walkthroughs Guide**: `stackbench/walkthroughs/README.md` - Walkthrough module documentation
