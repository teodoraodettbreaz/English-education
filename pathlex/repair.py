from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from .generator import GeneratedNode, GeneratedStory
from .llm import LLMError, LLMProvider, complete_json
from .prompts import repair_messages, to_plain
from .verifier import SemanticVerifier


AuditFunction = Callable[[GeneratedStory], Any]


@dataclass(slots=True)
class RepairAttempt:
    round_index: int
    node_id: str | None
    baseline_coverage: float
    candidate_coverage: float | None
    committed: bool
    reason: str
    affected_nodes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RepairOutcome:
    story: GeneratedStory
    audit: Any
    status: str
    attempts: list[RepairAttempt]

    def to_dict(self) -> dict[str, Any]:
        return {
            "story": self.story.to_dict(),
            "audit": to_plain(self.audit),
            "status": self.status,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
        }


def _get(value: Any, *names: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        for name in names:
            if name in value:
                return value[name]
        return default
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    return default


def _coverage(audit: Any) -> float:
    value = _get(
        audit,
        "worst_path_coverage",
        "worst_coverage",
        "wpc",
        default=0.0,
    )
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _status(audit: Any) -> str:
    return str(_get(audit, "status", default="COUNTEREXAMPLE"))


def _worst_path(audit: Any) -> list[str]:
    value = _get(
        audit,
        "counterexample_path",
        "worst_path",
        "path",
        default=[],
    )
    return [str(item) for item in value] if isinstance(value, (list, tuple)) else []


def _debts(audit: Any) -> list[dict[str, Any]]:
    value = _get(audit, "debts", "missing_constraints", "deficits", default=[])
    if not value:
        counterexample = _get(audit, "counterexample", default=None)
        if isinstance(counterexample, dict):
            value = counterexample.get("debts", [])
    if not isinstance(value, list):
        return []
    return [to_plain(item) if not isinstance(item, dict) else dict(item) for item in value]


def descendants(story: GeneratedStory, node_id: str) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    stack = [node_id]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        ordered.append(current)
        stack.extend(reversed(story.edges.get(current, [])))
    return ordered


class TransactionalRepairer:


    def __init__(
        self,
        provider: LLMProvider,
        verifier: SemanticVerifier,
        *,
        max_rounds: int = 3,
        min_improvement: float = 1e-9,
        temperature: float = 0.15,
        max_tokens: int = 4096,
    ) -> None:
        self.provider = provider
        self.verifier = verifier
        self.max_rounds = max(0, max_rounds)
        self.min_improvement = min_improvement
        self.temperature = temperature
        self.max_tokens = max_tokens

    def repair(
        self,
        specification: Any,
        story: GeneratedStory,
        audit_fn: AuditFunction,
        *,
        interface_language: str = "en",
    ) -> RepairOutcome:
        current = story.clone()
        current_audit = audit_fn(current)
        attempts: list[RepairAttempt] = []
        if _status(current_audit) == "VERIFIED":
            return RepairOutcome(current, current_audit, "VERIFIED", attempts)
        for round_index in range(1, self.max_rounds + 1):
            baseline = _coverage(current_audit)
            path = _worst_path(current_audit)
            debts = _debts(current_audit)
            node_id = self._select_node(current, path, debts)
            if node_id is None:
                attempts.append(
                    RepairAttempt(
                        round_index=round_index,
                        node_id=None,
                        baseline_coverage=baseline,
                        candidate_coverage=None,
                        committed=False,
                        reason="No reachable node can carry the outstanding debt.",
                    )
                )
                break
            candidate = current.clone()
            candidate_node = candidate.nodes[node_id]
            candidate_slots = copy.deepcopy(candidate_node.planned_slots)
            self._attach_debt_slots(candidate_slots, debts, round_index, node_id)
            candidate_node.planned_slots = candidate_slots
            messages = repair_messages(
                specification=specification,
                node=candidate_node.to_dict(),
                incoming_state=self._incoming_state(candidate, node_id),
                debts=debts,
                allowed_edges=[
                    {"choice_id": f"{node_id}-c{index + 1}", "next_id": next_id}
                    for index, next_id in enumerate(candidate.edges.get(node_id, []))
                ],
                interface_language=interface_language,
            )
            try:
                payload = complete_json(
                    self.provider,
                    messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    purpose=f"repair node {node_id}",
                )
                revised = GeneratedNode.from_payload(
                    payload,
                    expected_id=node_id,
                    depth=candidate_node.depth,
                    expected_next_ids=candidate.edges.get(node_id, []),
                    planned_slots=candidate_slots,
                )
                revised.version = candidate_node.version + 1
                candidate.nodes[node_id] = revised
            except (LLMError, ValueError, TypeError) as exc:
                attempts.append(
                    RepairAttempt(
                        round_index=round_index,
                        node_id=node_id,
                        baseline_coverage=baseline,
                        candidate_coverage=None,
                        committed=False,
                        reason=f"Repair generation failed; state unchanged: {str(exc)[:500]}",
                    )
                )
                return RepairOutcome(current, current_audit, "UNKNOWN", attempts)

            affected = descendants(candidate, node_id)
            for affected_id in affected:
                candidate.verifications.pop(affected_id, None)
            verification = self.verifier.verify_story(
                specification, candidate, node_ids=affected
            )
            if verification.status != "VERIFIED":
                attempts.append(
                    RepairAttempt(
                        round_index=round_index,
                        node_id=node_id,
                        baseline_coverage=baseline,
                        candidate_coverage=None,
                        committed=False,
                        reason=(
                            "Candidate rolled back because affected nodes were not "
                            f"fully verified ({verification.status})."
                        ),
                        affected_nodes=affected,
                    )
                )
                continue
            candidate_audit = audit_fn(candidate)
            candidate_coverage = _coverage(candidate_audit)
            improves = candidate_coverage > baseline + self.min_improvement
            safe_status = _status(candidate_audit) in {"VERIFIED", "COUNTEREXAMPLE"}
            if improves and safe_status:
                current = candidate
                current_audit = candidate_audit
                attempts.append(
                    RepairAttempt(
                        round_index=round_index,
                        node_id=node_id,
                        baseline_coverage=baseline,
                        candidate_coverage=candidate_coverage,
                        committed=True,
                        reason="Candidate committed after verification and worst-path improvement.",
                        affected_nodes=affected,
                    )
                )
                if _status(current_audit) == "VERIFIED":
                    return RepairOutcome(current, current_audit, "VERIFIED", attempts)
            else:
                attempts.append(
                    RepairAttempt(
                        round_index=round_index,
                        node_id=node_id,
                        baseline_coverage=baseline,
                        candidate_coverage=candidate_coverage,
                        committed=False,
                        reason=(
                            "Candidate rolled back because it did not improve the worst "
                            "path or produced an unknown audit state."
                        ),
                        affected_nodes=affected,
                    )
                )
        final_status = "VERIFIED" if _status(current_audit) == "VERIFIED" else _status(current_audit)
        if final_status not in {"VERIFIED", "COUNTEREXAMPLE", "UNKNOWN"}:
            final_status = "COUNTEREXAMPLE"
        return RepairOutcome(current, current_audit, final_status, attempts)

    @staticmethod
    def _select_node(
        story: GeneratedStory,
        path: list[str],
        debts: list[dict[str, Any]],
    ) -> str | None:
        candidates = [node_id for node_id in path if node_id in story.nodes]
        if not candidates:
            candidates = list(story.nodes)
        rejected_slot_ids = {
            str(slot_id)
            for debt in debts
            for slot_id in (debt.get("rejected_slots") or [])
            if slot_id
        }
        if rejected_slot_ids:
            for node_id in reversed(candidates):
                node_slots = {
                    str(slot.get("slot_id") or slot.get("id") or "")
                    for slot in story.nodes[node_id].planned_slots
                }
                if node_slots & rejected_slot_ids:
                    return node_id
        target_ids = {
            str(debt.get("target_id") or debt.get("lexical_unit_id") or "")
            for debt in debts
        }
        for node_id in reversed(candidates):
            node = story.nodes[node_id]
            if node_id == story.root_id:
                continue
            node_targets = {
                str(slot.get("target_id") or slot.get("lexical_unit_id") or "")
                for slot in node.planned_slots
            }
            if target_ids & node_targets:
                return node_id
        for node_id in reversed(candidates):
            if node_id != story.root_id:
                return node_id
        return None

    @staticmethod
    def _attach_debt_slots(
        slots: list[dict[str, Any]],
        debts: list[dict[str, Any]],
        round_index: int,
        node_id: str,
    ) -> None:
        existing = {
            str(slot.get("slot_id") or slot.get("id") or "") for slot in slots
        }
        for index, debt in enumerate(debts):
            rejected = {
                str(item) for item in (debt.get("rejected_slots") or []) if item
            }




            if rejected & existing:
                continue
            target_id = str(debt.get("target_id") or debt.get("lexical_unit_id") or "")
            if not target_id:
                continue
            slot_id = f"repair-{round_index}-{node_id}-{index + 1}"
            if slot_id in existing:
                continue
            kind = str(debt.get("kind") or "")
            derived_mode = kind.split(":", 1)[1] if kind.startswith("mode:") else ""
            derived_phase = kind.split(":", 1)[1] if kind.startswith("phase:") else ""
            context = str(
                debt.get("context")
                or debt.get("context_label")
                or (
                    f"repair-context-{round_index}-{index + 1}"
                    if kind == "contexts"
                    else "repair-context"
                )
            )
            surface = str(
                debt.get("surface")
                or debt.get("required_surface")
                or debt.get("word")
                or debt.get("lemma")
                or ""
            )
            slots.append(
                {
                    "id": slot_id,
                    "slot_id": slot_id,
                    "target_id": target_id,
                    "node_id": node_id,
                    "occurrence_index": int(
                        debt.get("occurrence_index") or 10_000 + index
                    ),
                    "surface": surface,
                    "required_surface": surface,
                    "mode": str(debt.get("mode") or derived_mode or "exposure"),
                    "context": context,
                    "context_label": context,
                    "phase": str(debt.get("phase") or derived_phase or "middle"),
                    "source": "worst-path-debt",
                }
            )

    @staticmethod
    def _incoming_state(story: GeneratedStory, node_id: str) -> dict[str, Any]:
        parents = [
            source
            for source, targets in story.edges.items()
            if node_id in targets and source in story.nodes
        ]
        return {
            "parent_states": [story.nodes[parent].plot_state for parent in parents],
            "current_version": story.nodes[node_id].version,
        }


__all__ = [
    "RepairAttempt",
    "RepairOutcome",
    "TransactionalRepairer",
    "descendants",
]

