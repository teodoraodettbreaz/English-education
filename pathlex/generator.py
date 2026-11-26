from __future__ import annotations

import copy
import re
from collections import Counter
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Iterable

from .llm import LLMError, LLMProvider, LLMResponseError, complete_json
from .prompts import node_generation_messages, to_plain


@dataclass(slots=True)
class GeneratedChoice:
    choice_id: str
    label_en: str
    label_zh: str
    next_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GeneratedChoice":
        return cls(
            choice_id=str(payload.get("choice_id") or payload.get("id") or ""),
            label_en=str(payload.get("label_en") or ""),
            label_zh=str(payload.get("label_zh") or ""),
            next_id=str(payload.get("next_id") or payload.get("target_node_id") or ""),
        )


@dataclass(slots=True)
class GeneratedOpportunity:
    slot_id: str
    target_id: str
    surface: str
    mode: str
    context: str
    phase: str
    evidence_span: str
    retrieval: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GeneratedOpportunity":
        retrieval = payload.get("retrieval")
        return cls(
            slot_id=str(payload.get("slot_id") or payload.get("id") or ""),
            target_id=str(payload.get("target_id") or ""),
            surface=str(payload.get("surface") or ""),
            mode=str(payload.get("mode") or ""),
            context=str(payload.get("context") or payload.get("context_label") or ""),
            phase=str(payload.get("phase") or ""),
            evidence_span=str(payload.get("evidence_span") or ""),
            retrieval=dict(retrieval) if isinstance(retrieval, dict) else {},
        )


@dataclass(slots=True)
class GeneratedNode:
    node_id: str
    depth: int
    title: str
    story_markdown: str
    support: dict[str, str]
    plot_state: dict[str, Any]
    choices: list[GeneratedChoice]
    opportunities: list[GeneratedOpportunity]
    safety_notes: list[str]
    planned_slots: list[dict[str, Any]] = field(default_factory=list)
    structural_errors: list[str] = field(default_factory=list)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "depth": self.depth,
            "title": self.title,
            "story_markdown": self.story_markdown,
            "support": dict(self.support),
            "plot_state": copy.deepcopy(self.plot_state),
            "choices": [choice.to_dict() for choice in self.choices],
            "opportunities": [item.to_dict() for item in self.opportunities],
            "safety_notes": list(self.safety_notes),
            "planned_slots": copy.deepcopy(self.planned_slots),
            "structural_errors": list(self.structural_errors),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GeneratedNode":


        raw_choices = payload.get("choices") or []
        raw_opportunities = payload.get("opportunities") or []
        return cls(
            node_id=str(payload.get("node_id") or payload.get("id") or ""),
            depth=int(payload.get("depth") or 0),
            title=str(payload.get("title") or ""),
            story_markdown=str(payload.get("story_markdown") or payload.get("text") or ""),
            support=_bilingual(payload.get("support")),
            plot_state=(
                copy.deepcopy(payload.get("plot_state"))
                if isinstance(payload.get("plot_state"), dict)
                else {}
            ),
            choices=[
                GeneratedChoice.from_dict(item)
                for item in raw_choices
                if isinstance(item, dict)
            ],
            opportunities=[
                GeneratedOpportunity.from_dict(item)
                for item in raw_opportunities
                if isinstance(item, dict)
            ],
            safety_notes=[str(item) for item in payload.get("safety_notes") or []],
            planned_slots=copy.deepcopy(payload.get("planned_slots") or []),
            structural_errors=[
                str(item) for item in payload.get("structural_errors") or []
            ],
            version=int(payload.get("version") or 1),
        )

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        expected_id: str,
        depth: int,
        expected_next_ids: list[str],
        planned_slots: list[dict[str, Any]],
    ) -> "GeneratedNode":
        node_id = str(payload.get("node_id", ""))
        if node_id != expected_id:
            raise LLMResponseError(
                f"Generated node ID {node_id!r} does not match {expected_id!r}."
            )
        story_markdown = payload.get("story_markdown")
        if not isinstance(story_markdown, str) or not story_markdown.strip():
            raise LLMResponseError(f"Node {expected_id} has no story_markdown.")
        raw_choices = payload.get("choices", [])
        if not isinstance(raw_choices, list):
            raise LLMResponseError(f"Node {expected_id} choices must be a list.")
        choices: list[GeneratedChoice] = []
        for index, raw in enumerate(raw_choices):
            if not isinstance(raw, dict):
                raise LLMResponseError(f"Node {expected_id} choice {index} is invalid.")
            choices.append(
                GeneratedChoice(
                    choice_id=str(raw.get("choice_id") or f"{expected_id}-c{index + 1}"),
                    label_en=str(raw.get("label_en", "")).strip(),
                    label_zh=str(raw.get("label_zh", "")).strip(),
                    next_id=str(raw.get("next_id", "")),
                )
            )
        raw_opportunities = payload.get("opportunities", [])
        if not isinstance(raw_opportunities, list):
            raise LLMResponseError(f"Node {expected_id} opportunities must be a list.")
        opportunities: list[GeneratedOpportunity] = []
        for index, raw in enumerate(raw_opportunities):
            if not isinstance(raw, dict):
                raise LLMResponseError(
                    f"Node {expected_id} opportunity {index} is invalid."
                )
            opportunities.append(
                GeneratedOpportunity(
                    slot_id=str(raw.get("slot_id", "")),
                    target_id=str(raw.get("target_id", "")),
                    surface=str(raw.get("surface", "")),
                    mode=str(raw.get("mode", "")),
                    context=str(raw.get("context", "")),
                    phase=str(raw.get("phase", "")),
                    evidence_span=str(raw.get("evidence_span", "")),
                    retrieval=(
                        dict(raw.get("retrieval", {}))
                        if isinstance(raw.get("retrieval", {}), dict)
                        else {}
                    ),
                )
            )
        node = cls(
            node_id=node_id,
            depth=depth,
            title=str(payload.get("title", "")).strip(),
            story_markdown=story_markdown.strip(),
            support=_bilingual(payload.get("support")),
            plot_state=(
                copy.deepcopy(payload.get("plot_state"))
                if isinstance(payload.get("plot_state"), dict)
                else {"summary": str(payload.get("plot_state", ""))}
            ),
            choices=choices,
            opportunities=opportunities,
            safety_notes=[str(note) for note in payload.get("safety_notes", [])]
            if isinstance(payload.get("safety_notes", []), list)
            else [],
            planned_slots=copy.deepcopy(planned_slots),
        )
        node.structural_errors.extend(
            structural_node_checks(node, expected_next_ids=expected_next_ids)
        )
        return node


@dataclass(slots=True)
class GeneratedStory:
    story_id: str
    root_id: str
    nodes: dict[str, GeneratedNode]
    edges: dict[str, list[str]]
    status: str
    errors: list[str] = field(default_factory=list)
    prompt_version: str = "pathlex-2026-11-v1"
    verifications: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "story_id": self.story_id,
            "root_id": self.root_id,
            "nodes": {key: value.to_dict() for key, value in self.nodes.items()},
            "edges": copy.deepcopy(self.edges),
            "status": self.status,
            "errors": list(self.errors),
            "prompt_version": self.prompt_version,
            "verifications": {
                key: value.to_dict() if hasattr(value, "to_dict") else to_plain(value)
                for key, value in self.verifications.items()
            },
        }

    def clone(self) -> "GeneratedStory":
        return copy.deepcopy(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GeneratedStory":


        raw_nodes = payload.get("nodes") or {}
        if not isinstance(raw_nodes, dict):
            raise ValueError("Persisted story nodes must be an object.")
        raw_edges = payload.get("edges") or {}
        if not isinstance(raw_edges, dict):
            raise ValueError("Persisted story edges must be an object.")
        story = cls(
            story_id=str(payload.get("story_id") or ""),
            root_id=str(payload.get("root_id") or ""),
            nodes={
                str(node_id): GeneratedNode.from_dict(node)
                for node_id, node in raw_nodes.items()
                if isinstance(node, dict)
            },
            edges={
                str(source): [str(target) for target in targets]
                for source, targets in raw_edges.items()
                if isinstance(targets, list)
            },
            status=str(payload.get("status") or "UNKNOWN"),
            errors=[str(item) for item in payload.get("errors") or []],
            prompt_version=str(payload.get("prompt_version") or "pathlex-2026-11-v1"),
        )
        raw_verifications = payload.get("verifications") or {}
        if isinstance(raw_verifications, dict):

            from .verifier import NodeVerification

            story.verifications = {
                str(node_id): NodeVerification.from_dict(value)
                for node_id, value in raw_verifications.items()
                if isinstance(value, dict)
            }
        return story


@dataclass(slots=True)
class GenerationResult:
    story: GeneratedStory
    generated_node_count: int
    failed_node_id: str | None = None


def _bilingual(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {"en": str(value or ""), "zh": str(value or "")}
    return {"en": str(value.get("en", "")), "zh": str(value.get("zh", ""))}


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


def _id(value: Any) -> str:
    result = _get(value, "node_id", "id", default="")
    return str(result)


def _nodes(graph: Any) -> dict[str, Any]:
    raw = _get(graph, "nodes", default={})
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    if isinstance(raw, Iterable) and not isinstance(raw, (str, bytes)):
        return {_id(node): node for node in raw}
    raise ValueError("Graph nodes must be a mapping or iterable.")


def _edge_map(graph: Any, nodes: dict[str, Any]) -> dict[str, list[str]]:
    edges: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    raw_edges = _get(graph, "edges", "adjacency", default=None)
    if isinstance(raw_edges, dict):
        for source, targets in raw_edges.items():
            values = targets if isinstance(targets, list) else list(targets or [])
            edges[str(source)] = [str(_get(item, "target", "next_id", default=item)) for item in values]
        return edges
    if isinstance(raw_edges, list):
        for edge in raw_edges:
            source = str(_get(edge, "source", "from_id", default=""))
            target = str(_get(edge, "target", "to_id", "next_id", default=""))
            if source and target:
                edges.setdefault(source, []).append(target)
        return edges
    for node_id, node in nodes.items():
        children = _get(node, "children", "next_ids", "outgoing", default=None)
        if children is None:
            children = _get(node, "choices", default=[])
        edges[node_id] = [
            str(
                _get(
                    item,
                    "target",
                    "target_node_id",
                    "next_id",
                    default=item,
                )
            )
            for item in children
        ]
    return edges


def _topological_order(root_id: str, edges: dict[str, list[str]]) -> list[str]:
    order: list[str] = []
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in permanent:
            return
        if node_id in temporary:
            raise ValueError("Story graph contains a cycle; finite DAG required.")
        temporary.add(node_id)
        for child in edges.get(node_id, []):
            visit(child)
        temporary.remove(node_id)
        permanent.add(node_id)
        order.append(node_id)

    visit(root_id)
    order.reverse()
    return order


def _parents(edges: dict[str, list[str]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {node_id: [] for node_id in edges}
    for source, targets in edges.items():
        for target in targets:
            result.setdefault(target, []).append(source)
    return result


def structural_node_checks(
    node: GeneratedNode, *, expected_next_ids: list[str]
) -> list[str]:
    errors: list[str] = []
    actual_targets = [choice.next_id for choice in node.choices]
    if sorted(actual_targets) != sorted(expected_next_ids):
        errors.append(
            f"Outgoing choices {actual_targets!r} do not match planned edges {expected_next_ids!r}."
        )
    if any(not choice.label_en or not choice.label_zh for choice in node.choices):
        errors.append("Every nonterminal choice requires English and Chinese labels.")
    choice_ids = [choice.choice_id for choice in node.choices]
    if any(not choice_id for choice_id in choice_ids):
        errors.append("Every outgoing choice requires a non-empty choice_id.")
    duplicate_choices = sorted(
        choice_id for choice_id, count in Counter(choice_ids).items() if count > 1
    )
    if duplicate_choices:
        errors.append(f"Duplicate choice IDs: {', '.join(duplicate_choices)}.")

    planned_by_id = {
        str(slot.get("slot_id") or slot.get("id") or ""): slot
        for slot in node.planned_slots
    }
    planned_ids = set(planned_by_id)
    realized_id_list = [item.slot_id for item in node.opportunities]
    realized_ids = set(realized_id_list)
    duplicate_slots = sorted(
        slot_id for slot_id, count in Counter(realized_id_list).items() if count > 1
    )
    if duplicate_slots:
        errors.append(f"Duplicate realized opportunity slots: {', '.join(duplicate_slots)}.")
    missing = sorted(slot_id for slot_id in planned_ids - realized_ids if slot_id)
    if missing:
        errors.append(f"Missing planned opportunity slots: {', '.join(missing)}.")
    extra = sorted(slot_id for slot_id in realized_ids - planned_ids if slot_id)
    if extra:
        errors.append(f"Unplanned opportunity slots: {', '.join(extra)}.")
    target_by_slot = {
        str(slot.get("slot_id") or slot.get("id") or ""): str(
            slot.get("surface")
            or slot.get("required_surface")
            or slot.get("word")
            or slot.get("target")
            or ""
        )
        for slot in node.planned_slots
    }
    for opportunity in node.opportunities:
        planned = planned_by_id.get(opportunity.slot_id)
        if planned is None:
            continue
        expected_target = str(
            planned.get("target_id") or planned.get("lexical_unit_id") or ""
        )
        expected_mode = str(planned.get("mode") or "exposure")
        expected_context = str(
            planned.get("context_label") or planned.get("context") or "general"
        )
        expected_phase = str(planned.get("phase") or "middle")
        for field_name, actual, expected in (
            ("target_id", opportunity.target_id, expected_target),
            ("mode", opportunity.mode, expected_mode),
            ("context", opportunity.context, expected_context),
            ("phase", opportunity.phase, expected_phase),
        ):
            if actual != expected:
                errors.append(
                    f"Opportunity {opportunity.slot_id} {field_name}={actual!r} "
                    f"does not match planned value {expected!r}."
                )
        target = target_by_slot.get(opportunity.slot_id) or opportunity.surface
        if not target:
            continue
        escaped = re.escape(target)
        if opportunity.mode in {"exposure", "judgment"}:
            if not re.search(rf"\*\*[^*]*{escaped}[^*]*\*\*", node.story_markdown, re.I):
                errors.append(
                    f"Visible opportunity {opportunity.slot_id} is not bold in story prose."
                )
        if opportunity.mode == "retrieval":
            pre_answer = " ".join(
                [
                    node.story_markdown,
                    str(opportunity.retrieval.get("question_en", "")),
                    str(opportunity.retrieval.get("question_zh", "")),
                    str(opportunity.retrieval.get("hint_en", "")),
                    str(opportunity.retrieval.get("hint_zh", "")),
                ]
            )
            if re.search(rf"\b{escaped}\b", pre_answer, re.I):
                errors.append(
                    f"Retrieval opportunity {opportunity.slot_id} reveals its answer before response."
                )
            accepted = opportunity.retrieval.get("accepted_answers", [])
            if not isinstance(accepted, list) or not accepted:
                errors.append(
                    f"Retrieval opportunity {opportunity.slot_id} has no accepted answer."
                )
            elif target.casefold().strip() not in {
                str(item).casefold().strip() for item in accepted
            }:
                errors.append(
                    f"Retrieval opportunity {opportunity.slot_id} does not accept the "
                    "planned target form."
                )
    return errors


def apply_generated_story(story: GeneratedStory, planned_graph: Any) -> Any:


    from .models import Choice, OpportunitySlot, RetrievalPrompt, StoryStatus

    graph = copy.deepcopy(planned_graph)
    for node_id, generated in story.nodes.items():
        if node_id not in graph.nodes:
            raise ValueError(f"Generated story contains unknown node {node_id!r}.")
        node = graph.nodes[node_id]
        node.title = generated.title
        node.text = generated.story_markdown
        node.plot_state = copy.deepcopy(generated.plot_state)
        existing_slots = {slot.id for slot in node.slots}
        for raw_slot in generated.planned_slots:
            slot_id = str(raw_slot.get("slot_id") or raw_slot.get("id") or "")
            if not slot_id or slot_id in existing_slots:
                continue
            node.slots.append(
                OpportunitySlot.from_dict(
                    {
                        "id": slot_id,
                        "target_id": str(raw_slot.get("target_id", "")),
                        "node_id": node_id,
                        "occurrence_index": int(
                            raw_slot.get("occurrence_index") or 10_000 + len(node.slots)
                        ),
                        "mode": str(raw_slot.get("mode") or "exposure"),
                        "context_label": str(
                            raw_slot.get("context_label")
                            or raw_slot.get("context")
                            or "repair-context"
                        ),
                        "phase": str(raw_slot.get("phase") or node.phase),
                        "required_surface": str(
                            raw_slot.get("required_surface")
                            or raw_slot.get("surface")
                            or ""
                        ),
                    }
                )
            )
            existing_slots.add(slot_id)
        node.choices = [
            Choice(
                id=choice.choice_id,
                target_node_id=choice.next_id,
                label_en=choice.label_en,
                label_zh=choice.label_zh,
            )
            for choice in generated.choices
        ]
        node.retrieval_prompts = []
        for opportunity in generated.opportunities:
            if opportunity.mode != "retrieval":
                continue
            node.retrieval_prompts.append(
                RetrievalPrompt(
                    slot_id=opportunity.slot_id,
                    prompt_en=str(opportunity.retrieval.get("question_en", "")),
                    prompt_zh=str(opportunity.retrieval.get("question_zh", "")),
                    accepted_answers=[
                        str(item)
                        for item in opportunity.retrieval.get("accepted_answers", [])
                    ],
                    feedback_en=str(opportunity.retrieval.get("feedback_en", "")),
                    feedback_zh=str(opportunity.retrieval.get("feedback_zh", "")),
                )
            )
        node.version = max(node.version + 1, generated.version)
        node.verification_stale = True
    graph.version += 1
    if graph.status is not StoryStatus.PLAN_INFEASIBLE:
        graph.status = StoryStatus.PLAN_FEASIBLE
    graph.metadata["generated_story"] = {
        node_id: {
            "support": copy.deepcopy(node.support),
            "opportunities": [item.to_dict() for item in node.opportunities],
            "safety_notes": list(node.safety_notes),
            "structural_errors": list(node.structural_errors),
        }
        for node_id, node in story.nodes.items()
    }
    return graph


class PathLexGenerator:
    def __init__(
        self,
        provider: LLMProvider,
        *,
        temperature: float = 0.25,
        max_tokens_per_node: int = 4096,
        format_retries: int = 1,
    ) -> None:
        self.provider = provider
        self.temperature = temperature
        self.max_tokens_per_node = max_tokens_per_node
        self.format_retries = max(0, format_retries)

    def generate(
        self,
        specification: Any,
        planned_graph: Any,
        *,
        interface_language: str = "en",
    ) -> GenerationResult:
        nodes = _nodes(planned_graph)
        root_id = str(_get(planned_graph, "root_id", "start_id", default=""))
        if not root_id or root_id not in nodes:
            raise ValueError("Planned graph must identify a valid root_id.")
        edges = _edge_map(planned_graph, nodes)
        order = _topological_order(root_id, edges)
        parents = _parents(edges)
        story_id = str(
            _get(planned_graph, "story_id", "graph_id", "id", default="story-draft")
        )
        story = GeneratedStory(
            story_id=story_id,
            root_id=root_id,
            nodes={},
            edges=edges,
            status="GENERATING",
        )
        for node_id in order:
            planned_node = nodes[node_id]
            depth = int(_get(planned_node, "depth", default=0) or 0)
            slots = [
                to_plain(slot)
                for slot in (_get(planned_node, "slots", "opportunity_slots", default=[]) or [])
            ]
            outgoing = [
                {"choice_id": f"{node_id}-c{index + 1}", "next_id": target}
                for index, target in enumerate(edges.get(node_id, []))
            ]
            incoming_states = [
                story.nodes[parent].plot_state
                for parent in parents.get(node_id, [])
                if parent in story.nodes
            ]
            incoming_state: Any
            if len(incoming_states) == 1:
                incoming_state = incoming_states[0]
            else:
                incoming_state = {
                    "incoming_branches": incoming_states,
                    "merge_requires_consistent_facts": len(incoming_states) > 1,
                }
            messages = node_generation_messages(
                specification=specification,
                node=planned_node,
                slots=slots,
                outgoing_edges=outgoing,
                incoming_plot_state=incoming_state,
                interface_language=interface_language,
            )
            last_error: Exception | None = None
            for attempt in range(self.format_retries + 1):
                try:
                    payload = complete_json(
                        self.provider,
                        messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens_per_node,
                        purpose=f"generate node {node_id}",
                    )
                    generated = GeneratedNode.from_payload(
                        payload,
                        expected_id=node_id,
                        depth=depth,
                        expected_next_ids=edges.get(node_id, []),
                        planned_slots=slots,
                    )
                    story.nodes[node_id] = generated
                    last_error = None
                    break
                except (LLMError, ValueError, TypeError) as exc:
                    last_error = exc
                    if attempt < self.format_retries:
                        messages = list(messages) + [
                            {
                                "role": "user",
                                "content": (
                                    "Your previous response could not be accepted: "
                                    f"{str(exc)[:500]}. Return a complete JSON object only."
                                ),
                            }
                        ]
            if last_error is not None:
                story.status = "GENERATION_FAILURE"
                story.errors.append(f"Node {node_id}: {str(last_error)[:1000]}")
                return GenerationResult(
                    story=story,
                    generated_node_count=len(story.nodes),
                    failed_node_id=node_id,
                )
        story.status = (
            "GENERATED_WITH_STRUCTURAL_ERRORS"
            if any(node.structural_errors for node in story.nodes.values())
            else "GENERATED"
        )
        return GenerationResult(story=story, generated_node_count=len(story.nodes))


__all__ = [
    "apply_generated_story",
    "GeneratedChoice",
    "GeneratedNode",
    "GeneratedOpportunity",
    "GeneratedStory",
    "GenerationResult",
    "PathLexGenerator",
    "structural_node_checks",
]

