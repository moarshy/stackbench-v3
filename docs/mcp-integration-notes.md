# MCP Integration Technical Notes

**Date:** 2025-10-29
**Related:** Clarity Agent, API Completeness Agent, Walkthrough System

---

## Key Learnings from MCP Integration

This document captures important technical details about integrating MCP servers with Claude Code agents in Stackbench.

### Critical: Permission Mode for MCP Tools

**Problem:** MCP tools require explicit permission to execute, even with standard permission modes like `acceptEdits`.

**Solution:** Agents that use MCP servers **must** set `permission_mode="bypassPermissions"` in `ClaudeAgentOptions`.

```python
options = ClaudeAgentOptions(
    system_prompt=SYSTEM_PROMPT,
    allowed_tools=["Read"],
    permission_mode="bypassPermissions",  # ← Required for MCP tools
    hooks=hooks,
    cwd=str(Path.cwd()),
    mcp_servers={
        "my-server": {
            "command": sys.executable,
            "args": ["-m", "stackbench.mcp_servers.my_server"],
        }
    }
)
```

**Affected Agents:**
- ✅ `clarity_agent.py` - Uses clarity-scoring MCP server
- ✅ `analysis_agent.py` (sub-agent) - Uses api-completeness MCP server
- ✅ `matching_agent.py` (sub-agent) - Uses api-completeness MCP server
- ✅ `introspection_agent.py` (sub-agent) - Uses Bash (no MCP, but uses bypassPermissions)
- ✅ `walkthrough_audit_agent.py` - Uses walkthrough MCP server

### Validation Hooks Still Work

**Important:** Setting `permission_mode="bypassPermissions"` does **NOT** disable validation hooks.

- Validation hooks intercept tool calls **before execution**
- They can still validate output and return `permissionDecision: 'deny'`
- The agent receives the denial feedback and must fix the output

**Example from `stackbench/hooks/validation.py:503-509`:**
```python
return {
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',  # ← Still blocks invalid writes
        'permissionDecisionReason': error_msg
    }
}
```

### Common MCP Server Bug: Missing Pydantic Fields

**Issue Found:** `clarity_scoring_server.py` was creating `ScoreBreakdown` objects without the required `base_score` field.

**Fix Applied (stackbench/mcp_servers/clarity_scoring_server.py:206):**
```python
breakdown = ScoreBreakdown(
    base_score=10.0,  # ← Was missing, caused validation errors
    critical_issues_penalty=critical_count * PENALTY_WEIGHTS["critical_issue"],
    # ... other fields
)
```

**Lesson:** Always ensure MCP server responses match the exact Pydantic schema expected by the agent.

### Testing MCP Server Integration

Created `test_mcp_server_agent.py` for verifying MCP server integration:

```bash
uv run python test_mcp_server_agent.py
```

**What it tests:**
- MCP server can be started and connected
- Agent can call MCP tools successfully
- MCP server returns properly formatted responses
- Pydantic validation passes

**Test Results:**
- ✅ MCP server returns all required fields
- ✅ Agent receives and parses responses correctly
- ✅ Scores calculated deterministically

### MCP Server Response Format

MCP servers return `TextContent` objects with JSON in the `.text` field:

```python
from mcp.server.models.primitives import TextContent

return [
    TextContent(
        type="text",
        text=json.dumps({
            "clarity_score": result.model_dump(),
            "breakdown": breakdown.model_dump(),
        }, indent=2),
    )
]
```

The Claude SDK automatically extracts the JSON from `.text` and provides it to the agent.

### Debugging MCP Issues

**Symptoms of MCP permission issues:**
- Agent says "MCP tool requires permission"
- Agent creates manual/hallucinated responses instead of calling MCP
- Tool calls appear in logs but return empty `{}`

**Diagnosis Steps:**
1. Check `permission_mode` is set to `bypassPermissions`
2. Check MCP server is configured correctly in `mcp_servers` dict
3. Verify MCP server Python module path is correct
4. Check agent logs at `data/<run_id>/validation_logs/<agent>_logs/*/tools.jsonl`
5. Look for `tool_output: null` or empty responses

**Tools Log Analysis:**
```bash
# Check if MCP tools are being called
grep "mcp__" data/<run_id>/validation_logs/clarity_logs/*/tools.jsonl

# Check for errors in tool responses
jq '.error' data/<run_id>/validation_logs/clarity_logs/*/tools.jsonl | grep -v null
```

### Best Practices

1. **Always use bypassPermissions for MCP agents** - No exceptions
2. **Validate MCP response schemas** - Use Pydantic models consistently
3. **Test MCP servers independently** - Use test scripts like `test_mcp_server_agent.py`
4. **Check agent logs** - Essential for debugging MCP integration issues
5. **Keep validation hooks** - They still provide value even with bypassPermissions

### Related Issues

**GitHub Issues:** (None yet - internal documentation)

**Related PRs:** (Add PR numbers here when changes are committed)

---

## Future Considerations

1. **Investigate permission granularity** - Can we bypass only for MCP tools, not all tools?
2. **MCP server error handling** - Better error messages when Pydantic validation fails
3. **MCP response caching** - Avoid recalculating deterministic scores
4. **MCP server health checks** - Detect when MCP servers fail to start

---

**Last Updated:** 2025-10-29
