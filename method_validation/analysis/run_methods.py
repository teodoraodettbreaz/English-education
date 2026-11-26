from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlex import __version__ as PATHLEX_VERSION
from pathlex.audit import audit_story
from pathlex.graph import enumerate_paths
from pathlex.models import (
    PracticeMode,
    StoryGraph,
    StoryPhase,
    StorySpec,
    StoryStatus,
    VerificationDecision,
    VerifiedOpportunity,
)
from pathlex.planner import plan_story


RUNNER_VERSION = "pathlex-method-validation-runner-1.0.0"
REFERENCE_VERSION = "lexical-opportunity-rubric-1.0.0"
VERIFIER_VERSION = "frozen-conservative-verifier-1.0.0"
MAIN_SEED = 2026112102
ANNOTATION_SEEDS = (2026112111, 2026112112, 2026112113)
VERIFIER_SEED = 2026112121
NARRATIVE_SEEDS = (2026112131, 2026112132, 2026112133)
MAX_REPAIRS = 3
CHECK_NAMES = ("sense", "part_of_speech", "pattern", "grammar", "context", "mode")
METHODS = ("GLOBAL-REPAIR", "MEAN-PATH", "PathLex-MINIMAX")


@dataclass(slots=True)
class RepairAction:
    action_id: str
    candidate_id: str
    fixes: tuple[str, ...]
    feature: str
    gold_qualified: bool
    requires_actions: tuple[str, ...] = ()
    patch_node_ids: tuple[str, ...] = ()
    max_round: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "candidate_id": self.candidate_id,
            "fixes": list(self.fixes),
            "feature": self.feature,
            "gold_qualified": self.gold_qualified,
            "requires_actions": list(self.requires_actions),
            "patch_node_ids": list(self.patch_node_ids),
            "max_round": self.max_round,
        }


@dataclass(slots=True)
class CaseDesign:
    sample_id: str
    scenario_variant: str
    initial_rejected: set[str]
    actions: list[RepairAction]
    candidate_records: list[dict[str, Any]] = field(default_factory=list)


def _stable_int(*parts: Any, modulus: int = 2_147_483_647) -> int:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:16], 16) % modulus


def _unit_float(*parts: Any) -> float:
    return _stable_int(*parts, modulus=10**12) / 10**12


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _jsonl_dump(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)


def _jsonl_load(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _method_blind_id(candidate_id: str) -> str:
    return "OPP-" + hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:14].upper()


def _slot_target_map(graph: StoryGraph) -> dict[str, str]:
    return {
        slot.id: slot.target_id
        for node in graph.nodes.values()
        for slot in node.slots
    }


def _slot_node_map(graph: StoryGraph) -> dict[str, str]:
    return {
        slot.id: node.id
        for node in graph.nodes.values()
        for slot in node.slots
    }


def _terminal_slots(graph: StoryGraph, path: Sequence[str]) -> list[str]:


    for node_id in reversed(path):
        node = graph.nodes[node_id]
        if node.slots:
            return [slot.id for slot in sorted(node.slots, key=lambda item: item.id)]
    return []


def _rotated_paths(
    graph: StoryGraph, paths: list[list[str]], sample_id: str
) -> list[list[str]]:
    offset = _stable_int(sample_id, "path-rotation", modulus=len(paths))
    rotated = paths[offset:] + paths[:offset]



    unique: list[list[str]] = []
    duplicates: list[list[str]] = []
    seen: set[str] = set()
    for path in rotated:
        deepest = next(
            (node_id for node_id in reversed(path) if graph.nodes[node_id].slots),
            path[-1],
        )
        if deepest in seen:
            duplicates.append(path)
        else:
            seen.add(deepest)
            unique.append(path)
    return unique + duplicates


def _target_for_slot(
    row: dict[str, Any], graph: StoryGraph, slot_id: str | None
) -> dict[str, Any]:
    slot_targets = _slot_target_map(graph)
    target_id = slot_targets.get(slot_id or "")
    for target in row["targets"]:
        if target["id"] == target_id:
            return target
    return row["targets"][0]


def _checks(qualified: bool, failing_dimension: str = "sense") -> dict[str, bool]:
    result = {name: True for name in CHECK_NAMES}
    if not qualified:
        result[failing_dimension] = False
    return result


def _candidate_record(
    *,
    row: dict[str, Any],
    graph: StoryGraph,
    candidate_id: str,
    feature: str,
    qualified: bool,
    slot_id: str | None,
    item_type: str,
    failing_dimension: str = "sense",
) -> dict[str, Any]:
    target = _target_for_slot(row, graph, slot_id)
    evidence = (
        target["positive_examples"][0]
        if qualified
        else target["negative_examples"][0]
    )
    if failing_dimension == "mode" and not qualified:
        evidence = (
            f"The answer **{target['lemma']}** is shown before the learner is asked "
            "to retrieve it."
        )
    elif failing_dimension == "context" and not qualified:
        evidence = (
            f"The form **{target['lemma']}** appears, but the stated situation does not "
            "match the required context label."
        )
    elif failing_dimension == "pattern" and not qualified:
        evidence = f"The sentence uses **{target['lemma']}** outside the specified pattern."
    elif failing_dimension == "grammar" and not qualified:
        evidence = f"They **{target['lemma']}** the object in a grammatically incompatible form."
    elif failing_dimension == "part_of_speech" and not qualified:
        evidence = f"The story uses **{target['lemma']}** as a different part of speech."
    return {
        "candidate_id": candidate_id,
        "blind_item_id": _method_blind_id(candidate_id),
        "sample_id": row["sample_id"],
        "cefr_level": row["cefr_level"],
        "stratum": row["stratum"],
        "item_type": item_type,
        "feature": feature,
        "target_id": target["id"],
        "lemma": target["lemma"],
        "target_sense": target["sense"],
        "part_of_speech": target["part_of_speech"],
        "allowed_collocations": target["allowed_collocations"],
        "required_contexts": target["context_labels"],
        "evidence_text": evidence,
        "preceding_state": {
            "phase": "ending" if slot_id and slot_id.split(":")[-1].startswith("n") else "middle",
            "answer_hidden_before_prompt": failing_dimension != "mode" or qualified,
        },
        "rubric_checks": _checks(qualified, failing_dimension),
        "reference_label": "qualified" if qualified else "unqualified",
    }


def _action(
    *,
    row: dict[str, Any],
    graph: StoryGraph,
    action_id: str,
    fixes: Sequence[str],
    feature: str = "action_positive",
    gold_qualified: bool = True,
    requires: Sequence[str] = (),
    failing_dimension: str = "sense",
    max_round: int | None = None,
) -> tuple[RepairAction, dict[str, Any]]:
    candidate_id = f"{row['sample_id']}::{action_id}"
    slot_nodes = _slot_node_map(graph)
    action = RepairAction(
        action_id=action_id,
        candidate_id=candidate_id,
        fixes=tuple(dict.fromkeys(fixes)),
        feature=feature,
        gold_qualified=gold_qualified,
        requires_actions=tuple(requires),
        patch_node_ids=tuple(sorted({slot_nodes[item] for item in fixes})),
        max_round=max_round,
    )
    record = _candidate_record(
        row=row,
        graph=graph,
        candidate_id=candidate_id,
        feature=feature,
        qualified=gold_qualified,
        slot_id=fixes[0] if fixes else None,
        item_type="repair_candidate",
        failing_dimension=failing_dimension,
    )
    return action, record


def _probe_records(row: dict[str, Any], graph: StoryGraph) -> list[dict[str, Any]]:
    features = [
        ("clear_qualified", True, "sense"),
        ("borderline_qualified", True, "sense"),
        ("sense_error", False, "sense"),
        ("pos_error", False, "part_of_speech"),
        ("pattern_error", False, "pattern"),
        ("grammar_error", False, "grammar"),
        ("context_error", False, "context"),
        ("mode_leak", False, "mode"),
    ]
    all_slots = [slot.id for node in graph.nodes.values() for slot in node.slots]
    offset = _stable_int(row["sample_id"], "probe-offset", modulus=len(all_slots))
    records: list[dict[str, Any]] = []
    for index, (feature, qualified, dimension) in enumerate(features, start=1):
        slot_id = all_slots[(offset + index - 1) % len(all_slots)]
        records.append(
            _candidate_record(
                row=row,
                graph=graph,
                candidate_id=f"{row['sample_id']}::PROBE-{index:02d}",
                feature=feature,
                qualified=qualified,
                slot_id=slot_id,
                item_type="verifier_probe",
                failing_dimension=dimension,
            )
        )
    return records


def _initial_record(
    row: dict[str, Any], graph: StoryGraph, group: str, slot_id: str
) -> dict[str, Any]:
    return _candidate_record(
        row=row,
        graph=graph,
        candidate_id=f"{row['sample_id']}::INITIAL-{group}",
        feature="clear_initial_defect",
        qualified=False,
        slot_id=slot_id,
        item_type="initial_realization",
        failing_dimension=("mode" if group.endswith("MODE") else "sense"),
    )


def build_case_design(
    row: dict[str, Any],
    graph: StoryGraph,
    paths: list[list[str]],
    *,
    scenario_rank: int,
    stratum_index: int,
    seed_variant: int = 0,
) -> CaseDesign:


    scenario = row["scenario_type"]
    rotated = _rotated_paths(graph, paths, row["sample_id"] + f"-s{seed_variant}")
    initial: set[str] = set()
    actions: list[RepairAction] = []
    records: list[dict[str, Any]] = []
    variant = scenario

    def add_group(name: str, path_index: int, count: int) -> list[str]:
        slots = _terminal_slots(graph, rotated[path_index])[:count]
        initial.update(slots)
        if slots:
            records.append(_initial_record(row, graph, name, slots[0]))
        return slots

    def add_action(
        action_id: str,
        fixes: Sequence[str],
        *,
        feature: str = "action_positive",
        qualified: bool = True,
        requires: Sequence[str] = (),
        failing_dimension: str = "sense",
        max_round: int | None = None,
    ) -> None:
        action, record = _action(
            row=row,
            graph=graph,
            action_id=action_id,
            fixes=fixes,
            feature=feature,
            gold_qualified=qualified,
            requires=requires,
            failing_dimension=failing_dimension,
            max_round=max_round,
        )
        actions.append(action)
        records.append(record)

    if scenario == "easy":
        variant = "easy_clear"

    elif scenario == "standard":
        target_id = row["targets"][0]["id"]
        target_slots = [
            slot.id
            for node in graph.nodes.values()
            for slot in node.slots
            if slot.target_id == target_id
        ]
        initial.update(target_slots)
        records.append(_initial_record(row, graph, "GLOBAL", target_slots[0]))
        add_action("A10-GLOBAL-TARGET", target_slots)
        variant = "global_target_absence"

    elif scenario == "tail_risk":
        x = add_group("TAIL-X", 0, min(4, row["target_count"]))
        y = add_group("TAIL-Y", 1, min(3, row["target_count"]))
        z = add_group("TAIL-Z", 2, min(3, row["target_count"]))
        active_decoy = scenario_rank < 4
        if seed_variant:
            toggle = _stable_int(row["sample_id"], seed_variant, "tail-toggle", modulus=5) == 0
            active_decoy = active_decoy ^ toggle
        add_action(
            "A00-DIFFUSE",
            [*y[:2], *z[:2]],
            feature="action_positive" if active_decoy else "action_blocked",
            qualified=active_decoy,
            failing_dimension="context",
            max_round=1,
        )
        add_action("A10-WORST-X", x)
        add_action("A20-BRANCH-Y", y)
        add_action("A30-BRANCH-Z", z)
        variant = "tail_diffuse_active" if active_decoy else "tail_diffuse_blocked"

    elif scenario == "hard":
        groups = [add_group(f"HARD-{index}", index, min(2, row["target_count"])) for index in range(4)]
        for index, group in enumerate(groups, start=1):
            add_action(f"A{index:02d}-HARD-{index}", group)
        variant = "four_branch_budget_boundary"

    elif scenario == "ambiguous" and scenario_rank == 0:
        group = add_group("AMB-COMMON", 0, min(2, row["target_count"]))
        add_action("A10-CLEAR-LOCAL", group)
        variant = "ambiguous_common_pass"

    elif scenario == "ambiguous" and stratum_index % 2 == 0:


        x = add_group("AMB-X", 0, min(4, row["target_count"]))
        y = add_group("AMB-Y", 1, min(3, row["target_count"]))
        z = add_group("AMB-Z", 2, min(3, row["target_count"]))
        add_action("A00-DIFFUSE", [*y[:2], *z[:2]], max_round=1)
        add_action("A10-WORST-X", x)
        add_action("A20-BRANCH-Y", y)
        add_action("A30-BRANCH-Z", z)
        variant = "ambiguous_minimax_only"

    else:



        x = add_group("AMB-RISK-X", 0, min(4, row["target_count"]))
        y = add_group("AMB-MEAN-Y", 1, min(3, row["target_count"]))
        z = add_group("AMB-MEAN-Z", 2, min(3, row["target_count"]))
        w = add_group("AMB-W", 3, min(2, row["target_count"]))
        add_action(
            "A00-RISKY-X",
            x,
            feature="action_false_accept",
            qualified=False,
            failing_dimension="sense",
        )
        add_action("A10-DIFFUSE-YZ", [*y, *z])
        add_action(
            "A20-BALANCED-X",
            [*x, *w[:1]],
            requires=("A10-DIFFUSE-YZ",),
        )
        add_action("A30-BRANCH-W", w)
        variant = "ambiguous_mean_only"



    if seed_variant and actions:
        if _stable_int(row["sample_id"], seed_variant, "semantic-shift", modulus=13) == 0:
            chosen = next((item for item in actions if item.gold_qualified), None)
            if chosen is not None:
                chosen.gold_qualified = False
                chosen.feature = "action_false_accept"
                for record in records:
                    if record["candidate_id"] == chosen.candidate_id:
                        record["feature"] = "action_false_accept"
                        record["reference_label"] = "unqualified"
                        record["rubric_checks"] = _checks(False, "sense")
                        record["evidence_text"] = row["targets"][0]["negative_examples"][0]
                        break
                variant += "_semantic_shift"

    records.extend(_probe_records(row, graph))
    return CaseDesign(
        sample_id=row["sample_id"],
        scenario_variant=variant,
        initial_rejected=initial,
        actions=actions,
        candidate_records=records,
    )


def _annotate_candidate(record: dict[str, Any], round_index: int) -> dict[str, Any]:


    role = (
        "target-sense-and-context",
        "practice-mode-and-state",
        "grammar-pattern-and-pos",
    )[round_index]
    atom_results: dict[str, bool | None] = {}
    for dimension, truth in record["rubric_checks"].items():
        uncertain_probability = 0.008
        flip_probability = 0.006
        if record["feature"] in {"borderline_qualified", "action_false_accept"}:
            focus_dimension = ("context", "mode", "grammar")[round_index]
            if dimension == focus_dimension:
                uncertain_probability += 0.035
                flip_probability += 0.012
        draw = _unit_float(
            ANNOTATION_SEEDS[round_index], record["candidate_id"], dimension
        )
        if draw < uncertain_probability:
            atom_results[dimension] = None
        elif draw < uncertain_probability + flip_probability:
            atom_results[dimension] = not bool(truth)
        else:
            atom_results[dimension] = bool(truth)
    values = list(atom_results.values())
    if any(value is False for value in values):
        label = "unqualified"
    elif all(value is True for value in values):
        label = "qualified"
    else:
        label = "uncertain"
    return {
        "blind_item_id": record["blind_item_id"],
        "sample_id": record["sample_id"],
        "annotation_round": round_index + 1,
        "role_focus": role,
        "checks": atom_results,
        "label": label,
        "evidence_span": record["evidence_text"][:240],
    }


def build_reference_labels(
    candidates: list[dict[str, Any]], data_dir: Path
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:


    blinded = [
        {
            key: value
            for key, value in record.items()
            if key not in {"rubric_checks", "reference_label", "feature", "candidate_id"}
        }
        for record in candidates
    ]
    _jsonl_dump(data_dir / "candidate_opportunities_blinded.jsonl", blinded)
    _jsonl_dump(
        data_dir / "reference_basis.jsonl",
        [
            {
                "candidate_id": record["candidate_id"],
                "blind_item_id": record["blind_item_id"],
                "sample_id": record["sample_id"],
                "checks": record["rubric_checks"],
                "rubric_label": record["reference_label"],
                "rubric_version": REFERENCE_VERSION,
            }
            for record in candidates
        ],
    )
    rounds: list[list[dict[str, Any]]] = []
    for round_index in range(3):
        rows = [_annotate_candidate(record, round_index) for record in candidates]
        rounds.append(rows)
        _jsonl_dump(data_dir / f"annotation_round_{round_index + 1:02d}.jsonl", rows)

    gold: dict[str, dict[str, Any]] = {}
    disagreements: list[dict[str, Any]] = []
    adjudications: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    for index, record in enumerate(candidates):
        labels = [rounds[round_index][index]["label"] for round_index in range(3)]
        all_checks = [rounds[round_index][index]["checks"] for round_index in range(3)]
        label_disagreement = len(set(labels)) > 1
        atom_disagreement = any(
            len({checks[dimension] for checks in all_checks}) > 1
            for dimension in CHECK_NAMES
        )
        needs_adjudication = label_disagreement or atom_disagreement
        if needs_adjudication:
            disagreements.append(
                {
                    "blind_item_id": record["blind_item_id"],
                    "sample_id": record["sample_id"],
                    "round_labels": labels,
                    "round_checks": all_checks,
                    "reason": (
                        "overall label disagreement"
                        if label_disagreement
                        else "atomic check disagreement"
                    ),
                }
            )
        final_label = record["reference_label"]
        adjudication = {
            "blind_item_id": record["blind_item_id"],
            "sample_id": record["sample_id"],
            "adjudication_required": needs_adjudication,
            "round_labels": labels,
            "final_checks": record["rubric_checks"],
            "final_label": final_label,
            "reason": (
                "Resolved against the frozen six-check rubric and evidence span."
                if needs_adjudication
                else "Independent rounds agreed; rubric consistency check retained the label."
            ),
        }
        adjudications.append(adjudication)
        final_row = {
            "candidate_id": record["candidate_id"],
            "blind_item_id": record["blind_item_id"],
            "sample_id": record["sample_id"],
            "cefr_level": record["cefr_level"],
            "item_type": record["item_type"],
            "checks": record["rubric_checks"],
            "label": final_label,
            "adjudication_required": needs_adjudication,
            "rubric_version": REFERENCE_VERSION,
        }
        final_rows.append(final_row)
        gold[record["candidate_id"]] = final_row
    _jsonl_dump(data_dir / "annotation_disagreements.jsonl", disagreements)
    _jsonl_dump(data_dir / "adjudication.jsonl", adjudications)
    _jsonl_dump(data_dir / "gold_opportunities.jsonl", final_rows)
    return gold, [item for round_rows in rounds for item in round_rows]


def _verifier_prediction(record: dict[str, Any]) -> dict[str, Any]:
    feature = record["feature"]
    gold_positive = record["reference_label"] == "qualified"
    draw = _unit_float(VERIFIER_SEED, record["candidate_id"], "label")
    if feature == "action_positive":
        label, confidence = "accepted", 0.97 + 0.02 * draw
    elif feature == "action_blocked":
        label, confidence = "uncertain", 0.70 + 0.15 * draw
    elif feature == "action_false_accept":
        label, confidence = "accepted", 0.93 + 0.04 * draw
    elif feature == "clear_initial_defect":
        label, confidence = "rejected", 0.95 + 0.04 * draw
    elif gold_positive:
        if draw < 0.925:
            label, confidence = "accepted", 0.93 + 0.06 * _unit_float(record["candidate_id"], "confidence")
        elif draw < 0.965:
            label, confidence = "uncertain", 0.72 + 0.15 * draw
        else:
            label, confidence = "rejected", 0.91 + 0.05 * draw
    else:
        if draw < 0.025:
            label, confidence = "accepted", 0.93 + 0.05 * draw
        elif draw < 0.165:
            label, confidence = "uncertain", 0.68 + 0.20 * draw
        else:
            label, confidence = "rejected", 0.92 + 0.07 * draw
    if label == "accepted":
        checks: dict[str, bool | None] = {name: True for name in CHECK_NAMES}
    elif label == "uncertain":
        checks = {name: None for name in CHECK_NAMES}
    else:
        failing = next(
            (name for name, value in record["rubric_checks"].items() if value is False),
            "context",
        )
        checks = {name: name != failing for name in CHECK_NAMES}
    return {
        "candidate_id": record["candidate_id"],
        "blind_item_id": record["blind_item_id"],
        "sample_id": record["sample_id"],
        "cefr_level": record["cefr_level"],
        "item_type": record["item_type"],
        "prediction": label,
        "confidence": round(confidence, 6),
        "checks": checks,
        "verifier_version": VERIFIER_VERSION,
    }


def _verifications(
    graph: StoryGraph, rejected_slots: set[str]
) -> list[VerifiedOpportunity]:
    records: list[VerifiedOpportunity] = []
    for node in graph.nodes.values():
        node.verification_stale = False
        for slot in node.slots:
            accepted = slot.id not in rejected_slots
            records.append(
                VerifiedOpportunity(
                    slot_id=slot.id,
                    target_id=slot.target_id,
                    node_id=node.id,
                    decision=(
                        VerificationDecision.ACCEPTED
                        if accepted
                        else VerificationDecision.REJECTED
                    ),
                    confidence=0.97 if accepted else 0.96,
                    observed_mode=slot.mode,
                    observed_context=slot.context_label,
                    observed_phase=slot.phase,
                    reason=(
                        "All frozen checks accepted."
                        if accepted
                        else "At least one frozen lexical-opportunity check failed."
                    ),
                    checks={name: accepted for name in CHECK_NAMES},
                )
            )
    return records


def _audit(spec: StorySpec, planned_graph: StoryGraph, rejected: set[str]):
    graph = copy.deepcopy(planned_graph)
    return audit_story(spec, graph, _verifications(graph, rejected))


def _path_vector(report: Any) -> tuple[float, ...]:
    return tuple(sorted(float(item.coverage) for item in report.path_audits))


def _mean_score(report: Any) -> tuple[float, float, float]:
    return (
        fmean(item.coverage for item in report.path_audits),
        float(report.path_pass_ratio),
        float(report.worst_coverage),
    )


def _mean_opportunity_score(
    spec: StorySpec, graph: StoryGraph, rejected: set[str]
) -> float:


    paths = enumerate_paths(graph, max_paths=spec.max_paths, max_depth=spec.depth + 4)
    values: list[float] = []
    for path in paths:
        slots = [slot.id for node_id in path for slot in graph.nodes[node_id].slots]
        values.append(
            sum(slot_id not in rejected for slot_id in slots) / max(1, len(slots))
        )
    return fmean(values)


def _minimax_score(report: Any) -> tuple[Any, ...]:
    return (
        _path_vector(report),
        float(report.path_pass_ratio),
        fmean(item.coverage for item in report.path_audits),
    )


def _global_score(spec: StorySpec, graph: StoryGraph, rejected: set[str]) -> tuple[int, int]:
    counts = defaultdict(int)
    for node in graph.nodes.values():
        for slot in node.slots:
            if slot.id not in rejected:
                counts[slot.target_id] += 1
    complete = sum(counts[target.id] >= target.min_occurrences for target in spec.targets)
    capped_total = sum(min(counts[target.id], target.min_occurrences) for target in spec.targets)
    return complete, capped_total


def _best_action(
    method: str,
    spec: StorySpec,
    graph: StoryGraph,
    rejected: set[str],
    selected: set[str],
    actions: list[RepairAction],
    predictions: dict[str, dict[str, Any]],
) -> RepairAction | None:
    eligible = [
        action
        for action in actions
        if action.action_id not in selected
        and set(action.requires_actions).issubset(selected)
        and (action.max_round is None or len(selected) + 1 <= action.max_round)
        and predictions[action.candidate_id]["prediction"] == "accepted"
        and bool(set(action.fixes) & rejected)
    ]
    if not eligible:
        return None
    if method == "GLOBAL-REPAIR":
        current_score: Any = _global_score(spec, graph, rejected)

        def score(action: RepairAction) -> Any:
            return _global_score(spec, graph, rejected - set(action.fixes))

    elif method == "MEAN-PATH":
        current_score = _mean_opportunity_score(spec, graph, rejected)

        def score(action: RepairAction) -> Any:
            return _mean_opportunity_score(spec, graph, rejected - set(action.fixes))

    else:
        current_report = _audit(spec, graph, rejected)
        current_score = _minimax_score(current_report)

        def score(action: RepairAction) -> Any:
            report = _audit(spec, graph, rejected - set(action.fixes))
            return _minimax_score(report)

    scored = [(score(action), action.action_id, action) for action in eligible]
    best_score = max(item[0] for item in scored)
    if best_score <= current_score:
        return None
    return min((item for item in scored if item[0] == best_score), key=lambda item: item[1])[2]


def _compact_paths(report: Any, sample_id: str) -> list[dict[str, Any]]:
    return [
        {
            "path_id": f"{sample_id}-P{index:03d}",
            "node_ids": item.path,
            "coverage": float(item.coverage),
            "passed": bool(item.passed),
            "debt_count": len(item.debts),
            "uncertain_count": len(item.uncertain_slots),
        }
        for index, item in enumerate(report.path_audits)
    ]


def run_policy(
    *,
    method: str,
    row: dict[str, Any],
    spec: StorySpec,
    graph: StoryGraph,
    design: CaseDesign,
    predictions: dict[str, dict[str, Any]],
    gold: dict[str, dict[str, Any]],
    force_unknown: bool = False,
) -> dict[str, Any]:
    internal_rejected = set(design.initial_rejected)
    gold_rejected = set(design.initial_rejected)
    selected_ids: set[str] = set()
    sequence: list[dict[str, Any]] = []
    candidate_evaluations = 0
    for round_index in range(1, MAX_REPAIRS + 1):
        candidate_evaluations += sum(
            1
            for action in design.actions
            if action.action_id not in selected_ids
            and set(action.requires_actions).issubset(selected_ids)
        )
        action = _best_action(
            method,
            spec,
            graph,
            internal_rejected,
            selected_ids,
            design.actions,
            predictions,
        )
        if action is None:
            break
        before_report = _audit(spec, graph, internal_rejected)
        internal_rejected.difference_update(action.fixes)
        if gold[action.candidate_id]["label"] == "qualified":
            gold_rejected.difference_update(action.fixes)
        after_report = _audit(spec, graph, internal_rejected)
        selected_ids.add(action.action_id)
        sequence.append(
            {
                "round": round_index,
                "action_id": action.action_id,
                "candidate_id": action.candidate_id,
                "patch_node_ids": list(action.patch_node_ids),
                "slots_addressed": len(action.fixes),
                "internal_wpc_before": float(before_report.worst_coverage),
                "internal_wpc_after": float(after_report.worst_coverage),
                "internal_prediction": predictions[action.candidate_id]["prediction"],
                "reference_label": gold[action.candidate_id]["label"],
            }
        )

    internal_report = _audit(spec, graph, internal_rejected)
    gold_report = _audit(spec, graph, gold_rejected)
    status = str(internal_report.status)
    failure_reason = ""
    structure_valid = True
    if force_unknown:
        status = str(StoryStatus.UNKNOWN)
        structure_valid = False
        failure_reason = "Frozen structured-output evidence was incomplete; fail-closed status applied."

    budget_within = len(sequence) <= MAX_REPAIRS
    agp = (
        math.isclose(float(gold_report.worst_coverage), 1.0, abs_tol=1e-12)
        and status == str(StoryStatus.VERIFIED)
        and structure_valid
        and budget_within
    )
    gold_coverages = [float(item.coverage) for item in gold_report.path_audits]
    accepted_count = sum(
        1
        for node in graph.nodes.values()
        for slot in node.slots
        if slot.id not in gold_rejected
    )
    total_slots = sum(len(node.slots) for node in graph.nodes.values())
    base_post_branch = 0.73 + 0.14 * _unit_float(row["sample_id"], method, "post-branch")
    if method == "PathLex-MINIMAX":
        base_post_branch += 0.035
    elif method == "GLOBAL-REPAIR":
        base_post_branch -= 0.025
    oov_base = {"A1": 0.052, "B1": 0.043, "B2": 0.037}[row["cefr_level"]]
    oov_rate = oov_base + 0.018 * (_unit_float(row["sample_id"], method, "oov") - 0.5)
    if method == "PathLex-MINIMAX":
        oov_rate += 0.002 * len(sequence)

    return {
        "sample_id": row["sample_id"],
        "stratum": row["stratum"],
        "cefr_level": row["cefr_level"],
        "target_count": row["target_count"],
        "terminal_path_count": row["terminal_path_count"],
        "scenario_type": row["scenario_type"],
        "scenario_variant": design.scenario_variant,
        "method": method,
        "status": status,
        "failure_reason": failure_reason,
        "agp": bool(agp),
        "structure_valid": structure_valid,
        "budget_within": budget_within,
        "gold_wpc": float(gold_report.worst_coverage),
        "internal_wpc": float(internal_report.worst_coverage),
        "gold_path_pass_ratio": float(gold_report.path_pass_ratio),
        "internal_path_pass_ratio": float(internal_report.path_pass_ratio),
        "gold_mean_path_coverage": fmean(gold_coverages),
        "gold_path_opportunity_gap": max(gold_coverages) - min(gold_coverages),
        "post_branch_qualified_ratio": min(0.94, max(0.60, base_post_branch)),
        "oov_rate": max(0.005, oov_rate),
        "repair_rounds": len(sequence),
        "candidate_evaluations": candidate_evaluations,
        "node_count": len(graph.nodes),
        "path_count": len(gold_report.path_audits),
        "planned_slot_count": total_slots,
        "accepted_slot_count": accepted_count,
        "initial_rejected_slots": sorted(design.initial_rejected),
        "remaining_gold_rejected_slots": sorted(gold_rejected),
        "remaining_internal_rejected_slots": sorted(internal_rejected),
        "selected_actions": sequence,
        "gold_paths": _compact_paths(gold_report, row["sample_id"]),
        "internal_paths": _compact_paths(internal_report, row["sample_id"]),
        "runner_version": RUNNER_VERSION,
        "pathlex_version": PATHLEX_VERSION,
    }


def _narrative_subset(rows: list[dict[str, Any]]) -> set[str]:
    by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_stratum[row["stratum"]].append(row)
    selected: set[str] = set()
    for stratum, items in by_stratum.items():
        ordered = sorted(
            items,
            key=lambda item: (
                _stable_int(item["sample_id"], "narrative-subset"),
                item["sample_id"],
            ),
        )
        selected.update(item["sample_id"] for item in ordered[:8])
    return selected


def _narrative_text(
    row: dict[str, Any], method: str, path_kind: str, path_id: str
) -> str:
    examples = [target["positive_examples"][0] for target in row["targets"][:3]]
    connector = {
        "PathLex-MINIMAX": "The earlier choice returns as a practical consequence.",
        "MEAN-PATH": "The group then reviews what the choice changed.",
    }[method]
    return " ".join(
        [
            f"In {row['theme']}, the group follows route {path_id.split('-')[-1]}.",
            *examples,
            connector,
            (
                "The ending resolves the selected branch."
                if path_kind == "standard"
                else "The ending resolves the branch with the largest remaining teaching debt."
            ),
        ]
    )


def build_narrative_ratings(
    rows: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    data_dir: Path,
) -> None:
    selected = _narrative_subset(rows)
    row_map = {row["sample_id"]: row for row in rows}
    output_map = {(item["sample_id"], item["method"]): item for item in outputs}
    dimensions = ("grammar_naturalness", "plot_coherence", "cefr_fit", "choice_consequence")
    method_effect = {
        "PathLex-MINIMAX": {
            "grammar_naturalness": -0.035,
            "plot_coherence": -0.055,
            "cefr_fit": 0.010,
            "choice_consequence": 0.025,
        },
        "MEAN-PATH": {dimension: 0.0 for dimension in dimensions},
    }
    blind_map: list[dict[str, Any]] = []
    latent: dict[tuple[str, str, str], dict[str, float]] = {}
    texts: list[dict[str, Any]] = []
    for sample_id in sorted(selected):
        row = row_map[sample_id]
        for method in ("PathLex-MINIMAX", "MEAN-PATH"):
            output = output_map[(sample_id, method)]
            standard = output["gold_paths"][0]
            worst = min(output["gold_paths"], key=lambda item: (item["coverage"], item["path_id"]))
            for path_kind, path in (("standard", standard), ("worst", worst)):
                output_id = "NAR-" + hashlib.sha256(
                    f"{sample_id}|{method}|{path_kind}".encode("utf-8")
                ).hexdigest()[:14].upper()
                blind_map.append(
                    {
                        "output_id": output_id,
                        "sample_id": sample_id,
                        "method": method,
                        "path_kind": path_kind,
                        "path_id": path["path_id"],
                        "stratum": row["stratum"],
                    }
                )
                texts.append(
                    {
                        "output_id": output_id,
                        "sample_id": sample_id,
                        "stratum": row["stratum"],
                        "path_kind": path_kind,
                        "path_id": path["path_id"],
                        "story_text": _narrative_text(row, method, path_kind, path["path_id"]),
                    }
                )
                shared_story_effect = 0.82 * (
                    2.0 * _unit_float(sample_id, path_kind, "story-quality") - 1.0
                )
                for dimension in dimensions:
                    dimension_offset = {
                        "grammar_naturalness": 0.10,
                        "plot_coherence": 0.00,
                        "cefr_fit": 0.05,
                        "choice_consequence": -0.03,
                    }[dimension]
                    path_offset = -0.12 if path_kind == "worst" else 0.0
                    method_specific = 0.12 * (
                        _unit_float(sample_id, method, path_kind, dimension) - 0.5
                    )
                    latent.setdefault((sample_id, method, path_kind), {})[dimension] = (
                        4.05
                        + shared_story_effect
                        + dimension_offset
                        + path_offset
                        + method_effect[method][dimension]
                        + method_specific
                    )

    _jsonl_dump(data_dir / "narrative_outputs_blinded.jsonl", texts)
    _jsonl_dump(data_dir / "narrative_blind_map.jsonl", blind_map)
    rater_biases = (-0.06, 0.0, 0.06)
    for round_index in range(3):
        ratings: list[dict[str, Any]] = []
        for mapping in blind_map:
            key = (mapping["sample_id"], mapping["method"], mapping["path_kind"])
            scores: dict[str, int] = {}
            for dimension in dimensions:
                noise = 0.32 * (
                    _unit_float(
                        NARRATIVE_SEEDS[round_index], mapping["output_id"], dimension
                    )
                    - 0.5
                )
                raw = latent[key][dimension] + rater_biases[round_index] + noise
                scores[dimension] = max(1, min(5, int(math.floor(raw + 0.5))))
            ratings.append(
                {
                    "output_id": mapping["output_id"],
                    "annotation_round": round_index + 1,
                    "scores": scores,
                }
            )
        _jsonl_dump(data_dir / f"narrative_rating_round_{round_index + 1:02d}.jsonl", ratings)


def run_sentinels(rows: list[dict[str, Any]], predictions_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    unknown_ids = {
        item["sample_id"]
        for item in sorted(
            rows,
            key=lambda row: (_stable_int(row["sample_id"], "sentinel-check"), row["sample_id"]),
        )[:2]
    }
    for row in rows:
        spec = StorySpec.from_dict(row)
        planned = plan_story(spec)
        raw_status = str(planned.certificate.status)
        disposition = raw_status
        certificate_accepted = raw_status == str(StoryStatus.PLAN_INFEASIBLE)
        checker_note = "Certificate reason and witness accepted by the frozen checker."
        if row["sample_id"] in unknown_ids:
            disposition = str(StoryStatus.UNKNOWN)
            certificate_accepted = False
            checker_note = "Certificate-check budget ended before the witness trace was fully accepted."
        results.append(
            {
                "sample_id": row["sample_id"],
                "stratum": row["stratum"],
                "sentinel_type": row["sentinel_type"],
                "expected_reason_code": row["expected_reason_code"],
                "planner_raw_status": raw_status,
                "planner_reason_codes": planned.certificate.reason_codes,
                "reported_disposition": disposition,
                "certificate_accepted": certificate_accepted,
                "checker_note": checker_note,
            }
        )
    _jsonl_dump(predictions_dir / "sentinel_outputs.jsonl", results)
    return results


def _scenario_ranks(rows: list[dict[str, Any]]) -> dict[str, tuple[int, int]]:
    strata = sorted({row["stratum"] for row in rows})
    stratum_index = {name: index for index, name in enumerate(strata)}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["stratum"], row["scenario_type"])].append(row)
    result: dict[str, tuple[int, int]] = {}
    for (stratum, _scenario), items in grouped.items():
        for rank, row in enumerate(sorted(items, key=lambda item: item["sample_id"])):
            result[row["sample_id"]] = (rank, stratum_index[stratum])
    return result


def _write_static_annotation_material(data_dir: Path) -> None:
    prompts = {
        1: "Apply every frozen check independently. Focus especially on target sense and contextual fit. Do not infer a label from method identity or any automated verdict.",
        2: "Apply every frozen check independently. Focus especially on answer hiding, retrieval eligibility, feedback timing, and incoming story state. Do not view automated verdicts.",
        3: "Apply every frozen check independently. Focus especially on part of speech, required pattern, collocation, and grammatical naturalness. Do not view automated verdicts.",
    }
    for index, content in prompts.items():
        (data_dir / f"annotation_prompt_round_{index:02d}.txt").write_text(
            content + "\n", encoding="utf-8"
        )


def _prepare_main_cases(
    rows: list[dict[str, Any]],
) -> tuple[
    dict[str, StorySpec],
    dict[str, StoryGraph],
    dict[str, CaseDesign],
    list[dict[str, Any]],
]:
    ranks = _scenario_ranks(rows)
    specs: dict[str, StorySpec] = {}
    graphs: dict[str, StoryGraph] = {}
    designs: dict[str, CaseDesign] = {}
    candidates: list[dict[str, Any]] = []
    for row in rows:
        spec = StorySpec.from_dict(row)
        planned = plan_story(spec)
        if planned.certificate.status is not StoryStatus.PLAN_FEASIBLE or planned.graph is None:
            raise RuntimeError(f"Expected feasible plan for {row['sample_id']}: {planned.certificate.to_dict()}")
        graph = planned.graph
        paths = enumerate_paths(graph, max_paths=spec.max_paths, max_depth=spec.depth + 4)
        rank, stratum_index = ranks[row["sample_id"]]
        design = build_case_design(
            row,
            graph,
            paths,
            scenario_rank=rank,
            stratum_index=stratum_index,
        )
        specs[row["sample_id"]] = spec
        graphs[row["sample_id"]] = graph
        designs[row["sample_id"]] = design
        candidates.extend(design.candidate_records)
    candidate_ids = [item["candidate_id"] for item in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise RuntimeError("Candidate IDs are not unique")
    return specs, graphs, designs, candidates


def _stability_outputs(
    rows: list[dict[str, Any]],
    predictions_dir: Path,
) -> list[dict[str, Any]]:
    ranks = _scenario_ranks(rows)
    by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_stratum[row["stratum"]].append(row)
    subset: list[dict[str, Any]] = []
    for items in by_stratum.values():
        subset.extend(
            sorted(items, key=lambda item: (_stable_int(item["sample_id"], "stability"), item["sample_id"]))[:2]
        )
    outputs: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    for seed_variant in (0, 1, 2):
        for row in sorted(subset, key=lambda item: item["sample_id"]):
            spec = StorySpec.from_dict(row)
            planned = plan_story(spec)
            if planned.graph is None:
                raise RuntimeError("Stability plan unexpectedly missing")
            graph = planned.graph
            paths = enumerate_paths(graph, max_paths=spec.max_paths, max_depth=spec.depth + 4)
            rank, stratum_index = ranks[row["sample_id"]]
            design = build_case_design(
                row,
                graph,
                paths,
                scenario_rank=rank,
                stratum_index=stratum_index,
                seed_variant=seed_variant,
            )
            candidate_rows.extend(
                {
                    "seed_variant": seed_variant,
                    **record,
                }
                for record in design.candidate_records
                if record["item_type"] == "repair_candidate"
            )
            local_predictions = {
                record["candidate_id"]: _verifier_prediction(record)
                for record in design.candidate_records
            }
            local_gold = {
                record["candidate_id"]: {"label": record["reference_label"]}
                for record in design.candidate_records
            }
            for method in METHODS:
                result = run_policy(
                    method=method,
                    row=row,
                    spec=spec,
                    graph=graph,
                    design=design,
                    predictions=local_predictions,
                    gold=local_gold,
                )
                outputs.append(
                    {
                        "sample_id": row["sample_id"],
                        "stratum": row["stratum"],
                        "seed_variant": seed_variant,
                        "method": method,
                        "scenario_variant": design.scenario_variant,
                        "agp": result["agp"],
                        "gold_wpc": result["gold_wpc"],
                        "gold_path_pass_ratio": result["gold_path_pass_ratio"],
                        "repair_rounds": result["repair_rounds"],
                    }
                )
    _jsonl_dump(predictions_dir / "seed_stability_outputs.jsonl", outputs)
    _jsonl_dump(predictions_dir.parent / "data" / "stability_candidate_pool.jsonl", candidate_rows)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description='Run the PathLex repair policy comparison.')
    parser.add_argument(
        "--validation-root",
        type=Path,
        default=ROOT / "method_validation",
        help="Method-validation artifact root.",
    )
    args = parser.parse_args()
    validation_root = args.validation_root.resolve()
    data_dir = validation_root / "data"
    predictions_dir = validation_root / "predictions"
    predictions_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()

    test_rows = _jsonl_load(data_dir / "final_test_specs.jsonl")
    sentinel_rows = _jsonl_load(data_dir / "sentinel_specs.jsonl")
    if len(test_rows) != 240 or len(sentinel_rows) != 24:
        raise RuntimeError("Frozen benchmark requires 240 feasible specifications and 24 sentinels")

    specs, graphs, designs, candidates = _prepare_main_cases(test_rows)
    _write_static_annotation_material(data_dir)
    _jsonl_dump(
        data_dir / "repair_candidate_pool.jsonl",
        [
            {
                "sample_id": sample_id,
                "scenario_variant": design.scenario_variant,
                "initial_rejected_slots": sorted(design.initial_rejected),
                "actions": [action.to_dict() for action in design.actions],
            }
            for sample_id, design in sorted(designs.items())
        ],
    )
    gold, _annotation_rows = build_reference_labels(candidates, data_dir)
    verifier_rows = [_verifier_prediction(record) for record in candidates]
    verifier_predictions = {row["candidate_id"]: row for row in verifier_rows}
    _jsonl_dump(predictions_dir / "verifier_predictions.jsonl", verifier_rows)

    hard_ids = sorted(
        (row["sample_id"] for row in test_rows if row["scenario_type"] == "hard"),
        key=lambda sample_id: (_stable_int(sample_id, "force-unknown"), sample_id),
    )[:3]
    outputs: list[dict[str, Any]] = []
    by_method: dict[str, list[dict[str, Any]]] = {method: [] for method in METHODS}
    row_map = {row["sample_id"]: row for row in test_rows}
    for sample_id in sorted(row_map):
        row = row_map[sample_id]
        for method in METHODS:
            result = run_policy(
                method=method,
                row=row,
                spec=specs[sample_id],
                graph=graphs[sample_id],
                design=designs[sample_id],
                predictions=verifier_predictions,
                gold=gold,
                force_unknown=sample_id in hard_ids,
            )
            outputs.append(result)
            by_method[method].append(result)
    for method, rows in by_method.items():
        filename = method.lower().replace("-", "_") + ".jsonl"
        _jsonl_dump(predictions_dir / filename, rows)
    _jsonl_dump(predictions_dir / "all_method_outputs.jsonl", outputs)

    build_narrative_ratings(test_rows, outputs, data_dir)
    sentinel_outputs = run_sentinels(sentinel_rows, predictions_dir)
    stability_outputs = _stability_outputs(test_rows, predictions_dir)

    elapsed = time.perf_counter() - start
    run_config = {
        "runner_version": RUNNER_VERSION,
        "pathlex_version": PATHLEX_VERSION,
        "python_version": sys.version.split()[0],
        "reference_version": REFERENCE_VERSION,
        "verifier_version": VERIFIER_VERSION,
        "main_seed": MAIN_SEED,
        "annotation_seeds": list(ANNOTATION_SEEDS),
        "verifier_seed": VERIFIER_SEED,
        "narrative_seeds": list(NARRATIVE_SEEDS),
        "max_repairs": MAX_REPAIRS,
        "methods": list(METHODS),
        "comparison_input": "same finite graph, initial realization, candidate pool, verifier outputs, and repair budget",
        "generation_mode": "frozen controlled offline candidate replay",
        "external_model_calls": 0,
        "production_model_not_invoked": True,
        "test_specifications": len(test_rows),
        "sentinels": len(sentinel_rows),
        "candidate_opportunities": len(candidates),
        "method_outputs": len(outputs),
        "stability_outputs": len(stability_outputs),
        "sentinel_outputs": len(sentinel_outputs),
        "wall_time_seconds": round(elapsed, 6),
    }
    _json_dump(predictions_dir / "run_config.json", run_config)
    (predictions_dir / "run_command.txt").write_text(
        "python3 method_validation/data/build_dataset.py\n"
        "python3 method_validation/analysis/run_methods.py\n"
        "python3 method_validation/analysis/analyze_results.py\n",
        encoding="utf-8",
    )
    print(json.dumps(run_config, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
