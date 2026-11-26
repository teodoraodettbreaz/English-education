from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from pathlex.config import Settings
from pathlex.llm import Message, ScriptedTestProvider


def settings_for(root: Path) -> Settings:
    return Settings(
        host="127.0.0.1",
        port=0,
        database_path=root / "ENGINEERING_TEST.sqlite3",
        static_path=Path(__file__).resolve().parents[1] / "pathlex" / "static",
        max_request_bytes=1_000_000,
        max_paths=64,
        max_nodes=255,
    )


def story_payload(*, language: str = "en") -> dict[str, Any]:
    return {
        "title": "ENGINEERING TEST: Route through the fog",
        "interface_language": language,
        "cefr_level": "B1",
        "theme": "A harmless route-finding puzzle",
        "known_vocabulary": ["route", "map", "fog", "choose"],
        "base_vocabulary": ["a", "the", "be", "find", "go", "through"],
        "safety_notes": "No violence; no stereotypes",
        "graph": {
            "depth": 3,
            "branch_factor": 2,
            "max_paths": 4,
            "common_prefix_opportunity_limit": 0.5,
        },
        "targets": [
            {
                "word": "navigate",
                "sense": "to find or plan a route",
                "part_of_speech": "verb",
                "allowed_collocations": ["navigate a route", "navigate through"],
                "forbidden_collocations": ["navigate a person"],
                "positive_examples": ["We navigate through the fog."],
                "negative_examples": ["We navigate him the map."],
                "contexts": ["route planning", "directions"],
                "min_occurrences": 2,
                "min_gap": 0,
                "max_gap": 0,
                "min_contexts": 2,
                "mode_counts": {"exposure": 1, "judgment": 0, "retrieval": 1},
            }
        ],
    }


def _json_after(text: str, label: str) -> Any:
    position = text.index(label) + len(label)
    remainder = text[position:].lstrip()
    value, _ = json.JSONDecoder().raw_decode(remainder)
    return value


def engineering_responder(messages: Sequence[Message]) -> str:


    system = messages[0]["content"]
    user = messages[-1]["content"]
    if "constrained writing component" in system:
        node = _json_after(user, "Node and depth:\n")
        slots = _json_after(user, "Required pedagogical slots:\n")
        edges = _json_after(user, "Allowed outgoing edges (use every edge exactly once; terminals use []):\n")
        visible = [
            str(slot.get("required_surface") or "target")
            for slot in slots
            if slot.get("mode") in {"exposure", "judgment"}
        ]
        story = "A route puzzle waits beside the quiet harbor."
        if visible:
            story += " We **" + "** and **".join(visible) + "** through the fog."
        opportunities = []
        for slot in slots:
            mode = str(slot.get("mode") or "exposure")
            surface = str(slot.get("required_surface") or "")
            retrieval = {}
            if mode == "retrieval":
                retrieval = {
                    "question_en": "Which verb means to find or plan a route?",
                    "question_zh": "哪个动词表示寻找或规划路线？",
                    "hint_en": "It begins with n.",
                    "hint_zh": "它以字母 n 开头。",
                    "accepted_answers": [surface],
                    "feedback_en": f"The requested word is {surface}.",
                    "feedback_zh": f"本题目标词是 {surface}。",
                }
            opportunities.append(
                {
                    "slot_id": slot["id"],
                    "target_id": slot["target_id"],
                    "surface": "" if mode == "retrieval" else surface,
                    "mode": mode,
                    "context": slot["context_label"],
                    "phase": slot["phase"],
                    "evidence_span": "engineering fixture",
                    "retrieval": retrieval,
                }
            )
        payload = {
            "node_id": node["id"],
            "title": f"Scene {node['id']}",
            "story_markdown": story,
            "support": {
                "en": "Use the route clues before choosing.",
                "zh": "选择前请先利用路线线索。",
            },
            "plot_state": {
                "summary": f"The reader reached {node['id']}.",
                "characters": ["The guide remains calm."],
                "open_threads": [],
            },
            "choices": [
                {
                    "choice_id": edge["choice_id"],
                    "label_en": f"Take route {index + 1}",
                    "label_zh": f"选择路线 {index + 1}",
                    "next_id": edge["next_id"],
                }
                for index, edge in enumerate(edges)
            ],
            "opportunities": opportunities,
            "safety_notes": [],
        }
        return json.dumps(payload, ensure_ascii=False)

    if "conservative semantic verifier" in system:
        slots = _json_after(user, "Planned slots:\n")
        node = _json_after(user, "Generated node:\n")
        payload = {
            "node_id": node["node_id"],
            "verdicts": [
                {
                    "slot_id": slot["id"],
                    "target_id": slot["target_id"],
                    "label": "accepted",
                    "confidence": 0.99,
                    "sense_ok": True,
                    "pos_ok": True,
                    "pattern_ok": True,
                    "grammar_ok": True,
                    "context_ok": True,
                    "mode_ok": True,
                    "evidence_span": "engineering fixture",
                    "reason": "Deterministic wiring fixture accepts the declared slot.",
                }
                for slot in slots
            ],
            "node_notes": ["ENGINEERING_TEST_DOUBLE"],
        }
        return json.dumps(payload)

    raise AssertionError("The engineering provider received an unexpected prompt")


def provider_factory() -> ScriptedTestProvider:
    return ScriptedTestProvider(responder=engineering_responder)
