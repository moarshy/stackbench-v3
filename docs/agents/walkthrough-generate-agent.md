# Walkthrough Generate Agent

## Objective

The Walkthrough Generate Agent converts tutorial/quickstart documentation into **structured, executable walkthroughs**. It:
- Analyzes tutorial documentation (markdown)
- Breaks down content into discrete, logical steps
- Extracts four content types per step (user-facing, agent context, operations, introduction)
- Validates output against `WalkthroughExport` schema via hooks
- Produces JSON that the Audit Agent can execute step-by-step

This agent is part of the **Walkthrough Validation System** - a standalone validation approach that simulates a real developer following a tutorial.

## Position in Pipeline

```
┌─────────────────────────────────────┐
│    WALKTHROUGH VALIDATION SYSTEM    │
│         (Standalone)                │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────┐
│ GENERATE AGENT          │ ◄── YOU ARE HERE
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
│ AUDIT AGENT             │
│  (Execution + Gaps)     │
└─────────────────────────┘
```

**Stage**: Standalone (not part of core pipeline)
**Runs**: On-demand via `stackbench walkthrough generate`
**Dependencies**: Tutorial markdown file
**Consumers**: MCP Server → Audit Agent

## Inputs

### Required
- **`output_folder`** (Path): Folder to save generated walkthroughs
- **`library_name`** (str): Name of the library being documented
- **`library_version`** (str): Version of the library
- **`doc_path`** (Path): Path to tutorial/quickstart markdown file

### Optional
- **`walkthrough_id`** (str): Custom ID for the walkthrough (default: `wt_{doc_name}`)

### Environment
- Tutorial documentation file (markdown)
- Claude SDK for agent execution

## Expected Output

### Output Files

```
output_folder/
├── wt_{id}.json                           # Generated walkthrough
└── agent_logs/
    ├── generate.log                       # Human-readable log
    ├── generate_tools.jsonl               # Tool call trace
    └── validation_logs/
        └── walkthrough_generation_validation_calls.txt
```

### Output Schema (`wt_{id}.json`)

```json
{
  "version": "1.0",
  "exportedAt": "2025-01-15T12:00:00Z",

  "walkthrough": {
    "title": "Getting Started with LanceDB",
    "description": "A comprehensive quickstart guide to LanceDB",
    "type": "quickstart",
    "status": "published",
    "createdAt": 1705320000000,
    "updatedAt": 1705320000000,
    "estimatedDurationMinutes": 30,
    "tags": ["python", "database", "quickstart"],
    "metadata": null
  },

  "steps": [
    {
      "title": "Install Dependencies",
      "contentFields": {
        "version": "v1",
        "contentForUser": "# Install Dependencies\n\nFirst, install LanceDB:\n\n```bash\npip install lancedb\n```",
        "contextForAgent": "LanceDB requires Python 3.8+ and pip. The installation includes PyArrow dependencies which may take a few minutes on first install.",
        "operationsForAgent": "1. Run: pip install lancedb\n2. Verify installation: python -c 'import lancedb; print(lancedb.__version__)'\n3. Expected output: 0.25.2 or similar",
        "introductionForAgent": "This step ensures the LanceDB library is installed in the environment before proceeding with the tutorial."
      },
      "displayOrder": 0,
      "createdAt": 1705320000000,
      "updatedAt": 1705320000000,
      "metadata": {"imported": true},
      "nextStepReference": 1
    },
    {
      "title": "Connect to Database",
      "contentFields": {
        "version": "v1",
        "contentForUser": "# Connect to Database\n\nConnect to a LanceDB database:\n\n```python\nimport lancedb\ndb = lancedb.connect(\"./data/sample-lancedb\")\n```",
        "contextForAgent": "LanceDB uses a directory-based storage model. The connect() function creates the directory if it doesn't exist.",
        "operationsForAgent": "1. Create Python script or interactive session\n2. Import lancedb\n3. Run: db = lancedb.connect(\"./data/sample-lancedb\")\n4. Verify: Database directory should exist at ./data/sample-lancedb",
        "introductionForAgent": "This step establishes a connection to a LanceDB database, which is required for all subsequent operations."
      },
      "displayOrder": 1,
      "createdAt": 1705320000000,
      "updatedAt": 1705320000000,
      "metadata": {"imported": true},
      "nextStepReference": 2
    },
    {
      "title": "Create a Table",
      "contentFields": {
        "version": "v1",
        "contentForUser": "# Create a Table\n\nCreate a table with sample data:\n\n```python\nimport pandas as pd\n\ndata = [\n    {\"vector\": [1.0, 2.0], \"item\": \"apple\"},\n    {\"vector\": [3.0, 4.0], \"item\": \"banana\"}\n]\ntable = db.create_table(\"fruits\", data)\n```",
        "contextForAgent": "LanceDB tables are created from Python data structures (lists of dicts, pandas DataFrames, PyArrow tables). The 'vector' field is required for vector search.",
        "operationsForAgent": "1. Define data structure with vector field\n2. Run: table = db.create_table(\"fruits\", data)\n3. Verify: Table should appear in db.list_tables()\n4. Expected: table object ready for queries",
        "introductionForAgent": "This step creates a LanceDB table with sample data, demonstrating the basic table creation API."
      },
      "displayOrder": 2,
      "createdAt": 1705320000000,
      "updatedAt": 1705320000000,
      "metadata": {"imported": true},
      "nextStepReference": null
    }
  ],

  "metadata": {
    "originalDocPath": "/path/to/quickstart.md",
    "generatedBy": "stackbench-walkthrough-generator"
  }
}
```

## Pseudocode

```python
async def generate_walkthrough(doc_path, library_name, library_version):
    """Generate a walkthrough from a tutorial."""

    # 1. Read tutorial documentation
    content = read_file(doc_path)

    # 2. Setup validation hooks
    hooks = {
        'PreToolUse': [
            validation_hook,  # Validates against WalkthroughExport schema
            logging_hook      # Logs all tool calls
        ],
        'PostToolUse': [logging_hook]
    }

    # 3. Create Claude agent
    options = ClaudeAgentOptions(
        system_prompt=GENERATION_SYSTEM_PROMPT,
        allowed_tools=["Read", "Write"],
        hooks=hooks
    )

    # 4. Ask Claude to generate walkthrough
    prompt = f"""
    Analyze this tutorial and create a step-by-step walkthrough.

    Document: {doc_path}
    Library: {library_name} v{library_version}

    Content:
    {content}

    Break into logical steps (typically 5-15 for a quickstart).

    For each step, provide:
    - title: Action-oriented (e.g., "Install Dependencies")
    - contentForUser: User-facing markdown with code blocks
    - contextForAgent: Background knowledge agent needs
    - operationsForAgent: Exact commands to execute
    - introductionForAgent: Purpose and goals

    Save to: {output_file}

    Use Write tool to save the JSON.
    """

    await claude.query(prompt)

    # 5. Agent uses Write tool → validation hook runs
    # If validation passes → file saved
    # If validation fails → hook blocks write, sends error to Claude

    # 6. Load generated file
    walkthrough_data = load_json(output_file)

    # 7. Parse and return
    return WalkthroughExport(**walkthrough_data)


# What Claude does internally
def claude_generation_logic(content, library_name, library_version):
    """Claude's analysis and structuring process."""

    # 1. Identify logical sections
    sections = parse_markdown_sections(content)

    # 2. Break into steps
    steps = []

    for section in sections:
        # Identify discrete operations
        operations = identify_operations(section)

        # Group related operations into steps
        for op_group in group_operations(operations):
            step = create_step(op_group, section)
            steps.append(step)

    # 3. For each step, extract 4 content fields
    structured_steps = []

    for i, step in enumerate(steps):
        # contentForUser: User-facing markdown
        content_for_user = extract_user_content(step)

        # contextForAgent: What agent needs to know
        context_for_agent = f"""
        {extract_background_info(step)}
        {extract_expected_behavior(step)}
        {extract_dependencies_on_previous_steps(step, steps[:i])}
        """

        # operationsForAgent: Exact commands
        operations_for_agent = f"""
        1. {extract_bash_command(step)}
        2. {extract_verification_step(step)}
        3. Expected: {extract_success_criteria(step)}
        """

        # introductionForAgent: Purpose
        introduction_for_agent = f"This step {extract_purpose(step)}."

        structured_steps.append({
            "title": step.title,
            "contentFields": {
                "version": "v1",
                "contentForUser": content_for_user,
                "contextForAgent": context_for_agent.strip(),
                "operationsForAgent": operations_for_agent.strip(),
                "introductionForAgent": introduction_for_agent
            },
            "displayOrder": i,
            "createdAt": now_ms,
            "updatedAt": now_ms,
            "metadata": {"imported": True},
            "nextStepReference": i + 1 if i < len(steps) - 1 else null
        })

    # 4. Create walkthrough metadata
    walkthrough = {
        "title": extract_title(content),
        "description": extract_description(content),
        "type": detect_type(content),  # quickstart, tutorial, guide
        "status": "published",
        "createdAt": now_ms,
        "updatedAt": now_ms,
        "estimatedDurationMinutes": estimate_duration(structured_steps),
        "tags": extract_tags(content, library_name)
    }

    # 5. Create export object
    export = {
        "version": "1.0",
        "exportedAt": now_iso,
        "walkthrough": walkthrough,
        "steps": structured_steps,
        "metadata": {
            "originalDocPath": doc_path,
            "generatedBy": "stackbench-walkthrough-generator"
        }
    }

    # 6. Write JSON (validation hook will check schema)
    use_write_tool(output_file, json.dumps(export, indent=2))

    return export


def extract_operations(section):
    """Identify discrete operations in a section."""

    operations = []

    # Pattern 1: Bash commands
    bash_blocks = find_code_blocks(section, language="bash")
    for block in bash_blocks:
        operations.append({
            "type": "bash_command",
            "command": block.code,
            "description": extract_preceding_text(block)
        })

    # Pattern 2: Python code blocks
    python_blocks = find_code_blocks(section, language="python")
    for block in python_blocks:
        operations.append({
            "type": "python_code",
            "code": block.code,
            "description": extract_preceding_text(block),
            "expected_output": extract_following_text(block)
        })

    # Pattern 3: File creation
    file_patterns = ["create a file", "save to", "edit"]
    if any(pattern in section.text.lower() for pattern in file_patterns):
        operations.append({
            "type": "file_operation",
            "description": extract_file_operation_details(section)
        })

    return operations


def group_operations(operations):
    """Group related operations into steps."""

    groups = []
    current_group = []

    for op in operations:
        # Start new group if operation is independent
        if is_independent_operation(op):
            if current_group:
                groups.append(current_group)
            current_group = [op]
        else:
            # Add to current group
            current_group.append(op)

    if current_group:
        groups.append(current_group)

    return groups
```

## Key Features

### 1. **Four Content Fields**

Each step has exactly 4 content fields:

```json
{
  "contentForUser": "What the user sees (markdown with code)",
  "contextForAgent": "What the agent needs to know (background)",
  "operationsForAgent": "What the agent should do (commands)",
  "introductionForAgent": "Why this step matters (purpose)"
}
```

### 2. **Schema Validation via Hooks**

Before writing JSON:
```python
@PreToolUse hook (on Write)
def validate_walkthrough_json(json_data):
    try:
        WalkthroughExport(**json_data)
        return True  # Allow write
    except ValidationError as e:
        send_error_to_claude(e)
        return False  # Block write
```

### 3. **Linked Steps**

Each step references the next:
```python
# Step 0
"nextStepReference": 1

# Step 1
"nextStepReference": 2

# Last step
"nextStepReference": null
```

### 4. **Duration Estimation**

Estimates time based on:
- Number of steps
- Complexity of operations (bash vs code)
- Number of verification steps

```python
duration = (
    num_steps * 2 +                    # Base 2 min per step
    num_bash_commands * 1 +            # 1 min per bash
    num_python_blocks * 3 +            # 3 min per code block
    num_file_operations * 2            # 2 min per file op
)
```

## Logging & Debugging

### Logs
```
output_folder/agent_logs/
├── generate.log         # Human-readable
├── generate_tools.jsonl # Tool calls
└── validation_logs/
    └── walkthrough_generation_validation_calls.txt
```

### Log Contents
- Read tool calls (for reading doc)
- Write tool call with full JSON
- Validation hook failures with Pydantic errors

## Performance

- **Single document**: ~10-15 seconds
- **Typical output**: 5-15 steps per tutorial
- **Bottlenecks**: Claude analysis time

## Common Issues & Solutions

### Issue: Validation hook fails with "Missing required field"
**Cause**: Generated JSON doesn't match schema
**Solution**: Check `validation_logs/` for specific Pydantic error

### Issue: Steps too granular (50+ steps for simple tutorial)
**Cause**: Agent breaking down too much
**Solution**: Adjust prompt to group related operations

### Issue: operationsForAgent too vague
**Cause**: Agent not being specific enough
**Solution**: Emphasize "exact commands" in prompt

### Issue: Missing nextStepReference on last step
**Cause**: Agent set to integer instead of null
**Solution**: Hook validates this - agent will fix

## Implementation Notes

### Why Write Tool?

```python
# Alternative: Return JSON in response
# ❌ Problems:
# - No validation until after response complete
# - Can't iterate on errors
# - Large JSON in text blocks

# Write Tool approach:
# ✅ Validation happens immediately
# ✅ Agent can fix errors and retry
# ✅ Clean file output
```

### Schema Enforcement

The validation hook ensures:
- All required fields present
- Correct data types
- Valid step references
- Proper timestamp formats

## Related Documentation

- **Schemas**: `stackbench/walkthroughs/schemas.py` - `WalkthroughExport`, `WalkthroughStep`, `ContentFields`
- **Hooks**: `stackbench/hooks/validation.py` - `create_walkthrough_generation_validation_hook()`
- **CLI**: `stackbench walkthrough generate --repo <url> --doc-path <path>`

## See Also

- [Walkthrough Audit Agent](./walkthrough-audit-agent.md) - Executes generated walkthroughs
- [MCP Server](../walkthroughs/mcp-server.md) - Delivers steps to audit agent
