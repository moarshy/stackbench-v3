#!/usr/bin/env python3
"""
Simple test to verify MCP server integration with Claude Code agent.

This test creates a minimal agent that calls the clarity scoring MCP server
to verify the server returns data correctly.
"""

import asyncio
import json
import sys
from pathlib import Path

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)

async def test_mcp_server():
    """Test that MCP server returns data correctly."""

    print("🧪 Testing Clarity MCP Server Integration")
    print("=" * 60)

    # Create agent options with MCP server configured
    # NOTE: bypassPermissions allows MCP tools to run without asking for permission
    options = ClaudeAgentOptions(
        system_prompt="You are a test agent. Call the calculate_clarity_score MCP tool with the provided test data.",
        allowed_tools=[],  # No file tools needed, just MCP
        permission_mode="bypassPermissions",  # Required for MCP tools to work without prompting
        cwd=str(Path.cwd()),
        mcp_servers={
            "clarity-scoring": {
                "command": sys.executable,
                "args": ["-m", "stackbench.mcp_servers.clarity_scoring_server"],
            }
        }
    )

    # Test data - minimal valid input
    test_issues = [
        {
            "type": "clarity",
            "severity": "warning",
            "description": "Step 1 is unclear",
            "line": 10,
            "section": "Introduction",
            "suggestion": "Add more detail"
        }
    ]

    test_metrics = {
        "total_steps": 5,
        "total_code_blocks": 3,
        "has_prerequisites": True,
        "has_verification": False,
        "total_headings": 4,
        "failed_api_validations": 0,
        "failed_code_examples": 0
    }

    prompt = f"""Call the calculate_clarity_score MCP tool with these parameters:

issues: {json.dumps(test_issues, indent=2)}

metrics: {json.dumps(test_metrics, indent=2)}

After calling the tool, tell me what you received back. Include the full response data.
"""

    print("\n📤 Sending test prompt to agent...")
    print(f"Prompt: {prompt[:200]}...\n")

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            response_text = ""
            tool_calls_seen = []

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text
                            print(f"Agent: {block.text}")
                        else:
                            # Track tool calls
                            block_type = type(block).__name__
                            tool_calls_seen.append(block_type)
                            print(f"[Tool Call: {block_type}]")

            print("\n" + "=" * 60)
            print("✅ Test completed!")
            print(f"\nTool calls observed: {tool_calls_seen}")
            print(f"\nAgent response length: {len(response_text)} chars")

            # Check if response looks valid
            if "clarity_score" in response_text.lower() or "overall" in response_text.lower():
                print("\n✅ Response contains expected keywords (clarity_score/overall)")
            else:
                print("\n⚠️  Response doesn't contain expected keywords")
                print(f"Preview: {response_text[:300]}")

            return response_text

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_mcp_server())

    if result:
        print("\n" + "=" * 60)
        print("Full response:")
        print(result)
    else:
        print("\n❌ No response received")
        sys.exit(1)
