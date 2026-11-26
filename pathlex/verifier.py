from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from .generator import GeneratedNode, GeneratedStory, structural_node_checks
from .llm import LLMError, LLMProvider, complete_json
from .prompts import to_plain, verification_messages


VALID_LABELS = {"accepted", "rejected", "uncertain"}


@dataclass(slots=True)
class OpportunityVerdict:
    slot_id: str
    target_id: str
    label: str
    confidence: float
    sense_ok: bool
    pos_ok: bool
    pattern_ok: bool
    grammar_ok: bool
    context_ok: bool
    mode_ok: bool
    evidence_span: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OpportunityVerdict":
        return cls(
            slot_id=str(payload.get("slot_id") or ""),
            target_id=str(payload.get("target_id") or ""),
            label=str(payload.get("label") or "uncertain"),
            confidence=float(payload.get("confidence") or 0.0),
            sense_ok=bool(payload.get("sense_ok")),
            pos_ok=bool(payload.get("pos_ok")),
            pattern_ok=bool(payload.get("pattern_ok")),
            grammar_ok=bool(payload.get("grammar_ok")),
            context_ok=bool(payload.get("context_ok")),
            mode_ok=bool(payload.get("mode_ok")),
            evidence_span=str(payload.get("evidence_span") or ""),
            reason=str(payload.get("reason") or ""),
        )


@dataclass(slots=True)
class NodeVerification:
    node_id: str
    status: str
    verdicts: list[OpportunityVerdict]
    structural_errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "verdicts": [verdict.to_dict() for verdict in self.verdicts],
            "structural_errors": list(self.structural_errors),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NodeVerification":
        return cls(
            node_id=str(payload.get("node_id") or ""),
            status=str(payload.get("status") or "UNKNOWN"),
            verdicts=[
                OpportunityVerdict.from_dict(item)
                for item in payload.get("verdicts") or []
                if isinstance(item, dict)
            ],
            structural_errors=[
                str(item) for item in payload.get("structural_errors") or []
            ],
            notes=[str(item) for item in payload.get("notes") or []],
        )

    @property
    def accepted_records(self) -> list[dict[str, Any]]:
        if self.structural_errors:
            return []
        return [verdict.to_dict() for verdict in self.verdicts if verdict.label == "accepted"]


@dataclass(slots=True)
class StoryVerification:
    status: str
    nodes: dict[str, NodeVerification]
    accepted_records: list[dict[str, Any]]
    rejected_count: int
    uncertain_count: int
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "nodes": {key: value.to_dict() for key, value in self.nodes.items()},
            "accepted_records": copy.deepcopy(self.accepted_records),
            "rejected_count": self.rejected_count,
            "uncertain_count": self.uncertain_count,
            "errors": list(self.errors),
        }

    def to_core_verifications(self, story: GeneratedStory) -> list[Any]:


        from .models import (
            PracticeMode,
            StoryPhase,
            VerificationDecision,
            VerifiedOpportunity,
        )

        records: list[VerifiedOpportunity] = []
        for node_id, node_result in self.nodes.items():
            node = story.nodes[node_id]
            realized = {item.slot_id: item for item in node.opportunities}
            planned = {
                str(item.get("slot_id") or item.get("id") or ""): item
                for item in node.planned_slots
            }
            for verdict in node_result.verdicts:
                opportunity = realized.get(verdict.slot_id)
                slot = planned.get(verdict.slot_id, {})
                mode = (
                    opportunity.mode
                    if opportunity is not None
                    else str(slot.get("mode") or "exposure")
                )
                context = (
                    opportunity.context
                    if opportunity is not None
                    else str(slot.get("context") or slot.get("context_label") or "")
                )
                phase = (
                    opportunity.phase
                    if opportunity is not None
                    else str(slot.get("phase") or "middle")
                )
                try:
                    observed_mode = PracticeMode(mode)
                except ValueError:
                    observed_mode = PracticeMode.EXPOSURE
                try:
                    observed_phase = StoryPhase(phase)
                except ValueError:
                    observed_phase = StoryPhase.MIDDLE
                structural_failure = bool(node_result.structural_errors)
                records.append(
                    VerifiedOpportunity(
                        slot_id=verdict.slot_id,
                        target_id=verdict.target_id,
                        node_id=node_id,
                        decision=(
                            VerificationDecision.REJECTED
                            if structural_failure
                            else VerificationDecision(verdict.label)
                        ),
                        confidence=verdict.confidence,
                        observed_mode=observed_mode,
                        observed_context=context,
                        observed_phase=observed_phase,
                        reason=(
                            "; ".join(node_result.structural_errors)
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

    def mark_core_graph(self, graph: Any) -> None:


        for node_id, result in self.nodes.items():
            if node_id in graph.nodes:
                graph.nodes[node_id].verification_stale = result.status == "UNKNOWN"


def _slot_id(slot: dict[str, Any]) -> str:
    return str(slot.get("slot_id") or slot.get("id") or "")


def _target_id(slot: dict[str, Any]) -> str:
    return str(slot.get("target_id") or slot.get("lexical_unit_id") or "")


class SemanticVerifier:


    def __init__(
        self,
        provider: LLMProvider,
        *,
        acceptance_threshold: float = 0.92,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        if not 0.5 <= acceptance_threshold <= 1.0:
            raise ValueError("acceptance_threshold must be between 0.5 and 1.0.")
        self.provider = provider
        self.acceptance_threshold = acceptance_threshold
        self.temperature = temperature
        self.max_tokens = max_tokens

    def verify_node(
        self,
        specification: Any,
        node: GeneratedNode,
        *,
        incoming_state: Any = None,
        expected_next_ids: list[str] | None = None,
    ) -> NodeVerification:
        planned_slots = [dict(slot) for slot in node.planned_slots]
        structural_errors = list(node.structural_errors)
        if expected_next_ids is not None:
            structural_errors = structural_node_checks(
                node, expected_next_ids=expected_next_ids
            )
        if not planned_slots:
            status = "COUNTEREXAMPLE" if structural_errors else "VERIFIED"
            return NodeVerification(
                node_id=node.node_id,
                status=status,
                verdicts=[],
                structural_errors=structural_errors,
            )
        messages = verification_messages(
            specification=specification,
            node=node.to_dict(),
            planned_slots=planned_slots,
            incoming_state=incoming_state or {},
        )
        try:
            payload = complete_json(
                self.provider,
                messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                purpose=f"verify node {node.node_id}",
            )
        except LLMError as exc:
            return NodeVerification(
                node_id=node.node_id,
                status="UNKNOWN",
                verdicts=[
                    OpportunityVerdict(
                        slot_id=_slot_id(slot),
                        target_id=_target_id(slot),
                        label="uncertain",
                        confidence=0.0,
                        sense_ok=False,
                        pos_ok=False,
                        pattern_ok=False,
                        grammar_ok=False,
                        context_ok=False,
                        mode_ok=False,
                        evidence_span="",
                        reason=f"Verifier unavailable: {str(exc)[:500]}",
                    )
                    for slot in planned_slots
                ],
                structural_errors=structural_errors,
                notes=["Semantic verifier call failed; no opportunity was accepted."],
            )
        raw_verdicts = payload.get("verdicts")
        if not isinstance(raw_verdicts, list):
            raw_verdicts = []
            payload["node_notes"] = [
                "Verifier response omitted a valid verdicts list; all slots are uncertain."
            ]
        by_slot: dict[str, dict[str, Any]] = {}
        for raw in raw_verdicts:
            if isinstance(raw, dict):
                by_slot[str(raw.get("slot_id", ""))] = raw
        verdicts: list[OpportunityVerdict] = []
        for slot in planned_slots:
            slot_id = _slot_id(slot)
            raw = by_slot.get(slot_id)
            if raw is None:
                verdicts.append(
                    OpportunityVerdict(
                        slot_id=slot_id,
                        target_id=_target_id(slot),
                        label="uncertain",
                        confidence=0.0,
                        sense_ok=False,
                        pos_ok=False,
                        pattern_ok=False,
                        grammar_ok=False,
                        context_ok=False,
                        mode_ok=False,
                        evidence_span="",
                        reason="Verifier omitted this planned slot.",
                    )
                )
                continue
            verdicts.append(self._normalize_verdict(raw, slot))
        labels = {verdict.label for verdict in verdicts}
        if structural_errors or "rejected" in labels:
            status = "COUNTEREXAMPLE"
        elif "uncertain" in labels:
            status = "UNKNOWN"
        else:
            status = "VERIFIED"
        notes = payload.get("node_notes", [])
        return NodeVerification(
            node_id=node.node_id,
            status=status,
            verdicts=verdicts,
            structural_errors=structural_errors,
            notes=[str(note) for note in notes] if isinstance(notes, list) else [],
        )

    def _normalize_verdict(
        self, raw: dict[str, Any], slot: dict[str, Any]
    ) -> OpportunityVerdict:
        requested_label = str(raw.get("label", "uncertain")).lower()
        if requested_label not in VALID_LABELS:
            requested_label = "uncertain"
        confidence_valid = True
        try:
            confidence = float(raw.get("confidence", 0.0))
            if not math.isfinite(confidence):
                confidence_valid = False
                confidence = 0.0
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence_valid = False
            confidence = 0.0
        check_fields = (
            "sense_ok",
            "pos_ok",
            "pattern_ok",
            "grammar_ok",
            "context_ok",
            "mode_ok",
        )
        checks_valid = all(type(raw.get(field)) is bool for field in check_fields)
        checks = {field: raw.get(field) is True for field in check_fields}
        label = requested_label
        if not checks_valid or not confidence_valid:
            label = "uncertain"
        elif requested_label == "accepted" and (
            confidence < self.acceptance_threshold or not all(checks.values())
        ):
            label = "uncertain"
        reason = str(raw.get("reason", ""))[:1000]
        if not checks_valid:
            reason = (reason + " Verifier checks were not JSON booleans.").strip()
        if not confidence_valid:
            reason = (reason + " Verifier confidence was not finite.").strip()
        return OpportunityVerdict(
            slot_id=str(raw.get("slot_id") or _slot_id(slot)),
            target_id=str(raw.get("target_id") or _target_id(slot)),
            label=label,
            confidence=confidence,
            evidence_span=str(raw.get("evidence_span", ""))[:1000],
            reason=reason,
            **checks,
        )

    def verify_story(
        self,
        specification: Any,
        story: GeneratedStory,
        *,
        node_ids: Iterable[str] | None = None,
    ) -> StoryVerification:
        selected = list(node_ids) if node_ids is not None else list(story.nodes)
        results: dict[str, NodeVerification] = {}
        errors: list[str] = []
        for node_id in selected:
            node = story.nodes.get(node_id)
            if node is None:
                errors.append(f"Unknown node requested for verification: {node_id}")
                continue
            result = self.verify_node(
                specification,
                node,
                expected_next_ids=story.edges.get(node_id, []),
            )
            results[node_id] = result
            story.verifications[node_id] = result
        all_results = {
            key: value
            for key, value in story.verifications.items()
            if isinstance(value, NodeVerification)
        }
        accepted: list[dict[str, Any]] = []
        rejected_count = 0
        uncertain_count = 0
        for node_id, result in all_results.items():
            for verdict in result.verdicts:
                record = verdict.to_dict()
                record["node_id"] = node_id
                record["depth"] = story.nodes[node_id].depth
                if verdict.label == "accepted" and not result.structural_errors:
                    accepted.append(record)
                rejected_count += int(verdict.label == "rejected")
                uncertain_count += int(verdict.label == "uncertain")
        statuses = {result.status for result in all_results.values()}
        if errors or "UNKNOWN" in statuses or len(all_results) < len(story.nodes):
            status = "UNKNOWN"
        elif "COUNTEREXAMPLE" in statuses:
            status = "COUNTEREXAMPLE"
        else:
            status = "VERIFIED"
        return StoryVerification(
            status=status,
            nodes=results,
            accepted_records=accepted,
            rejected_count=rejected_count,
            uncertain_count=uncertain_count,
            errors=errors,
        )


__all__ = [
    "NodeVerification",
    "OpportunityVerdict",
    "SemanticVerifier",
    "StoryVerification",
]

