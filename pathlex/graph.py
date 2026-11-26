from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .models import Choice, StoryGraph, StoryNode, StoryPhase, StorySpec, StoryStatus


class GraphError(ValueError):
    pass


class GraphLimitError(GraphError):
    pass


def phase_for_depth(depth: int, final_depth: int) -> StoryPhase:
    if depth == 0:
        return StoryPhase.OPENING
    if depth >= final_depth:
        return StoryPhase.ENDING
    fraction = depth / max(1, final_depth)
    if fraction <= 0.34:
        return StoryPhase.OPENING
    if fraction < 0.75:
        return StoryPhase.MIDDLE
    return StoryPhase.ENDING


def expected_tree_size(branch_factor: int, depth: int) -> tuple[int, int]:


    paths = branch_factor ** (depth - 1)
    nodes = sum(branch_factor**level for level in range(depth))
    return nodes, paths


def build_balanced_tree(spec: StorySpec) -> StoryGraph:


    errors = spec.validate()
    if errors:
        raise GraphError("; ".join(errors))
    node_count, path_count = expected_tree_size(spec.branch_factor, spec.depth)
    if path_count > spec.max_paths:
        raise GraphLimitError(
            f"requested skeleton has {path_count} terminal paths; max_paths={spec.max_paths}"
        )
    if node_count > spec.max_nodes:
        raise GraphLimitError(
            f"requested skeleton has {node_count} nodes; max_nodes={spec.max_nodes}"
        )

    nodes: dict[str, StoryNode] = {}
    root = StoryNode(id="n0", depth=0, phase=StoryPhase.OPENING)
    nodes[root.id] = root
    current_level = [root]
    next_index = 1
    for level in range(spec.depth - 1):
        children: list[StoryNode] = []
        child_depth = level + 1
        for parent in current_level:
            for branch in range(spec.branch_factor):
                node_id = f"n{next_index}"
                next_index += 1
                child = StoryNode(
                    id=node_id,
                    depth=child_depth,
                    phase=phase_for_depth(child_depth, spec.depth - 1),
                    terminal=(child_depth == spec.depth - 1),
                )
                nodes[node_id] = child
                children.append(child)
                parent.choices.append(
                    Choice(
                        id=f"{parent.id}_choice_{branch + 1}",
                        target_node_id=node_id,
                        label_en=f"Choice {branch + 1}",
                        label_zh=f"选择 {branch + 1}",
                    )
                )
        current_level = children

    graph = StoryGraph(
        id=f"graph-{spec.id}",
        spec_id=spec.id,
        root_id=root.id,
        nodes=nodes,
        status=StoryStatus.DRAFT,
        metadata={
            "finite": True,
            "enumerable": True,
            "expected_paths": path_count,
            "expected_nodes": node_count,
            "skeleton": "full-balanced-tree",
        },
    )
    structural_errors = validate_graph(graph, max_nodes=spec.max_nodes)
    if structural_errors:
        raise GraphError("; ".join(structural_errors))
    return graph


def parent_map(graph: StoryGraph) -> dict[str, list[str]]:
    parents: dict[str, list[str]] = {node_id: [] for node_id in graph.nodes}
    for node in graph.nodes.values():
        for choice in node.choices:
            if choice.target_node_id in parents:
                parents[choice.target_node_id].append(node.id)
    return parents


def child_map(graph: StoryGraph) -> dict[str, list[str]]:
    return {
        node.id: [choice.target_node_id for choice in node.choices]
        for node in graph.nodes.values()
    }


def reachable_nodes(graph: StoryGraph, start_id: str | None = None) -> set[str]:
    start = start_id or graph.root_id
    if start not in graph.nodes:
        return set()
    seen: set[str] = set()
    queue: deque[str] = deque([start])
    while queue:
        node_id = queue.popleft()
        if node_id in seen:
            continue
        seen.add(node_id)
        queue.extend(
            choice.target_node_id
            for choice in graph.nodes[node_id].choices
            if choice.target_node_id in graph.nodes
        )
    return seen


def topological_order(graph: StoryGraph) -> list[str]:
    parents = parent_map(graph)
    indegree = {node_id: len(items) for node_id, items in parents.items()}
    queue: deque[str] = deque(sorted(key for key, value in indegree.items() if value == 0))
    order: list[str] = []
    children = child_map(graph)
    while queue:
        node_id = queue.popleft()
        order.append(node_id)
        for child_id in children.get(node_id, []):
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                queue.append(child_id)
    if len(order) != len(graph.nodes):
        raise GraphError("graph contains a cycle")
    return order


def validate_graph(graph: StoryGraph, *, max_nodes: int | None = None) -> list[str]:
    errors: list[str] = []
    if graph.root_id not in graph.nodes:
        errors.append("root node does not exist")
        return errors
    if max_nodes is not None and len(graph.nodes) > max_nodes:
        errors.append(f"graph has {len(graph.nodes)} nodes, exceeding {max_nodes}")
    seen_choice_ids: set[str] = set()
    for node_id, node in graph.nodes.items():
        if node_id != node.id:
            errors.append(f"node dictionary key {node_id!r} does not match node.id {node.id!r}")
        if node.terminal and node.choices:
            errors.append(f"terminal node {node_id!r} has outgoing choices")
        if not node.terminal and not node.choices:
            errors.append(f"non-terminal node {node_id!r} has no outgoing choices")
        for choice in node.choices:
            if choice.id in seen_choice_ids:
                errors.append(f"choice id {choice.id!r} is duplicated")
            seen_choice_ids.add(choice.id)
            if choice.target_node_id not in graph.nodes:
                errors.append(
                    f"choice {choice.id!r} points to missing node {choice.target_node_id!r}"
                )
    try:
        topological_order(graph)
    except GraphError as exc:
        errors.append(str(exc))
    reachable = reachable_nodes(graph)
    unreachable = sorted(set(graph.nodes) - reachable)
    if unreachable:
        errors.append(f"unreachable nodes: {', '.join(unreachable)}")
    return errors


def enumerate_paths(
    graph: StoryGraph,
    *,
    max_paths: int = 256,
    max_depth: int = 64,
) -> list[list[str]]:


    errors = validate_graph(graph)
    if errors:
        raise GraphError("; ".join(errors))
    paths: list[list[str]] = []
    active: set[str] = set()

    def visit(node_id: str, path: list[str]) -> None:
        if len(path) > max_depth:
            raise GraphLimitError(f"path depth exceeds max_depth={max_depth}")
        if node_id in active:
            raise GraphError(f"cycle encountered at {node_id!r}")
        node = graph.nodes[node_id]
        active.add(node_id)
        current = [*path, node_id]
        if node.terminal:
            paths.append(current)
            if len(paths) > max_paths:
                raise GraphLimitError(f"path count exceeds max_paths={max_paths}")
        else:
            for choice in node.choices:
                visit(choice.target_node_id, current)
        active.remove(node_id)

    visit(graph.root_id, [])
    return paths


def descendants(graph: StoryGraph, node_ids: Iterable[str]) -> set[str]:
    children = child_map(graph)
    found: set[str] = set()
    queue: deque[str] = deque(node_ids)
    while queue:
        node_id = queue.popleft()
        if node_id in found:
            continue
        found.add(node_id)
        queue.extend(children.get(node_id, []))
    return found


def invalidate_descendants(graph: StoryGraph, node_ids: Iterable[str]) -> set[str]:


    invalidated = descendants(graph, node_ids)
    for node_id in invalidated:
        node = graph.nodes[node_id]
        node.verification_stale = True
    return invalidated


def ledger_fingerprint(ledger: Mapping[str, Any]) -> str:
    canonical = json.dumps(ledger, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


@dataclass(slots=True)
class MergeResolution:
    unsafe_nodes: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    cloned_nodes: dict[str, list[str]] = field(default_factory=dict)
    needs_recursive_review: list[str] = field(default_factory=list)


def find_unsafe_merges(
    graph: StoryGraph,
    incoming_fingerprints: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, list[str]]]:


    parents = parent_map(graph)
    unsafe: dict[str, dict[str, list[str]]] = {}
    for node_id, parent_ids in parents.items():
        if len(parent_ids) < 2:
            continue
        supplied = incoming_fingerprints.get(node_id, {})
        groups: dict[str, list[str]] = defaultdict(list)
        for parent_id in parent_ids:
            fingerprint = supplied.get(parent_id, "MISSING")
            groups[fingerprint].append(parent_id)
        if len(groups) > 1 or "MISSING" in groups:
            unsafe[node_id] = dict(groups)
    return unsafe


def split_unsafe_merges(
    graph: StoryGraph,
    incoming_fingerprints: Mapping[str, Mapping[str, str]],
) -> tuple[StoryGraph, MergeResolution]:


    staged = copy.deepcopy(graph)
    unsafe = find_unsafe_merges(staged, incoming_fingerprints)
    resolution = MergeResolution(unsafe_nodes=unsafe)
    if not unsafe:
        return staged, resolution

    for node_id, groups in unsafe.items():
        original = staged.nodes[node_id]
        group_items = sorted(groups.items(), key=lambda item: item[0])
        clone_ids: list[str] = []
        for index, (_, parent_ids) in enumerate(group_items):
            if index == 0:
                target_id = node_id
            else:
                target_id = f"{node_id}__ledger_{index + 1}"
                suffix = 2
                while target_id in staged.nodes:
                    target_id = f"{node_id}__ledger_{index + 1}_{suffix}"
                    suffix += 1
                clone = copy.deepcopy(original)
                clone.id = target_id
                clone.version += 1
                clone.verification_stale = True
                for slot in clone.slots:
                    slot.node_id = target_id
                    slot.id = f"{slot.id}__ledger_{index + 1}"
                staged.nodes[target_id] = clone
                clone_ids.append(target_id)
            for parent_id in parent_ids:
                parent = staged.nodes[parent_id]
                for choice in parent.choices:
                    if choice.target_node_id == node_id:
                        choice.target_node_id = target_id
        if clone_ids:
            resolution.cloned_nodes[node_id] = clone_ids
            downstream = descendants(staged, [node_id, *clone_ids])
            resolution.needs_recursive_review.extend(sorted(downstream))

    staged.version += 1
    invalidate_descendants(staged, resolution.needs_recursive_review)
    structural_errors = validate_graph(staged)
    if structural_errors:
        raise GraphError("merge splitting produced an invalid graph: " + "; ".join(structural_errors))
    return staged, resolution

