# Stackbench

An AI-powered tool that validates documentation quality by checking if code examples work and API signatures match actual implementations.

## What It Does

Stackbench uses Claude Code agents to automatically validate documentation through three core processes:

1. **Extraction** - Analyzes markdown documentation to extract API signatures and code examples
2. **API Signature Validation** - Validates that documented function signatures match actual library implementations
3. **Code Example Validation** - Tests that code examples actually run without errors

Each process uses Claude Code with intelligent hooks that validate outputs and log execution details.

## How to Run

### Python CLI

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

## Hooks System

Stackbench uses programmatic Python hooks (via Claude Code) to ensure data quality:

- **Validation Hooks** - Block invalid JSON outputs before they're written
- **Logging Hooks** - Capture all tool calls and results for debugging

For details, see `stackbench/hooks/README.md`

## Requirements

- Python 3.11+
- Node.js 20+ (for frontend)
- UV (Python package manager)
- Bun or npm (for frontend)
- Claude Code CLI (for AI agent execution)
