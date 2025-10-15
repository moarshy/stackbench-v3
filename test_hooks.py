#!/usr/bin/env python3
"""
Test script to verify hooks are working with Claude SDK.
"""

import asyncio
from pathlib import Path
from typing import Any, Optional
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, HookMatcher, HookContext

# Simple logging directory
LOG_DIR = Path("./test_hooks_output")
LOG_DIR.mkdir(exist_ok=True)

async def pre_tool_hook(
    input_data: dict[str, Any],
    tool_use_id: Optional[str],
    context: HookContext
) -> dict[str, Any]:
    """Log all tool calls before execution."""
    tool_name = input_data.get('tool_name', 'unknown')
    tool_input = input_data.get('tool_input', {})

    log_file = LOG_DIR / "pre_tool_calls.txt"
    with open(log_file, 'a') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"PRE-TOOL: {tool_name}\n")
        f.write(f"Tool Use ID: {tool_use_id}\n")
        f.write(f"Input: {tool_input}\n")
        f.write(f"{'='*80}\n")

    print(f"✅ PRE-TOOL HOOK FIRED: {tool_name}")
    return {}

async def post_tool_hook(
    input_data: dict[str, Any],
    tool_use_id: Optional[str],
    context: HookContext
) -> dict[str, Any]:
    """Log all tool calls after execution."""
    tool_name = input_data.get('tool_name', 'unknown')

    log_file = LOG_DIR / "post_tool_calls.txt"
    with open(log_file, 'a') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"POST-TOOL: {tool_name}\n")
        f.write(f"Tool Use ID: {tool_use_id}\n")
        f.write(f"{'='*80}\n")

    print(f"✅ POST-TOOL HOOK FIRED: {tool_name}")
    return {}

async def test_hooks():
    """Test that hooks fire during Claude SDK usage."""
    print("🧪 Testing Claude Code hooks...")
    print(f"📁 Logs will be saved to: {LOG_DIR}")

    # Create a test file for Claude to read
    test_file = LOG_DIR / "test_document.txt"
    test_file.write_text("This is a test document for Claude to read.")

    # Configure hooks
    hooks = {
        'PreToolUse': [
            HookMatcher(hooks=[pre_tool_hook])  # Match all tools
        ],
        'PostToolUse': [
            HookMatcher(hooks=[post_tool_hook])  # Match all tools
        ]
    }

    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits",
        hooks=hooks,
        cwd=str(Path.cwd())
    )

    print("\n🤖 Creating Claude client with hooks...")
    async with ClaudeSDKClient(options=options) as client:
        print("🤖 Sending query to Claude...")
        await client.query(f"Please read the file at {test_file} and tell me what it says.")

        print("\n📥 Waiting for response...")
        response_text = ""
        async for message in client.receive_response():
            from claude_agent_sdk import AssistantMessage, TextBlock
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text

        print(f"\n💬 Claude's response: {response_text[:200]}...")

    # Check if hooks fired
    pre_log = LOG_DIR / "pre_tool_calls.txt"
    post_log = LOG_DIR / "post_tool_calls.txt"

    print("\n" + "="*80)
    print("📊 HOOK RESULTS:")
    print("="*80)

    if pre_log.exists():
        content = pre_log.read_text()
        pre_count = content.count("PRE-TOOL:")
        print(f"✅ PreToolUse hooks: {pre_count} calls logged")
        print(f"   Log file: {pre_log}")
    else:
        print(f"❌ PreToolUse hooks: No log file found")

    if post_log.exists():
        content = post_log.read_text()
        post_count = content.count("POST-TOOL:")
        print(f"✅ PostToolUse hooks: {post_count} calls logged")
        print(f"   Log file: {post_log}")
    else:
        print(f"❌ PostToolUse hooks: No log file found")

    print("="*80)
    print("\n🎯 If hooks are working, you should see log files with tool calls above.")
    print("   If not, hooks may not be firing during Claude SDK operations.")

if __name__ == "__main__":
    asyncio.run(test_hooks())
