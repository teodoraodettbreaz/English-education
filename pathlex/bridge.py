from __future__ import annotations

import copy
from typing import Any

from .audit import audit_story
from .generator import GeneratedStory
from .models import (
    AuditReport,
    OpportunitySlot,
    PracticeMode,
    StoryGraph,
    StoryPhase,
    StorySpec,
    StoryStatus,
    VerificationDecision,
    VerifiedOpportunity,
)
from .verifier import NodeVerification


def _enum_mode(value: Any) -> PracticeMode:
    try:
        return PracticeMode(str(value))
    except ValueError:
        return PracticeMode.EXPOSURE


def _enum_phase(value: Any, fallback: StoryPhase) -> StoryPhase:
    try:
        return StoryPhase(str(value))
    except ValueError:
        return fallback


def graph_with_generated_slots(
    planned_graph: StoryGraph, story: GeneratedStory
) -> StoryGraph:


    graph = copy.deepcopy(planned_graph)
    for node_id, graph_node in graph.nodes.items():
        generated = story.nodes.get(node_id)
        if generated is None:
            graph_node.verification_stale = True
            continue
        converted: list[OpportunitySlot] = []
        for index, raw in enumerate(generated.planned_slots):
            slot_id = str(raw.get("slot_id") or raw.get("id") or f"{node_id}:slot:{index + 1}")
            target_id = str(raw.get("target_id") or raw.get("lexical_unit_id") or "")
            if not target_id:
                continue
            try:
                occurrence_index = int(raw.get("occurrence_index") or index + 1)
            except (TypeError, ValueError):
                occurrence_index = index + 1
            converted.append(
                OpportunitySlot(
                    id=slot_id,
                    target_id=target_id,
                    node_id=node_id,
                    occurrence_index=occurrence_index,
                    mode=_enum_mode(raw.get("mode", "exposure")),
                    context_label=str(
                        raw.get("context_label") or raw.get("context") or "general"
                    ),
                    phase=_enum_phase(raw.get("phase"), graph_node.phase),
                    required_surface=str(
                        raw.get("required_surface")
                        or raw.get("surface")
                        or raw.get("word")
                        or ""
                    ),
                )
            )
        graph_node.slots = converted
        graph_node.version = generated.version
        graph_node.verification_stale = node_id not in story.verifications
    graph.version = max(graph.version, max((node.version for node in story.nodes.values()), default=0))
    return graph


def verified_opportunities(
    graph: StoryGraph, story: GeneratedStory
) -> list[VerifiedOpportunity]:
    slots = {
        slot.id: slot
        for node in graph.nodes.values()
        for slot in node.slots
    }
    records: list[VerifiedOpportunity] = []
    for node_id, raw_verification in story.verifications.items():
        if not isinstance(raw_verification, NodeVerification):
            continue
        structural_failure = bool(raw_verification.structural_errors)
        for verdict in raw_verification.verdicts:
            slot = slots.get(verdict.slot_id)
            if slot is None:
                continue
            label = "rejected" if structural_failure else verdict.label
            try:
                decision = VerificationDecision(label)
            except ValueError:
                decision = VerificationDecision.UNCERTAIN
            records.append(
                VerifiedOpportunity(
                    slot_id=slot.id,
                    target_id=slot.target_id,
                    node_id=node_id,
                    decision=decision,
                    confidence=verdict.confidence,
                    observed_mode=slot.mode,
                    observed_context=slot.context_label,
                    observed_phase=slot.phase,
                    reason=(
                        "; ".join(raw_verification.structural_errors)
                        if structural_failure
                        else verdict.reason
                    ),
                    checks={
                        "sense": False if structural_failure else verdict.sense_ok,
                        "part_of_speech": False if structural_failure else verdict.pos_ok,
                        "pattern": False if structural_failure else verdict.pattern_ok,
                        "grammar": False if structural_failure else verdict.grammar_ok,
                        "context": False if structural_failure else verdict.context_ok,
                        "mode": False if structural_failure else verdict.mode_ok,
                    },
                )
            )
    return records


def audit_generated_story(
    spec: StorySpec, planned_graph: StoryGraph, story: GeneratedStory
) -> AuditReport:
    graph = graph_with_generated_slots(planned_graph, story)
    generation_failed = story.status == "GENERATION_FAILURE" or len(story.nodes) < len(graph.nodes)
    report = audit_story(
        spec,
        graph,
        verified_opportunities(graph, story),
        generation_failed=generation_failed,
        failure_reason="; ".join(story.errors) if story.errors else "generation was incomplete",
    )


    structural = {
        node_id: list(node.structural_errors)
        for node_id, node in story.nodes.items()
        if node.structural_errors
    }
    if structural and report.status not in {
        StoryStatus.GENERATION_FAILURE,
        StoryStatus.PLAN_INFEASIBLE,
    }:
        report.status = StoryStatus.COUNTEREXAMPLE
        report.counterexample = report.counterexample or {
            "path": report.worst_path,
            "coverage": report.worst_coverage,
            "debts": [],
        }
        report.counterexample["structural_errors"] = structural
    return report


def repair_audit_payload(
    spec: StorySpec, planned_graph: StoryGraph, story: GeneratedStory
) -> dict[str, Any]:


    report = audit_generated_story(spec, planned_graph, story)
    payload = report.to_dict()
    counterexample = report.counterexample or {}
    payload["debts"] = list(counterexample.get("debts") or [])
    payload["counterexample_path"] = list(counterexample.get("path") or report.worst_path)
    return payload


__all__ = [
    "audit_generated_story",
    "graph_with_generated_slots",
    "repair_audit_payload",
    "verified_opportunities",
]

