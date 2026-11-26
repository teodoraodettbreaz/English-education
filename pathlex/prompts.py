from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


PROMPT_VERSION = "pathlex-2026-11-v1"


def to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_plain(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_plain(item) for item in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return to_plain(value.to_dict())
    if hasattr(value, "__dict__"):
        return {
            key: to_plain(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return value


def _json(value: Any) -> str:
    return json.dumps(to_plain(value), ensure_ascii=False, indent=2, sort_keys=True)


GENERATOR_SYSTEM = f"""You are the constrained writing component of PathLex.
Write one node of a finite English-learning branching story. Follow the supplied
story state, edge IDs, CEFR level, vocabulary boundary, and pedagogical slots
exactly. Never add an edge or change a next-node ID. Return JSON only.

Rules:
1. Story prose and choices are in English because the learner is studying English.
2. A planned exposure or judgment target must appear as **target** in story prose,
   using the specified sense, part of speech, pattern, and context.
3. For retrieval, do not reveal the target word in prose, choice labels, question,
   or hint before the learner answers. Put accepted answers and feedback only in
   the retrieval object; the application hides them until submission.
4. Give learner-facing support and feedback in BOTH English and Chinese. The
   current interface language controls which version is shown first, not whether
   either version exists.
5. Use mainly the allowed/known vocabulary. Do not use forbidden content or
   forbidden collocations. Keep plot facts consistent with the incoming state.
6. Include only opportunities that are actually realized in this node. Do not
   claim an opportunity merely because a word is present.

Prompt version: {PROMPT_VERSION}
"""


def node_generation_messages(
    *,
    specification: Any,
    node: Any,
    slots: list[Any],
    outgoing_edges: list[dict[str, Any]],
    incoming_plot_state: Any,
    interface_language: str,
) -> list[dict[str, str]]:
    language = "Chinese" if interface_language == "zh" else "English"
    schema = {
        "node_id": "must equal the supplied node ID",
        "title": "short English scene title",
        "story_markdown": "English prose; bold planned visible targets",
        "support": {"en": "brief optional learner support", "zh": "对应中文支持"},
        "plot_state": {
            "summary": "facts after this node",
            "characters": ["stable character facts"],
            "open_threads": ["unresolved plot facts"],
        },
        "choices": [
            {
                "choice_id": "stable ID",
                "label_en": "English learner-facing choice",
                "label_zh": "中文界面说明（不替代英语选择文本）",
                "next_id": "one supplied edge target",
            }
        ],
        "opportunities": [
            {
                "slot_id": "supplied pedagogical slot ID",
                "target_id": "supplied target ID",
                "surface": "realized target form, empty before retrieval",
                "mode": "exposure|judgment|retrieval",
                "context": "supplied context category",
                "phase": "opening|middle|ending",
                "evidence_span": "exact supporting text or question",
                "retrieval": {
                    "question_en": "English question, only for retrieval",
                    "question_zh": "中文任务说明, only for retrieval",
                    "hint_en": "must not reveal answer",
                    "hint_zh": "不得泄露答案",
                    "accepted_answers": ["answer variants"],
                    "feedback_en": "shown after answer",
                    "feedback_zh": "作答后显示",
                },
            }
        ],
        "safety_notes": ["empty unless a constraint needs review"],
    }
    user = f"""Create exactly one story node.

Current interface language: {language}

Teacher specification:
{_json(specification)}

Node and depth:
{_json(node)}

Incoming plot state:
{_json(incoming_plot_state)}

Required pedagogical slots:
{_json(slots)}

Allowed outgoing edges (use every edge exactly once; terminals use []):
{_json(outgoing_edges)}

Return exactly this JSON shape, with real values rather than comments:
{_json(schema)}
"""
    return [
        {"role": "system", "content": GENERATOR_SYSTEM},
        {"role": "user", "content": user},
    ]


VERIFIER_SYSTEM = f"""You are PathLex's conservative semantic verifier.
Judge only whether each claimed pedagogical opportunity is genuinely usable for
the teacher's exact lexical target. Prefer UNCERTAIN over accepting ambiguous
evidence. A string match is never enough. Return JSON only.

An opportunity is accepted only when all applicable conditions hold: requested
sense, part of speech, allowed collocation or syntax, grammatical naturalness,
context category, story phase, and practice mode. A retrieval opportunity also
requires that the answer was hidden until the learner responded and that feedback
appears afterward. A bold word without those properties is not automatically an
accepted opportunity.

Prompt version: {PROMPT_VERSION}
"""


def verification_messages(
    *,
    specification: Any,
    node: Any,
    planned_slots: list[Any],
    incoming_state: Any,
) -> list[dict[str, str]]:
    schema = {
        "node_id": "same node ID",
        "verdicts": [
            {
                "slot_id": "planned slot ID",
                "target_id": "target ID",
                "label": "accepted|rejected|uncertain",
                "confidence": 0.0,
                "sense_ok": False,
                "pos_ok": False,
                "pattern_ok": False,
                "grammar_ok": False,
                "context_ok": False,
                "mode_ok": False,
                "evidence_span": "short exact span",
                "reason": "brief auditable reason",
            }
        ],
        "node_notes": ["brief structural or semantic notes"],
    }
    return [
        {"role": "system", "content": VERIFIER_SYSTEM},
        {
            "role": "user",
            "content": f"""Verify this generated node against every planned slot.

Teacher specification:
{_json(specification)}

Incoming story and ledger state:
{_json(incoming_state)}

Planned slots:
{_json(planned_slots)}

Generated node:
{_json(node)}

Return exactly one verdict for every planned slot using this JSON shape:
{_json(schema)}
""",
        },
    ]


REPAIR_SYSTEM = f"""You are PathLex's transactional local story repairer.
Revise only the supplied node. Preserve its node ID and every outgoing next-node
ID. Address the specified worst-path lexical debt while keeping established plot
facts. Do not declare the graph feasible, verified, or unsatisfiable; downstream
code performs those checks. Return JSON only in the same node schema.

Prompt version: {PROMPT_VERSION}
"""


def repair_messages(
    *,
    specification: Any,
    node: Any,
    incoming_state: Any,
    debts: list[Any],
    allowed_edges: list[dict[str, Any]],
    interface_language: str,
) -> list[dict[str, str]]:
    language = "Chinese" if interface_language == "zh" else "English"
    return [
        {"role": "system", "content": REPAIR_SYSTEM},
        {
            "role": "user",
            "content": f"""Repair this node as a staged candidate.

Current interface language: {language}

Teacher specification:
{_json(specification)}

Incoming state:
{_json(incoming_state)}

Worst-path debts to address:
{_json(debts)}

Allowed outgoing edges (unchanged):
{_json(allowed_edges)}

Current node JSON:
{_json(node)}

Return the complete revised node JSON only. Keep bilingual support/feedback. For
retrieval, keep the target hidden before the learner answers.
""",
        },
    ]

