"""
Sub-agents for API completeness analysis.

The API completeness workflow is broken into 3 sequential sub-agents:
1. IntrospectionAgent: Discovers all APIs via introspection templates
2. MatchingAgent: Matches APIs to documentation
3. AnalysisAgent: Calculates metrics and builds final report
"""

from .introspection_agent import IntrospectionAgent
from .matching_agent import MatchingAgent
from .analysis_agent import AnalysisAgent

__all__ = ["IntrospectionAgent", "MatchingAgent", "AnalysisAgent"]
