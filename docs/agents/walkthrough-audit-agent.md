# Walkthrough Audit Agent

## Objective

The Walkthrough Audit Agent **executes walkthroughs step-by-step** to validate tutorial quality by actually following them like a real developer. It:
- Connects to an MCP server that delivers steps one-by-one
- Executes each step's operations (bash commands, file operations, code)
- Identifies gaps, unclear instructions, missing prerequisites
- Reports issues with specific step numbers and severity
- Produces a comprehensive gap report

This agent simulates the **real user experience** of following a tutorial, catching issues that static analysis misses.

## Position in Pipeline

```
┌─────────────────────────────────────┐
│    WALKTHROUGH VALIDATION SYSTEM    │
│         (Standalone)                │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────┐
│ GENERATE AGENT          │
│  (Tutorial → JSON)      │
└─────────────────────────┘
            ↓
            ↓ (walkthrough.json)
            ↓
┌─────────────────────────┐
│ MCP SERVER              │
│  (Step Delivery)        │
└─────────────────────────┘
            ↓
┌─────────────────────────┐
│ AUDIT AGENT             │ ◄── YOU ARE HERE
│  (Execution + Gaps)     │
└─────────────────────────┘
```

**Stage**: Final stage of walkthrough validation
**Runs**: On-demand via `stackbench walkthrough audit`
**Dependencies**: Generated walkthrough JSON, MCP server
**Consumers**: Gap reports, improvement feedback

## Inputs

### Required
- **`output_folder`** (Path): Folder to save audit results
- **`library_name`** (str): Name of the library being validated
- **`library_version`** (str): Version of the library
- **`walkthrough_path`** (Path): Path to walkthrough JSON file

### Optional
- **`working_directory`** (Path): Working directory for execution (default: temp dir)
- **`mcp_server_path`** (Path): Path to MCP server script (auto-detected if not provided)

### Environment
- MCP server (`stackbench.walkthroughs.mcp_server`)
- Bash access for executing commands
- Python environment for running code

## Expected Output

### Output Files

```
output_folder/
├── wt_{id}_audit.json                 # Audit results with gaps
├── wt_{id}_session.json              # MCP session state
└── agent_logs/
    ├── audit.log                      # Human-readable log
    └── audit_tools.jsonl              # Tool call trace
```

### Output Schema (`wt_{id}_audit.json`)

```json
{
  "walkthrough_id": "wt_quickstart",
  "walkthrough_title": "Getting Started with LanceDB",
  "library_name": "lancedb",
  "library_version": "0.25.2",
  "started_at": "2025-01-15T12:30:00Z",
  "completed_at": "2025-01-15T12:35:00Z",
  "duration_seconds": 300.5,
  "total_steps": 10,
  "completed_steps": 8,
  "failed_steps": 2,
  "success": false,

  "gaps": [
    {
      "step_number": 3,
      "step_title": "Configure Database",
      "gap_type": "logical_flow",
      "severity": "critical",
      "description": "Step 3 references 'config.yaml' file but this file was never created in previous steps",
      "suggested_fix": "Add Step 2b: Create config.yaml with example content before Step 3",
      "context": "Attempted to run: config = Config.from_file('config.yaml'). Error: FileNotFoundError",
      "timestamp": "2025-01-15T12:32:15Z"
    },
    {
      "step_number": 5,
      "step_title": "Query Data",
      "gap_type": "prerequisite",
      "severity": "warning",
      "description": "Step assumes 'data' directory exists but doesn't mention creating it",
      "suggested_fix": "Add prerequisite check or creation step for './data' directory",
      "context": "Command 'db = lancedb.connect(\"./data\")' works but directory wasn't explicitly created",
      "timestamp": "2025-01-15T12:33:20Z"
    },
    {
      "step_number": 7,
      "step_title": "Verify Results",
      "gap_type": "completeness",
      "severity": "info",
      "description": "No verification step to confirm query results are correct",
      "suggested_fix": "Add expected output or assertion to verify query worked",
      "context": "Query ran successfully but no way to verify correctness",
      "timestamp": "2025-01-15T12:34:10Z"
    }
  ],

  "execution_log": "[{...}]",
  "agent_log_path": "output_folder/agent_logs/audit.log",
  "critical_gaps": 1,
  "warning_gaps": 1,
  "info_gaps": 1
}
```

### Session File (`wt_{id}_session.json`)

```json
{
  "walkthrough_path": "/path/to/walkthrough.json",
  "current_step": 8,
  "is_complete": false,
  "completed_steps": 8,
  "gaps": [
    {
      "step_number": 3,
      "step_title": "Configure Database",
      "gap_type": "logical_flow",
      "severity": "critical",
      "description": "...",
      "suggested_fix": "...",
      "context": "...",
      "timestamp": "2025-01-15T12:32:15Z"
    }
  ],
  "session_started": "2025-01-15T12:30:00Z"
}
```

## Pseudocode

```python
async def audit_walkthrough(walkthrough_path, library_name, library_version):
    """Execute a walkthrough step-by-step and identify gaps."""

    # 1. Setup working directory
    working_dir = create_temp_dir("walkthrough_audit_")

    # 2. Setup MCP server configuration
    mcp_config = {
        "walkthrough": {
            "command": "uv",
            "args": ["run", "python", "-m", "stackbench.walkthroughs.mcp_server"]
        }
    }

    # 3. Create Claude agent with MCP server
    hooks = create_logging_hooks()

    options = ClaudeAgentOptions(
        system_prompt=AUDIT_SYSTEM_PROMPT,
        allowed_tools=["Bash", "Read", "Write", "Glob"],
        permission_mode="bypassPermissions",  # For MCP tools
        cwd=str(working_dir),
        mcp_servers=mcp_config,
        hooks=hooks
    )

    # 4. Ask Claude to audit
    prompt = f"""
    Audit this walkthrough by executing it step-by-step.

    Walkthrough: {walkthrough_path}
    Library: {library_name} v{library_version}

    WORKFLOW:
    1. Call mcp__walkthrough__start_walkthrough with path
    2. Loop:
       a. Call mcp__walkthrough__next_step
       b. Read step content
       c. Execute operations
       d. If issues found: call mcp__walkthrough__report_gap
       e. Continue to next step
    3. Complete when all steps done

    Begin now.
    """

    gaps = []
    completed_steps = 0
    failed_steps = 0

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        # 5. Monitor execution
        async for message in client.receive_response():
            # Track progress
            # Check for completion signals
            if "all steps completed" in message.text.lower():
                break

    # 6. Load gaps from MCP session file
    session_file = walkthrough_path.parent / f"{walkthrough_path.stem}_session.json"
    session_data = load_json(session_file)
    gaps = session_data["gaps"]
    completed_steps = session_data["completed_steps"]

    # 7. Create audit result
    result = AuditResult(
        walkthrough_id=walkthrough_path.stem,
        library_name=library_name,
        library_version=library_version,
        total_steps=count_steps(walkthrough_path),
        completed_steps=completed_steps,
        failed_steps=total_steps - completed_steps,
        gaps=gaps,
        ...
    )

    # 8. Save result
    save_json(output_folder / f"{walkthrough_path.stem}_audit.json", result)

    return result


# What Claude does internally
def claude_audit_logic(walkthrough_path):
    """Claude's step-by-step execution process."""

    # 1. Start walkthrough via MCP
    result = call_mcp_tool("mcp__walkthrough__start_walkthrough", {
        "walkthrough_path": str(walkthrough_path)
    })

    # Response: {"message": "Walkthrough started", "total_steps": 10}

    # 2. Loop through steps
    while True:
        # Get next step
        step_result = call_mcp_tool("mcp__walkthrough__next_step", {})

        if step_result["status"] == "complete":
            break

        step = step_result["step"]

        # 3. Read step content
        step_number = step["displayOrder"]
        step_title = step["title"]
        content = step["contentFields"]

        # 4. Execute operations
        operations = parse_operations(content["operationsForAgent"])

        for operation in operations:
            try:
                # Execute bash command
                if is_bash_command(operation):
                    result = run_bash(operation["command"])

                    # Check for errors
                    if result.exit_code != 0:
                        # Report execution gap
                        call_mcp_tool("mcp__walkthrough__report_gap", {
                            "gap_type": "execution_error",
                            "severity": "critical",
                            "description": f"Command failed: {operation['command']}",
                            "suggested_fix": f"Fix command or check prerequisites",
                            "context": result.stderr
                        })

                # Execute Python code
                elif is_python_code(operation):
                    result = run_bash(f"python -c '{operation['code']}'")

                    if result.exit_code != 0:
                        call_mcp_tool("mcp__walkthrough__report_gap", {
                            "gap_type": "execution_error",
                            "severity": "critical",
                            "description": "Python code failed",
                            "context": result.stderr
                        })

                # Check for undefined resources
                resources = extract_resources(operation)
                for resource in resources:
                    if not resource_exists(resource):
                        # Report logical flow gap
                        call_mcp_tool("mcp__walkthrough__report_gap", {
                            "gap_type": "logical_flow",
                            "severity": "critical",
                            "description": f"Step references '{resource}' not created earlier",
                            "suggested_fix": "Add step to create this resource before current step"
                        })

            except Exception as e:
                # Report execution gap
                call_mcp_tool("mcp__walkthrough__report_gap", {
                    "gap_type": "execution_error",
                    "severity": "critical",
                    "description": str(e),
                    "context": traceback.format_exc()
                })

        # 5. Check for clarity issues
        if is_unclear(content["contentForUser"]):
            call_mcp_tool("mcp__walkthrough__report_gap", {
                "gap_type": "clarity",
                "severity": "warning",
                "description": "Instructions are vague or ambiguous",
                "suggested_fix": "Make instructions more specific and actionable"
            })

        # 6. Check for missing prerequisites
        prerequisites = extract_prerequisites(content["contextForAgent"])
        for prereq in prerequisites:
            if not prereq_met(prereq):
                call_mcp_tool("mcp__walkthrough__report_gap", {
                    "gap_type": "prerequisite",
                    "severity": "warning",
                    "description": f"Prerequisite '{prereq}' not mentioned upfront",
                    "suggested_fix": "Add to prerequisites section"
                })

    # 7. Check status
    status_result = call_mcp_tool("mcp__walkthrough__walkthrough_status", {})

    # Response: {"current_step": 10, "total_steps": 10, "is_complete": true}

    return status_result


# MCP Server (step delivery)
class WalkthroughMCPServer:
    """MCP server that delivers walkthrough steps."""

    def __init__(self):
        self.walkthrough = None
        self.current_step_index = -1
        self.gaps = []
        self.session_file = None

    @mcp_tool
    def start_walkthrough(self, walkthrough_path: str):
        """Initialize walkthrough."""
        self.walkthrough = load_json(walkthrough_path)
        self.current_step_index = -1
        self.gaps = []
        self.session_file = Path(walkthrough_path).parent / f"{Path(walkthrough_path).stem}_session.json"

        # Create session file
        self.save_session()

        return {
            "message": "Walkthrough started",
            "total_steps": len(self.walkthrough["steps"])
        }

    @mcp_tool
    def next_step(self):
        """Get next step."""
        self.current_step_index += 1

        if self.current_step_index >= len(self.walkthrough["steps"]):
            return {
                "status": "complete",
                "message": "All steps completed"
            }

        step = self.walkthrough["steps"][self.current_step_index]

        # Save session
        self.save_session()

        return {
            "status": "in_progress",
            "step": step,
            "step_number": step["displayOrder"]
        }

    @mcp_tool
    def report_gap(self, gap_type: str, severity: str, description: str,
                   suggested_fix: str = None, context: str = None):
        """Report a gap found during execution."""
        current_step = self.walkthrough["steps"][self.current_step_index]

        gap = {
            "step_number": current_step["displayOrder"],
            "step_title": current_step["title"],
            "gap_type": gap_type,
            "severity": severity,
            "description": description,
            "suggested_fix": suggested_fix,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

        self.gaps.append(gap)

        # Save session
        self.save_session()

        return {
            "message": "Gap reported",
            "gap_count": len(self.gaps)
        }

    @mcp_tool
    def walkthrough_status(self):
        """Get current status."""
        return {
            "current_step": self.current_step_index,
            "total_steps": len(self.walkthrough["steps"]),
            "is_complete": self.current_step_index >= len(self.walkthrough["steps"]),
            "gap_count": len(self.gaps)
        }

    def save_session(self):
        """Save session state to file."""
        session_data = {
            "walkthrough_path": str(self.walkthrough),
            "current_step": self.current_step_index,
            "is_complete": self.current_step_index >= len(self.walkthrough["steps"]),
            "completed_steps": self.current_step_index + 1,
            "gaps": self.gaps,
            "session_started": self.session_started
        }

        with open(self.session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
```

## Key Features

### 1. **MCP Server Integration**

Agent can't see all steps at once - must call MCP tools:

```python
# Start
mcp__walkthrough__start_walkthrough(path)

# Get next step (one at a time)
mcp__walkthrough__next_step()

# Report issue
mcp__walkthrough__report_gap(type, severity, description, ...)

# Check status
mcp__walkthrough__walkthrough_status()
```

### 2. **Six Gap Categories**

```python
gap_types = [
    "clarity",           # Vague/unclear instructions
    "prerequisite",      # Missing setup requirements
    "logical_flow",      # References undefined resources
    "execution_error",   # Commands fail
    "completeness",      # Missing verification steps
    "cross_reference"    # Should link to other docs
]
```

### 3. **Three Severity Levels**

```python
# Critical: Blocks progress completely
severity = "critical"  # Can't continue

# Warning: Creates confusion/extra work
severity = "warning"   # Can work around

# Info: Minor improvement
severity = "info"      # Nice-to-have
```

### 4. **Sequential Execution**

MCP server enforces step order:
```python
# Can't skip ahead
step_1 = next_step()  # OK
step_2 = next_step()  # OK
step_5 = next_step()  # NO - must go through 3, 4 first
```

### 5. **State Persistence**

Session file tracks:
- Current step number
- All reported gaps
- Completion status
- Timestamps

## Logging & Debugging

### Logs
```
output_folder/agent_logs/
├── audit.log           # Human-readable
└── audit_tools.jsonl   # All tool calls (including MCP)
```

### Log Contents
- MCP tool calls (start, next_step, report_gap)
- Bash executions
- Gap reports
- Completion status

## Performance

- **Duration**: Depends on walkthrough complexity
- **Typical**: ~30-60 seconds for 10-step tutorial
- **Bottlenecks**: Command execution time

## Common Issues & Solutions

### Issue: MCP server not found
**Cause**: `mcp_server.py` path incorrect
**Solution**: Verify `mcp_server_path` or rely on auto-detection

### Issue: Agent skips steps
**Cause**: Not calling `next_step()` in loop
**Solution**: Check agent logs for MCP tool calls

### Issue: No gaps reported for obvious issues
**Cause**: Agent not detecting or not calling `report_gap`
**Solution**: Enhance prompt with specific gap detection patterns

### Issue: Session file not created
**Cause**: MCP server not saving state
**Solution**: Check MCP server logs, verify write permissions

## Implementation Notes

### Why MCP Server?

```python
# Alternative: Give agent full walkthrough JSON
# ❌ Problems:
# - Agent can skip steps
# - Can't simulate real user experience
# - No enforcement of sequential execution

# MCP Server approach:
# ✅ Enforces step-by-step execution
# ✅ Simulates real developer experience
# ✅ Structured gap reporting
# ✅ State tracking
```

### Gap Detection Strategy

```python
# Automatic detection
if command_failed:
    report_gap("execution_error", "critical", ...)

if resource_not_found:
    report_gap("logical_flow", "critical", ...)

# Heuristic detection
if unclear_instructions:
    report_gap("clarity", "warning", ...)

if missing_verification:
    report_gap("completeness", "info", ...)
```

## Related Documentation

- **Schemas**: `stackbench/walkthroughs/schemas.py` - `AuditResult`, `GapReport`
- **MCP Server**: `stackbench/walkthroughs/mcp_server.py`
- **CLI**: `stackbench walkthrough audit --walkthrough <path>`

## See Also

- [Walkthrough Generate Agent](./walkthrough-generate-agent.md) - Creates walkthrough JSON
- [MCP Server Documentation](../walkthroughs/mcp-server.md) - Step delivery protocol
