# Stackbench Walkthroughs

Interactive documentation validation through step-by-step execution.

## Overview

The Walkthroughs module provides a novel approach to documentation quality validation: instead of statically analyzing documentation, it **generates interactive walkthroughs** and **executes them step-by-step** using Claude Code agents to identify gaps, unclear instructions, and documentation issues.

## Architecture

### Components

1. **Schemas** (`schemas.py`): Pydantic models for walkthrough structure and audit results
2. **Generate Agent** (`walkthrough_generate_agent.py`): Converts documentation into structured walkthroughs
3. **Audit Agent** (`walkthrough_audit_agent.py`): Executes walkthroughs and identifies gaps
4. **MCP Server** (`mcp_server.py`): Provides step-by-step walkthrough serving via MCP protocol

### How It Works

```
Documentation (Markdown)
         ↓
   Generate Agent → Walkthrough JSON (structured steps)
         ↓
   Audit Agent + MCP Server → Gap Analysis Report
         ↓
   Actionable Issues & Improvements
```

## CLI Usage

### 1. Generate Walkthrough

```bash
stackbench walkthrough generate \
  --doc-path docs/quickstart.md \
  --library lancedb \
  --version 0.25.2 \
  --output ./data/wt_abc123
```

Creates a structured walkthrough JSON from documentation.

### 2. Audit Walkthrough

```bash
stackbench walkthrough audit \
  --walkthrough ./data/wt_abc123/wt_abc123.json \
  --library lancedb \
  --version 0.25.2
```

Executes the walkthrough step-by-step and identifies gaps.

### 3. Full Pipeline

```bash
stackbench walkthrough run \
  --doc-path docs/quickstart.md \
  --library lancedb \
  --version 0.25.2
```

Generates and audits in one command.

## Walkthrough Structure

### JSON Schema

```json
{
  "version": "1.0",
  "exportedAt": "2025-01-16T...",
  "walkthrough": {
    "title": "Getting Started with LanceDB",
    "description": "A comprehensive guide...",
    "estimatedDurationMinutes": 15,
    "tags": ["quickstart", "python"]
  },
  "steps": [
    {
      "title": "Install LanceDB",
      "contentFields": {
        "contentForUser": "# Install LanceDB\n\nRun: `pip install lancedb`",
        "contextForAgent": "LanceDB requires Python 3.9+...",
        "operationsForAgent": "1. Run: pip install lancedb\n2. Verify installation...",
        "introductionForAgent": "This step installs the library..."
      },
      "displayOrder": 1,
      "nextStepReference": 2
    }
  ]
}
```

### Content Fields

Each step has four content types designed for both human users and AI agents:

- **contentForUser**: Markdown content shown to users (documentation as they'd see it)
- **contextForAgent**: Background knowledge the agent needs (how things work, what to expect)
- **operationsForAgent**: Concrete commands and actions to execute (specific, executable)
- **introductionForAgent**: Purpose and goals of the step

## Gap Detection

The audit agent identifies six types of gaps:

### 1. **Clarity Gaps**
- Instructions too vague
- Ambiguous references
- Missing context

### 2. **Prerequisite Gaps**
- Missing setup requirements
- Undeclared dependencies
- Missing environment variables

### 3. **Logical Flow Gaps**
- Step references undefined resource
- Commands assume state not created
- Out-of-order operations

### 4. **Execution Gaps**
- Commands fail when executed
- Syntax errors
- Missing imports

### 5. **Completeness Gaps**
- Missing steps
- No verification procedures
- Missing cleanup instructions

### 6. **Cross-Reference Gaps**
- Should link to another doc
- Missing related concepts
- Duplicate content

## Audit Results

### Report Structure

```json
{
  "walkthrough_id": "wt_abc123",
  "walkthrough_title": "Getting Started",
  "library_name": "lancedb",
  "library_version": "0.25.2",
  "total_steps": 10,
  "completed_steps": 8,
  "failed_steps": 2,
  "success": false,
  "gaps": [
    {
      "step_number": 3,
      "step_title": "Connect to Database",
      "gap_type": "prerequisite",
      "severity": "critical",
      "description": "Step requires database file but doesn't mention creating it",
      "suggested_fix": "Add step to create database file or use default path"
    }
  ],
  "critical_gaps": 1,
  "warning_gaps": 3,
  "info_gaps": 2
}
```

## MCP Server Protocol

The MCP server provides these tools to the audit agent:

### `start_walkthrough(walkthrough_path)`
Initialize a walkthrough session from JSON file.

### `next_step()`
Get the next step in the walkthrough. Returns:
- `contentForUser`
- `contextForAgent`
- `operationsForAgent`
- `introductionForAgent`

### `walkthrough_status()`
Get current progress (step number, total steps, gaps reported).

### `report_gap(gap_type, severity, description, ...)`
Report an issue found during execution.

## Development

### Running the MCP Server Standalone

```bash
uv run python -m stackbench.walkthroughs.mcp_server
```

### Programmatic Usage

```python
from stackbench.walkthroughs import (
    WalkthroughGenerateAgent,
    WalkthroughAuditAgent,
)

# Generate
agent = WalkthroughGenerateAgent(
    output_folder=Path("./output"),
    library_name="mylib",
    library_version="1.0.0"
)
walkthrough = await agent.generate_walkthrough(Path("docs/quickstart.md"))

# Audit
audit_agent = WalkthroughAuditAgent(
    output_folder=Path("./output"),
    library_name="mylib",
    library_version="1.0.0"
)
result = await audit_agent.audit_walkthrough(Path("./output/walkthrough.json"))
```

## Design Philosophy

### Why Walkthroughs?

Traditional documentation validation (like the main Stackbench pipeline) excels at:
- API signature accuracy
- Code example syntax
- Static analysis

Walkthroughs excel at:
- **Tutorial quality** - Does the flow make sense?
- **Learning experience** - Can a real developer follow this?
- **Dynamic execution** - Do the steps actually work in sequence?
- **Gap identification** - What's missing or unclear?

### Why MCP?

Using an MCP server for step delivery:
- **Controls pacing**: Agent can't skip ahead or see all steps at once (simulates real user)
- **State tracking**: Server knows exactly what's been completed
- **Extensible**: Easy to add tools like `skip_step`, `get_hint`, `mark_unclear`

### Why stdio?

stdio-based MCP is simple and reliable:
- No network configuration needed
- Process isolation (agent runs in subprocess)
- Easy debugging (can log all MCP messages)
- Works with Claude Code SDK out of the box

## Future Enhancements

- [ ] Gap auto-fixing: Generate documentation patches
- [ ] Multi-language support: JavaScript, Go, Rust walkthroughs
- [ ] Parallel step execution: For independent steps
- [ ] Walkthrough diffing: Compare versions
- [ ] Interactive mode: Human-in-the-loop validation
- [ ] Video walkthrough generation: Capture execution as video

## Related Modules

- **Extraction Agent**: Extracts API signatures from docs
- **API Validation Agent**: Validates signatures against library
- **Code Validation Agent**: Executes code examples
- **Clarity Agent**: LLM-based documentation quality scoring

Walkthroughs complement these by focusing on the **end-to-end tutorial experience**.
