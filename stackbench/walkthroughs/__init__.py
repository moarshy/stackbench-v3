"""
Stackbench Walkthroughs - Interactive Documentation Validation

This module provides tools for:
1. Generating step-by-step walkthroughs from documentation
2. Auditing walkthroughs by executing them with Claude Code agents
3. Identifying gaps and issues through dynamic execution
"""

from .schemas import (
    ContentFields,
    WalkthroughStep,
    WalkthroughMetadata,
    Walkthrough,
    WalkthroughExport,
    GapReport,
    AuditResult,
    WalkthroughSession,
)

from .walkthrough_generate_agent import WalkthroughGenerateAgent
from .walkthrough_audit_agent import WalkthroughAuditAgent

__all__ = [
    # Schemas
    "ContentFields",
    "WalkthroughStep",
    "WalkthroughMetadata",
    "Walkthrough",
    "WalkthroughExport",
    "GapReport",
    "AuditResult",
    "WalkthroughSession",
    # Agents
    "WalkthroughGenerateAgent",
    "WalkthroughAuditAgent",
]
