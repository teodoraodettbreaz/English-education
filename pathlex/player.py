from __future__ import annotations

import re
from typing import Any


class PlayerError(ValueError):
    pass


def _nodes_by_id(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = graph.get("nodes")
    if isinstance(nodes, dict):
        return {str(key): value for key, value in nodes.items() if isinstance(value, dict)}
    if isinstance(nodes, list):
        return {
            str(node.get("id")): node
            for node in nodes
            if isinstance(node, dict) and node.get("id") is not None
        }
    return {}


def root_node_id(graph: dict[str, Any]) -> str:
    root = graph.get("root_id") or graph.get("start_node_id")
    if not isinstance(root, str) or not root:
        raise PlayerError("The published graph has no root node")
    if root not in _nodes_by_id(graph):
        raise PlayerError("The published graph root does not exist")
    return root


def initial_state(root_id: str) -> dict[str, Any]:
    return {
        "path": [root_id],
        "answers": {},
        "answered_slots": [],
        "answered_nodes": [],
        "visited": [root_id],
    }


def _localized(value: Any, language: str, fallback: str = "") -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        selected = value.get("zh" if language == "zh" else "en")
        if isinstance(selected, str):
            return selected
        for key in ("en", "zh"):
            if isinstance(value.get(key), str):
                return value[key]
    return fallback


def _choice_label(choice: dict[str, Any], language: str, fallback: str) -> str:
    direct = choice.get("label_zh" if language == "zh" else "label_en")
    if isinstance(direct, str) and direct:
        return direct
    return _localized(choice.get("label"), language, fallback)


def _retrieval_prompts(node: dict[str, Any]) -> list[dict[str, Any]]:
    prompts = node.get("retrieval_prompts")
    if isinstance(prompts, list):
        return [prompt for prompt in prompts if isinstance(prompt, dict)]
    derived: list[dict[str, Any]] = []
    for opportunity in node.get("opportunities") or []:
        if not isinstance(opportunity, dict) or opportunity.get("mode") != "retrieval":
            continue
        retrieval = opportunity.get("retrieval")
        if not isinstance(retrieval, dict):
            continue
        derived.append(
            {
                "slot_id": opportunity.get("slot_id"),
                "prompt_en": retrieval.get("question_en") or retrieval.get("prompt_en"),
                "prompt_zh": retrieval.get("question_zh") or retrieval.get("prompt_zh"),
                "accepted_answers": retrieval.get("accepted_answers") or [],
                "feedback_en": retrieval.get("feedback_en"),
                "feedback_zh": retrieval.get("feedback_zh"),
                "expected_display": retrieval.get("expected_display"),
            }
        )
    if derived:
        return derived
    legacy = node.get("retrieval")
    return [legacy] if isinstance(legacy, dict) else []


def _retrieval_id(prompt: dict[str, Any], index: int) -> str:
    return str(prompt.get("slot_id") or prompt.get("id") or f"retrieval-{index + 1}")


def _retrieval_public(
    prompt: dict[str, Any], prompt_id: str, language: str, answer_state: dict[str, Any] | None
) -> dict[str, Any]:
    prompt_text = prompt.get("prompt_zh" if language == "zh" else "prompt_en")
    if not isinstance(prompt_text, str):
        prompt_text = _localized(prompt.get("prompt"), language)
    payload: dict[str, Any] = {
        "id": prompt_id,
        "prompt": prompt_text,
        "answered": answer_state is not None,
    }
    if answer_state is not None:
        feedback = prompt.get("feedback_zh" if language == "zh" else "feedback_en")
        if not isinstance(feedback, str):
            feedback = _localized(prompt.get("feedback"), language)
        expected = prompt.get("expected_display")
        if not expected:
            accepted_answers = prompt.get("accepted_answers") or []
            expected = str(accepted_answers[0]) if accepted_answers else ""
        payload.update(
            {
                "feedback": feedback,
                "accepted": bool(answer_state.get("accepted")),
                "submitted_answer": str(answer_state.get("answer") or ""),
                "expected_display": _localized(expected, language, str(expected)),
            }
        )
    return payload


def public_node(
    graph: dict[str, Any], node_id: str, state: dict[str, Any], language: str
) -> dict[str, Any]:
    nodes = _nodes_by_id(graph)
    node = nodes.get(node_id)
    if node is None:
        raise PlayerError(f"Story node {node_id!r} does not exist")
    retrievals = _retrieval_prompts(node)
    choices = []
    for index, choice in enumerate(node.get("choices") or []):
        if not isinstance(choice, dict):
            continue
        choice_id = str(choice.get("id") or choice.get("choice_id") or f"choice-{index + 1}")
        choices.append({"id": choice_id, "label": _choice_label(choice, language, choice_id)})
    payload: dict[str, Any] = {
        "id": node_id,
        "title": _localized(node.get("title"), language),

        "text": str(node.get("text") or node.get("story_markdown") or ""),
        "support": _localized(node.get("support"), language),
        "choices": choices,
        "terminal": bool(node.get("terminal") or not choices),
        "depth": int(node.get("depth") or 0),
        "retrieval": None,
    }
    if retrievals:
        answers = state.get("answers") or {}
        answered_slots = set(state.get("answered_slots") or [])
        history: list[dict[str, Any]] = []
        pending: tuple[dict[str, Any], str] | None = None
        for index, prompt in enumerate(retrievals):
            prompt_id = _retrieval_id(prompt, index)
            answer_state = answers.get(prompt_id) if prompt_id in answered_slots else None
            if answer_state is not None:
                history.append(_retrieval_public(prompt, prompt_id, language, answer_state))
            elif pending is None:
                pending = (prompt, prompt_id)
        if pending is not None:
            payload["retrieval"] = _retrieval_public(pending[0], pending[1], language, None)
        elif history:
            payload["retrieval"] = history[-1]
        payload["retrieval_history"] = history
        payload["retrieval_remaining"] = len(retrievals) - len(history)
    return payload


def session_view(unit: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    graph = unit.get("graph") or {}
    state = session.get("state") or {}
    depth = max(0, len(state.get("path") or []) - 1)
    max_depth = int(
        (unit.get("spec") or {}).get("max_depth")
        or (unit.get("spec") or {}).get("depth")
        or 0
    )
    last_answer = state.get("last_answer") or {}
    if last_answer.get("node_id") != session.get("current_node_id"):
        last_answer = {}
    return {
        "id": session["id"],
        "unit_id": session["unit_id"],
        "title": unit.get("title", ""),
        "unit_title": unit.get("title", ""),
        "cefr_level": (unit.get("spec") or {}).get("cefr_level", ""),
        "language": session.get("language", "en"),
        "completed": bool(session.get("completed")),
        "complete": bool(session.get("completed")),
        "step": depth + 1,
        "total_steps": max_depth,
        "last_feedback": _localized(
            last_answer.get("feedback"), session.get("language", "en")
        ),
        "last_answer_correct": last_answer.get("accepted"),
        "progress": {
            "visited": len(state.get("visited") or []),
            "depth": depth,
            "max_depth": max_depth,
        },
        "node": public_node(
            graph,
            session["current_node_id"],
            state,
            session.get("language", "en"),
        ),
    }


def _normalize_answer(value: str) -> str:
    return re.sub(r"[^a-z0-9' -]+", "", value.casefold()).strip()


def submit_answer(
    graph: dict[str, Any], session: dict[str, Any], answer: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    if session.get("completed"):
        raise PlayerError("This story session is already complete")
    answer = answer.strip()
    if not answer:
        raise PlayerError("Enter an answer before checking it")
    if len(answer) > 300:
        raise PlayerError("The answer is longer than 300 characters")
    node_id = session["current_node_id"]
    node = _nodes_by_id(graph).get(node_id)
    retrievals = _retrieval_prompts(node) if isinstance(node, dict) else []
    if not retrievals:
        raise PlayerError("The current story node has no retrieval prompt")
    state = dict(session.get("state") or {})
    answered_slots = list(state.get("answered_slots") or [])
    retrieval: dict[str, Any] | None = None
    prompt_id = ""
    for index, candidate in enumerate(retrievals):
        candidate_id = _retrieval_id(candidate, index)
        if candidate_id not in answered_slots:
            retrieval = candidate
            prompt_id = candidate_id
            break
    if retrieval is None:
        raise PlayerError("Every retrieval prompt in this node has already been answered")
    accepted_answers = retrieval.get("accepted_answers") or []
    normalized = _normalize_answer(answer)
    accepted = normalized in {
        _normalize_answer(str(candidate)) for candidate in accepted_answers if candidate
    }
    answers = dict(state.get("answers") or {})
    answers[prompt_id] = {"answer": answer, "accepted": accepted}
    answered_slots.append(prompt_id)
    state["answers"] = answers
    state["answered_slots"] = answered_slots
    state["last_answer"] = {
        "node_id": node_id,
        "slot_id": prompt_id,
        "accepted": accepted,
        "feedback": {
            "en": str(retrieval.get("feedback_en") or ""),
            "zh": str(retrieval.get("feedback_zh") or ""),
        },
    }
    if all(
        _retrieval_id(item, index) in set(answered_slots)
        for index, item in enumerate(retrievals)
    ):
        answered_nodes = list(state.get("answered_nodes") or [])
        if node_id not in answered_nodes:
            answered_nodes.append(node_id)
        state["answered_nodes"] = answered_nodes
    return state, {
        "node_id": node_id,
        "slot_id": prompt_id,
        "accepted": accepted,
        "answer": answer,
    }


def choose(
    graph: dict[str, Any], session: dict[str, Any], choice_id: str
) -> tuple[str, dict[str, Any], bool, dict[str, Any]]:
    if session.get("completed"):
        raise PlayerError("This story session is already complete")
    nodes = _nodes_by_id(graph)
    node_id = session["current_node_id"]
    node = nodes.get(node_id)
    if node is None:
        raise PlayerError("The current story node no longer exists")
    state = dict(session.get("state") or {})
    if _retrieval_prompts(node) and node_id not in set(state.get("answered_nodes") or []):
        raise PlayerError("Answer the vocabulary prompt before choosing a path")
    selected: dict[str, Any] | None = None
    for index, choice_value in enumerate(node.get("choices") or []):
        if not isinstance(choice_value, dict):
            continue
        current_id = str(
            choice_value.get("id")
            or choice_value.get("choice_id")
            or f"choice-{index + 1}"
        )
        if current_id == choice_id:
            selected = choice_value
            break
    if selected is None:
        raise PlayerError("The selected path is not available from this node")
    next_id = (
        selected.get("next_node_id")
        or selected.get("target_node_id")
        or selected.get("next_id")
        or selected.get("target")
    )
    if not isinstance(next_id, str) or next_id not in nodes:
        raise PlayerError("The selected path points to a missing story node")
    path = list(state.get("path") or [node_id])
    visited = list(state.get("visited") or [node_id])
    path.append(next_id)
    visited.append(next_id)
    state["path"] = path
    state["visited"] = visited
    next_node = nodes[next_id]


    completed = False
    event = {"from": node_id, "choice_id": choice_id, "to": next_id}
    return next_id, state, completed, event

