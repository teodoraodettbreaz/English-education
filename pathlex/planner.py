from __future__ import annotations

import copy
import itertools
from dataclasses import dataclass
from typing import Any, Iterable

from .graph import GraphError, GraphLimitError, build_balanced_tree, enumerate_paths
from .models import (
    OpportunitySlot,
    PlanCertificate,
    PracticeMode,
    StoryGraph,
    StoryPhase,
    StorySpec,
    StoryStatus,
    TargetConstraint,
)


@dataclass(slots=True)
class PlanResult:
    graph: StoryGraph | None
    certificate: PlanCertificate


def _gap_ok(depths: tuple[int, ...], minimum: int, maximum: int | None) -> bool:
    for earlier, later in zip(depths, depths[1:]):
        intervening = later - earlier - 1
        if intervening < minimum:
            return False
        if maximum is not None and intervening > maximum:
            return False
    return True


def _phase_set(graph: StoryGraph, depth: int) -> set[StoryPhase]:
    return {node.phase for node in graph.nodes.values() if node.depth == depth}


def _shared_nodes(paths: list[list[str]]) -> set[str]:
    if not paths:
        return set()
    shared = set(paths[0])
    for path in paths[1:]:
        shared.intersection_update(path)
    return shared


def _candidate_depths(graph: StoryGraph, paths: list[list[str]]) -> list[int]:


    result: list[int] = []
    all_depths = sorted({node.depth for node in graph.nodes.values() if node.depth > 0})
    for depth in all_depths:
        if all(sum(graph.nodes[node_id].depth == depth for node_id in path) == 1 for path in paths):
            result.append(depth)
    return result


def _combination_score(depths: tuple[int, ...], final_depth: int) -> tuple[float, tuple[int, ...]]:


    if len(depths) == 1:
        return (abs(depths[0] - final_depth / 2), depths)
    gaps = [right - left for left, right in zip(depths, depths[1:])]
    target = (depths[-1] - depths[0]) / max(1, len(gaps))
    unevenness = sum((gap - target) ** 2 for gap in gaps)
    edge_penalty = abs(depths[0] - 1) * 0.05 + abs(final_depth - depths[-1]) * 0.05
    return (unevenness + edge_penalty, depths)


def choose_depths(
    target: TargetConstraint,
    graph: StoryGraph,
    paths: list[list[str]],
    common_prefix_max_ratio: float,
) -> tuple[list[int] | None, dict[str, Any]]:
    candidates = _candidate_depths(graph, paths)
    shared = _shared_nodes(paths)
    final_depth = max(node.depth for node in graph.nodes.values())
    diagnostics: dict[str, Any] = {
        "target_id": target.id,
        "candidate_depths": candidates,
        "required_occurrences": target.min_occurrences,
        "min_gap": target.min_gap,
        "max_gap": target.max_gap,
        "required_phases": [str(item) for item in target.required_phases],
        "common_prefix_max_ratio": common_prefix_max_ratio,
    }
    if len(candidates) < target.min_occurrences:
        diagnostics["failure"] = "INSUFFICIENT_DISTINCT_DEPTHS"
        return None, diagnostics

    feasible: list[tuple[int, ...]] = []
    for depths in itertools.combinations(candidates, target.min_occurrences):
        if not _gap_ok(depths, target.min_gap, target.max_gap):
            continue
        phases = set()
        for depth in depths:
            phases.update(_phase_set(graph, depth))
        if not set(target.required_phases).issubset(phases):
            continue
        shared_occurrences = 0
        for depth in depths:
            nodes_at_depth = [node.id for node in graph.nodes.values() if node.depth == depth]
            if nodes_at_depth and all(node_id in shared for node_id in nodes_at_depth):
                shared_occurrences += 1
        if shared_occurrences / len(depths) > common_prefix_max_ratio:
            continue
        feasible.append(depths)

    if not feasible:
        diagnostics["failure"] = "NO_DEPTH_COMBINATION_SATISFIES_CONSTRAINTS"
        return None, diagnostics
    selected = min(feasible, key=lambda item: _combination_score(item, final_depth))
    diagnostics["selected"] = list(selected)
    diagnostics["candidate_solution_count"] = len(feasible)
    return list(selected), diagnostics


def _mode_schedule(target: TargetConstraint) -> list[PracticeMode]:
    schedule: list[PracticeMode] = []


    for mode in (PracticeMode.RETRIEVAL, PracticeMode.JUDGMENT, PracticeMode.EXPOSURE):
        schedule.extend([mode] * int(target.mode_requirements.get(mode, 0)))
    while len(schedule) < target.min_occurrences:
        schedule.append(PracticeMode.EXPOSURE)
    return schedule[: target.min_occurrences]


def _context_schedule(target: TargetConstraint) -> list[str]:
    contexts = list(dict.fromkeys(target.context_labels))
    if not contexts:
        contexts = ["general"]
    return [contexts[index % len(contexts)] for index in range(target.min_occurrences)]


def _requirements_snapshot(spec: StorySpec) -> dict[str, Any]:
    return {
        "depth": spec.depth,
        "branch_factor": spec.branch_factor,
        "max_paths": spec.max_paths,
        "max_nodes": spec.max_nodes,
        "common_prefix_max_ratio": spec.common_prefix_max_ratio,
        "targets": {
            target.id: {
                "lemma": target.lemma,
                "min_occurrences": target.min_occurrences,
                "min_gap": target.min_gap,
                "max_gap": target.max_gap,
                "min_contexts": target.min_contexts,
                "context_labels": target.context_labels,
                "required_phases": [str(item) for item in target.required_phases],
                "mode_requirements": {
                    str(mode): count for mode, count in target.mode_requirements.items()
                },
            }
            for target in spec.targets
        },
    }


def _infeasible(
    reason_codes: Iterable[str],
    explanation: str,
    spec: StorySpec,
    *,
    graph: StoryGraph | None = None,
    witness: dict[str, Any] | None = None,
) -> PlanResult:
    certificate = PlanCertificate(
        status=StoryStatus.PLAN_INFEASIBLE,
        reason_codes=list(dict.fromkeys(reason_codes)),
        explanation=explanation,
        requirements=_requirements_snapshot(spec),
        witness=witness or {},
    )
    if graph is not None:
        graph.status = StoryStatus.PLAN_INFEASIBLE
        graph.plan_certificate = certificate
    return PlanResult(graph=graph, certificate=certificate)


def plan_story(spec: StorySpec, graph: StoryGraph | None = None) -> PlanResult:


    spec_errors = spec.validate()
    if spec_errors:
        return _infeasible(
            ["INVALID_STRUCTURED_REQUIREMENT"],
            "The structured teacher requirements are internally inconsistent.",
            spec,
            witness={"validation_errors": spec_errors},
        )
    try:
        source_graph = graph or build_balanced_tree(spec)
        paths = enumerate_paths(
            source_graph,
            max_paths=spec.max_paths,
            max_depth=spec.depth + 4,
        )
    except (GraphError, GraphLimitError) as exc:
        return _infeasible(
            ["FINITE_GRAPH_BOUNDARY_VIOLATION"],
            "The requested finite graph cannot be exhaustively planned within its bounds.",
            spec,
            graph=graph,
            witness={"error": str(exc)},
        )

    staged = copy.deepcopy(source_graph)
    for node in staged.nodes.values():
        node.slots.clear()
        node.verification_stale = True

    selected_depths: dict[str, list[int]] = {}
    diagnostic_witness: dict[str, Any] = {"targets": {}}
    selections: dict[str, tuple[list[int], list[PracticeMode], list[str]]] = {}
    for target in spec.targets:
        depths, diagnostics = choose_depths(
            target,
            staged,
            paths,
            spec.common_prefix_max_ratio,
        )
        diagnostic_witness["targets"][target.id] = diagnostics
        if depths is None:
            return _infeasible(
                [str(diagnostics.get("failure", "UNSAT"))],
                f"No finite slot assignment satisfies target {target.id!r}.",
                spec,
                graph=source_graph,
                witness=diagnostic_witness,
            )
        selected_depths[target.id] = depths
        selections[target.id] = (depths, _mode_schedule(target), _context_schedule(target))

    for target in spec.targets:
        depths, modes, contexts = selections[target.id]
        for occurrence_index, depth in enumerate(depths):
            nodes_at_depth = sorted(
                (node for node in staged.nodes.values() if node.depth == depth),
                key=lambda node: node.id,
            )
            for node in nodes_at_depth:
                node.slots.append(
                    OpportunitySlot(
                        id=f"slot:{target.id}:{occurrence_index + 1}:{node.id}",
                        target_id=target.id,
                        node_id=node.id,
                        occurrence_index=occurrence_index + 1,
                        mode=modes[occurrence_index],
                        context_label=contexts[occurrence_index],
                        phase=node.phase,
                        required_surface=target.lemma,
                    )
                )



    path_counts: dict[str, dict[str, int]] = {}
    for path_index, path in enumerate(paths):
        counts = {target.id: 0 for target in spec.targets}
        for node_id in path:
            for slot in staged.nodes[node_id].slots:
                counts[slot.target_id] += 1
        path_counts[str(path_index)] = counts
        for target in spec.targets:
            if counts[target.id] != target.min_occurrences:
                return _infeasible(
                    ["INTERNAL_WITNESS_MISMATCH"],
                    "The proposed assignment did not cover every terminal path.",
                    spec,
                    graph=source_graph,
                    witness={"path": path, "counts": counts},
                )

    certificate = PlanCertificate(
        status=StoryStatus.PLAN_FEASIBLE,
        reason_codes=[],
        explanation=(
            "An exhaustive finite-depth search found a slot assignment covering every "
            "reachable terminal path. Semantic realisation is not yet verified."
        ),
        selected_depths=selected_depths,
        requirements=_requirements_snapshot(spec),
        witness={
            "terminal_paths_checked": len(paths),
            "path_slot_counts": path_counts,
            "diagnostics": diagnostic_witness,
        },
    )
    staged.status = StoryStatus.PLAN_FEASIBLE
    staged.plan_certificate = certificate
    staged.version += 1
    staged.metadata["slots_planned"] = sum(len(node.slots) for node in staged.nodes.values())
    return PlanResult(graph=staged, certificate=certificate)

