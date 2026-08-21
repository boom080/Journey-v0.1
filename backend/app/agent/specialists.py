from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.schemas.agent import AgentSpecialist, AgentToolName

if TYPE_CHECKING:
    from app.agent.tool_registry import ToolExecution, ToolRuntime
    from app.schemas.agent import AgentPlanStep


@dataclass(frozen=True)
class SpecialistAgent:
    """Bounded specialist invoked by the orchestrator through an allowlist."""

    name: AgentSpecialist
    display_name: str
    tools: frozenset[AgentToolName]

    def execute(
        self,
        runtime: ToolRuntime,
        step: AgentPlanStep,
        handler: Callable[[ToolRuntime, AgentPlanStep], ToolExecution],
    ) -> ToolExecution:
        if step.tool not in self.tools:
            raise ValueError("specialist_tool_not_allowed")
        execution = handler(runtime, step)
        execution.specialist = self.name
        return execution


SPECIALIST_REGISTRY: dict[AgentSpecialist, SpecialistAgent] = {
    "record_agent": SpecialistAgent(
        name="record_agent",
        display_name="Record Agent",
        tools=frozenset(
            {"food.parse_candidate", "activity.parse_candidate", "weight.parse_candidate"}
        ),
    ),
    "health_knowledge_agent": SpecialistAgent(
        name="health_knowledge_agent",
        display_name="Health Knowledge Agent",
        tools=frozenset({"knowledge.answer", "knowledge.retrieve", "knowledge.safe_summary"}),
    ),
    "journey_summary_agent": SpecialistAgent(
        name="journey_summary_agent",
        display_name="Journey Summary Agent",
        tools=frozenset(
            {
                "context.load",
                "profile.read",
                "journey.read",
                "recommendation.generate",
                "weekly_summary.generate",
                "recommendation.rules_fallback",
            }
        ),
    ),
}


def specialist_for_tool(tool: str) -> AgentSpecialist:
    for specialist in SPECIALIST_REGISTRY.values():
        if tool in specialist.tools:
            return specialist.name
    return "orchestrator"


def selected_specialists(tools: list[str]) -> list[AgentSpecialist]:
    ordered: list[AgentSpecialist] = ["orchestrator"]
    for tool in tools:
        specialist = specialist_for_tool(tool)
        if specialist not in ordered:
            ordered.append(specialist)
    return ordered


def public_specialist_catalog() -> list[dict[str, Any]]:
    return [
        {
            "name": specialist.name,
            "display_name": specialist.display_name,
            "tools": sorted(specialist.tools),
        }
        for specialist in SPECIALIST_REGISTRY.values()
    ]
