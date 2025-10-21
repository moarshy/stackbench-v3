"""
MCP Server for Walkthrough Execution

This MCP server provides tools to the audit agent for step-by-step
walkthrough execution. It runs as a stdio-based server that communicates
with the Claude Code agent.

Tools provided:
- start_walkthrough: Initialize a walkthrough session
- next_step: Get the next step in the walkthrough
- walkthrough_status: Get current progress
- report_gap: Report an issue found during execution
"""

import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Handle both relative imports (when used as module) and absolute imports (when run as script)
try:
    from .schemas import Walkthrough, WalkthroughExport, WalkthroughSession, GapReport
except ImportError:
    from schemas import Walkthrough, WalkthroughExport, WalkthroughSession, GapReport


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/walkthrough_mcp_server.log')]
)
logger = logging.getLogger(__name__)


class WalkthroughMCPServer:
    """MCP Server for walkthrough execution."""

    def __init__(self):
        """Initialize the MCP server."""
        self.server = Server("walkthrough-server")
        self.session: Optional[WalkthroughSession] = None
        self.walkthrough_data: Optional[Walkthrough] = None
        self.session_file: Optional[Path] = None  # File to save session state

        # Register tools
        self._register_tools()
        logger.info("WalkthroughMCPServer initialized")

    def _save_session_state(self):
        """Save current session state to JSON file for the audit agent to read."""
        if not self.session or not self.session_file:
            return

        try:
            session_data = {
                "walkthrough_id": self.session.walkthrough_id,
                "current_step": self.session.current_step_number,
                "total_steps": self.session.total_steps,
                "completed_steps": self.session.current_step_index,
                "is_complete": self.session.is_complete,
                "gaps": [
                    {
                        "step_number": gap.step_number,
                        "step_title": gap.step_title,
                        "gap_type": gap.gap_type,
                        "severity": gap.severity,
                        "description": gap.description,
                        "suggested_fix": gap.suggested_fix,
                        "context": gap.context,
                        "timestamp": gap.timestamp
                    }
                    for gap in self.session.gaps_reported
                ],
                "last_updated": datetime.now().isoformat()
            }

            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)

            logger.debug(f"Session state saved to {self.session_file}")
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")

    def _register_tools(self):
        """Register all MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="start_walkthrough",
                    description=(
                        "Initialize a walkthrough session by loading the walkthrough JSON file. "
                        "This must be called before using other walkthrough tools."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "walkthrough_path": {
                                "type": "string",
                                "description": "Path to the walkthrough JSON file"
                            }
                        },
                        "required": ["walkthrough_path"]
                    }
                ),
                Tool(
                    name="next_step",
                    description=(
                        "Get the next step in the walkthrough. Returns the step details including "
                        "contentForUser, contextForAgent, operationsForAgent, and introductionForAgent. "
                        "Automatically advances to the next step."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="walkthrough_status",
                    description=(
                        "Get the current walkthrough status including current step number, "
                        "total steps, progress percentage, and gaps reported so far."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="report_gap",
                    description=(
                        "Report a gap or issue found during walkthrough execution. "
                        "Use this when you encounter unclear instructions, missing prerequisites, "
                        "execution errors, or other documentation issues."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "gap_type": {
                                "type": "string",
                                "enum": [
                                    "clarity",
                                    "prerequisite",
                                    "logical_flow",
                                    "execution_error",
                                    "completeness",
                                    "cross_reference"
                                ],
                                "description": "Type of gap encountered"
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["critical", "warning", "info"],
                                "description": "Severity level"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of the gap"
                            },
                            "suggested_fix": {
                                "type": "string",
                                "description": "Optional suggested fix or improvement"
                            },
                            "context": {
                                "type": "string",
                                "description": "Optional additional context (error messages, etc.)"
                            }
                        },
                        "required": ["gap_type", "severity", "description"]
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            try:
                logger.info(f"Tool called: {name} with arguments: {arguments}")

                if name == "start_walkthrough":
                    return await self._start_walkthrough(arguments)
                elif name == "next_step":
                    return await self._next_step()
                elif name == "walkthrough_status":
                    return await self._walkthrough_status()
                elif name == "report_gap":
                    return await self._report_gap(arguments)
                else:
                    error_msg = f"Unknown tool: {name}"
                    logger.error(error_msg)
                    return [TextContent(type="text", text=json.dumps({"error": error_msg}))]

            except Exception as e:
                error_msg = f"Error executing tool {name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return [TextContent(type="text", text=json.dumps({"error": error_msg}))]

    async def _start_walkthrough(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Initialize walkthrough session."""
        walkthrough_path = arguments.get("walkthrough_path")

        if not walkthrough_path:
            return [TextContent(type="text", text=json.dumps({
                "error": "walkthrough_path is required"
            }))]

        path = Path(walkthrough_path)
        if not path.exists():
            return [TextContent(type="text", text=json.dumps({
                "error": f"Walkthrough file not found: {walkthrough_path}"
            }))]

        try:
            # Load walkthrough JSON
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Parse as WalkthroughExport (top-level format)
            walkthrough_export = WalkthroughExport(**data)

            # Create Walkthrough object (without version/exportedAt wrapper)
            self.walkthrough_data = Walkthrough(
                walkthrough=walkthrough_export.walkthrough,
                steps=walkthrough_export.steps,
                metadata=walkthrough_export.metadata
            )

            # Create session
            walkthrough_id = path.stem  # Use filename as ID
            self.session = WalkthroughSession(
                walkthrough_id=walkthrough_id,
                walkthrough=self.walkthrough_data
            )

            # Set session file path (save in same directory as walkthrough)
            self.session_file = path.parent / f"{walkthrough_id}_session.json"

            logger.info(f"Walkthrough session started: {walkthrough_id}")
            logger.info(f"Total steps: {self.session.total_steps}")
            logger.info(f"Session file: {self.session_file}")

            # Save initial session state
            self._save_session_state()

            result = {
                "status": "started",
                "walkthrough_id": walkthrough_id,
                "title": self.walkthrough_data.walkthrough.title,
                "description": self.walkthrough_data.walkthrough.description,
                "total_steps": self.session.total_steps,
                "estimated_duration_minutes": self.walkthrough_data.walkthrough.estimatedDurationMinutes
            }

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Failed to load walkthrough: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({
                "error": f"Failed to load walkthrough: {str(e)}"
            }))]

    async def _next_step(self) -> list[TextContent]:
        """Get the next step in the walkthrough."""
        if not self.session:
            return [TextContent(type="text", text=json.dumps({
                "error": "No active session. Call start_walkthrough first."
            }))]

        if self.session.is_complete:
            return [TextContent(type="text", text=json.dumps({
                "status": "complete",
                "message": "All steps completed!",
                "total_steps": self.session.total_steps,
                "gaps_reported": len(self.session.gaps_reported)
            }))]

        # Get current step
        step = self.session.walkthrough.steps[self.session.current_step_index]

        # Prepare response
        result = {
            "step_number": self.session.current_step_number,
            "total_steps": self.session.total_steps,
            "title": step.title,
            "contentForUser": step.contentFields.contentForUser,
            "contextForAgent": step.contentFields.contextForAgent,
            "operationsForAgent": step.contentFields.operationsForAgent,
            "introductionForAgent": step.contentFields.introductionForAgent,
            "displayOrder": step.displayOrder,
            "nextStepReference": step.nextStepReference
        }

        # Advance to next step
        self.session.current_step_index += 1

        # Save session state after advancing
        self._save_session_state()

        logger.info(f"Returned step {result['step_number']}/{result['total_steps']}: {step.title}")

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _walkthrough_status(self) -> list[TextContent]:
        """Get current walkthrough status."""
        if not self.session:
            return [TextContent(type="text", text=json.dumps({
                "error": "No active session. Call start_walkthrough first."
            }))]

        result = {
            "walkthrough_id": self.session.walkthrough_id,
            "title": self.session.walkthrough.walkthrough.title,
            "current_step": self.session.current_step_number,
            "total_steps": self.session.total_steps,
            "progress_percentage": round(self.session.progress_percentage, 2),
            "is_complete": self.session.is_complete,
            "gaps_reported": len(self.session.gaps_reported),
            "gaps_by_severity": {
                "critical": sum(1 for g in self.session.gaps_reported if g.severity == "critical"),
                "warning": sum(1 for g in self.session.gaps_reported if g.severity == "warning"),
                "info": sum(1 for g in self.session.gaps_reported if g.severity == "info")
            }
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _report_gap(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """Report a gap found during execution."""
        if not self.session:
            return [TextContent(type="text", text=json.dumps({
                "error": "No active session. Call start_walkthrough first."
            }))]

        gap_type = arguments.get("gap_type")
        severity = arguments.get("severity")
        description = arguments.get("description")
        suggested_fix = arguments.get("suggested_fix")
        context = arguments.get("context")

        if not all([gap_type, severity, description]):
            return [TextContent(type="text", text=json.dumps({
                "error": "gap_type, severity, and description are required"
            }))]

        # Get current step (the one we just executed)
        step_number = self.session.current_step_number - 1 if self.session.current_step_index > 0 else 1
        step_index = step_number - 1
        step_title = self.session.walkthrough.steps[step_index].title if step_index < len(self.session.walkthrough.steps) else "Unknown"

        # Create gap report
        gap = GapReport(
            step_number=step_number,
            step_title=step_title,
            gap_type=gap_type,
            severity=severity,
            description=description,
            suggested_fix=suggested_fix,
            context=context
        )

        self.session.gaps_reported.append(gap)

        # Save session state after reporting gap
        self._save_session_state()

        logger.info(f"Gap reported for step {step_number}: {gap_type} ({severity})")

        result = {
            "status": "gap_reported",
            "step_number": step_number,
            "step_title": step_title,
            "gap_type": gap_type,
            "severity": severity,
            "total_gaps_reported": len(self.session.gaps_reported)
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def run(self):
        """Run the MCP server."""
        logger.info("Starting MCP server...")
        async with stdio_server() as (read_stream, write_stream):
            logger.info("MCP server running on stdio")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point for the MCP server."""
    server = WalkthroughMCPServer()
    await server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
