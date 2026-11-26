from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .graph import GraphError, GraphLimitError, enumerate_paths, validate_graph
from .models import (
    AuditReport,
    ConstraintCheck,
    OpportunitySlot,
    PathAudit,
    PracticeMode,
    StoryGraph,
    StoryPhase,
    StorySpec,
    StoryStatus,
    TargetConstraint,
    VerificationDecision,
    VerifiedOpportunity,
)


@dataclass(slots=True)
class LedgerTargetState:
    accepted_slots: list[str] = field(default_factory=list)
    accepted_positions: list[int] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)
    modes: list[str] = field(default_factory=list)
    rejected_slots: list[str] = field(default_factory=list)
    uncertain_slots: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_slots": self.accepted_slots,
            "accepted_positions": self.accepted_positions,
            "contexts": self.contexts,
            "phases": self.phases,
            "modes": self.modes,
            "rejected_slots": self.rejected_slots,
            "uncertain_slots": self.uncertain_slots,
        }


def _verification_map(
    verifications: Iterable[VerifiedOpportunity] | Mapping[str, VerifiedOpportunity],
) -> dict[str, VerifiedOpportunity]:
    if isinstance(verifications, Mapping):
        return dict(verifications)
    return {item.slot_id: item for item in verifications}


def replay_ledger(
    path: list[str],
    graph: StoryGraph,
    verifications: Iterable[VerifiedOpportunity] | Mapping[str, VerifiedOpportunity],
) -> dict[str, LedgerTargetState]:


    by_slot = _verification_map(verifications)
    ledger: dict[str, LedgerTargetState] = defaultdict(LedgerTargetState)
    for position, node_id in enumerate(path):
        node = graph.nodes[node_id]
        for slot in node.slots:
            state = ledger[slot.target_id]
            verification = by_slot.get(slot.id)
            if node.verification_stale or verification is None:
                state.uncertain_slots.append(slot.id)
                continue
            checks_are_clear = all(value is not None for value in verification.checks.values())
            checks_pass = all(value is True for value in verification.checks.values())
            if verification.decision is VerificationDecision.UNCERTAIN or not checks_are_clear:
                state.uncertain_slots.append(slot.id)
            elif verification.decision is VerificationDecision.REJECTED or not checks_pass:
                state.rejected_slots.append(slot.id)
            else:
                state.accepted_slots.append(slot.id)
                state.accepted_positions.append(position)
                state.contexts.append(verification.observed_context or slot.context_label)
                state.phases.append(str(verification.observed_phase or slot.phase))
                state.modes.append(str(verification.observed_mode or slot.mode))
    return dict(ledger)


def ledger_snapshot(
    path: list[str],
    graph: StoryGraph,
    verifications: Iterable[VerifiedOpportunity] | Mapping[str, VerifiedOpportunity],
) -> dict[str, Any]:


    return {
        target_id: state.to_dict()
        for target_id, state in replay_ledger(path, graph, verifications).items()
    }


def _target_check_blueprint(target: TargetConstraint) -> list[tuple[str, str]]:
    checks: list[tuple[str, str]] = [
        ("occurrences", f"at least {target.min_occurrences} accepted opportunities"),
        ("spacing", f"gap in [{target.min_gap}, {target.max_gap}]")
        if target.max_gap is not None
        else ("spacing", f"gap >= {target.min_gap}"),
        ("contexts", f"at least {target.min_contexts} explicit contexts"),
    ]
    checks.extend((f"phase:{phase}", f"contains phase {phase}") for phase in target.required_phases)
    checks.extend(
        (f"mode:{mode}", f"at least {count} {mode} opportunities")
        for mode, count in target.mode_requirements.items()
        if count > 0
    )
    return checks


def _spacing_passes(positions: list[int], target: TargetConstraint) -> bool:
    if len(positions) < target.min_occurrences:
        return False
    relevant = sorted(positions)[: target.min_occurrences]
    for earlier, later in zip(relevant, relevant[1:]):
        gap = later - earlier - 1
        if gap < target.min_gap:
            return False
        if target.max_gap is not None and gap > target.max_gap:
            return False
    return True


def _checks_for_target(
    target: TargetConstraint,
    state: LedgerTargetState,
    target_weight: float,
) -> tuple[list[ConstraintCheck], list[dict[str, Any]]]:
    blueprint = _target_check_blueprint(target)
    per_check_weight = target_weight / max(1, len(blueprint))
    mode_counts = Counter(state.modes)
    phase_values = set(state.phases)
    context_values = {item for item in state.contexts if item}
    values: dict[str, bool] = {
        "occurrences": len(state.accepted_slots) >= target.min_occurrences,
        "spacing": _spacing_passes(state.accepted_positions, target),
        "contexts": len(context_values) >= target.min_contexts,
    }
    for phase in target.required_phases:
        values[f"phase:{phase}"] = str(phase) in phase_values
    for mode, count in target.mode_requirements.items():
        if count > 0:
            values[f"mode:{mode}"] = mode_counts[str(mode)] >= count

    checks: list[ConstraintCheck] = []
    debts: list[dict[str, Any]] = []
    for kind, description in blueprint:
        satisfied = values[kind]
        detail = description
        checks.append(
            ConstraintCheck(
                id=f"{target.id}:{kind}",
                target_id=target.id,
                kind=kind,
                satisfied=satisfied,
                weight=per_check_weight,
                detail=detail,
            )
        )
        if not satisfied:
            debts.append(
                {
                    "target_id": target.id,
                    "lemma": target.lemma,
                    "kind": kind,
                    "requirement": detail,
                    "accepted": len(state.accepted_slots),
                    "rejected_slots": state.rejected_slots,
                    "uncertain_slots": state.uncertain_slots,
                }
            )
    return checks, debts


def _empty_report(status: StoryStatus, reasons: list[str], version: int) -> AuditReport:
    return AuditReport(
        status=status,
        worst_path=[],
        worst_coverage=0.0,
        path_pass_ratio=0.0,
        path_audits=[],
        unknown_reasons=reasons,
        graph_version=version,
    )


def audit_story(
    spec: StorySpec,
    graph: StoryGraph,
    verifications: Iterable[VerifiedOpportunity] | Mapping[str, VerifiedOpportunity],
    *,
    generation_failed: bool = False,
    failure_reason: str = "",
) -> AuditReport:


    if generation_failed:
        report = _empty_report(
            StoryStatus.GENERATION_FAILURE,
            [failure_reason or "story generation did not complete"],
            graph.version,
        )
        graph.status = report.status
        graph.audit_report = report
        return report
    if graph.status is StoryStatus.PLAN_INFEASIBLE:
        report = _empty_report(
            StoryStatus.PLAN_INFEASIBLE,
            ["the structured slot planner produced an UNSAT certificate"],
            graph.version,
        )
        graph.audit_report = report
        return report
    structural_errors = validate_graph(graph, max_nodes=spec.max_nodes)
    if structural_errors:
        report = _empty_report(StoryStatus.UNKNOWN, structural_errors, graph.version)
        graph.status = report.status
        graph.audit_report = report
        return report
    try:
        paths = enumerate_paths(graph, max_paths=spec.max_paths, max_depth=spec.depth + 8)
    except (GraphError, GraphLimitError) as exc:
        report = _empty_report(StoryStatus.UNKNOWN, [str(exc)], graph.version)
        graph.status = report.status
        graph.audit_report = report
        return report

    by_slot = _verification_map(verifications)
    target_weight_total = sum(target.weight for target in spec.targets)
    audits: list[PathAudit] = []
    any_definite_failure = False
    unknown_reasons: list[str] = []

    for path in paths:
        ledger = replay_ledger(path, graph, by_slot)
        checks: list[ConstraintCheck] = []
        debts: list[dict[str, Any]] = []
        uncertain_slots: list[str] = []
        path_definite_failure = False
        for target in spec.targets:
            state = ledger.get(target.id, LedgerTargetState())
            target_weight = target.weight / target_weight_total
            target_checks, target_debts = _checks_for_target(target, state, target_weight)
            checks.extend(target_checks)
            debts.extend(target_debts)
            uncertain_slots.extend(state.uncertain_slots)



            if state.rejected_slots:
                path_definite_failure = True
            elif not state.uncertain_slots and any(not item.satisfied for item in target_checks):
                path_definite_failure = True
        coverage = sum(item.weight for item in checks if item.satisfied)
        passed = all(item.satisfied for item in checks) and not uncertain_slots
        audits.append(
            PathAudit(
                path=path,
                coverage=round(coverage, 10),
                passed=passed,
                checks=checks,
                debts=debts,
                uncertain_slots=sorted(set(uncertain_slots)),
            )
        )
        any_definite_failure = any_definite_failure or path_definite_failure
        if uncertain_slots:
            unknown_reasons.append(
                f"path {' > '.join(path)} has {len(set(uncertain_slots))} unresolved slots"
            )

    worst = min(audits, key=lambda item: (item.coverage, item.path))
    passed_count = sum(item.passed for item in audits)
    if any_definite_failure:
        status = StoryStatus.COUNTEREXAMPLE
    elif unknown_reasons:
        status = StoryStatus.UNKNOWN
    elif passed_count == len(audits):
        status = StoryStatus.VERIFIED
    else:


        status = StoryStatus.COUNTEREXAMPLE

    counterexample = None
    if status is StoryStatus.COUNTEREXAMPLE:
        failing = next((item for item in audits if not item.passed), worst)
        counterexample = {
            "path": failing.path,
            "coverage": failing.coverage,
            "debts": failing.debts,
        }
    report = AuditReport(
        status=status,
        worst_path=worst.path,
        worst_coverage=worst.coverage,
        path_pass_ratio=passed_count / len(audits),
        path_audits=audits,
        counterexample=counterexample,
        unknown_reasons=list(dict.fromkeys(unknown_reasons)),
        graph_version=graph.version,
    )
    graph.status = status
    graph.audit_report = report
    return report

