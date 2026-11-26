from __future__ import annotations

import os
import copy
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

from .bridge import audit_generated_story, repair_audit_payload
from .config import Settings
from .generator import GeneratedStory, PathLexGenerator
from .llm import (
    BudgetedProvider,
    CallBudget,
    LLMConfigurationError,
    LLMError,
    LLMProvider,
    QwenProvider,
)
from .models import PracticeMode, StorySpec, StoryStatus
from .planner import plan_story
from .player import (
    PlayerError,
    choose,
    initial_state,
    root_node_id,
    session_view,
    submit_answer,
)
from .repair import TransactionalRepairer
from .storage import ConflictError, NotFoundError, Repository
from .verifier import SemanticVerifier


class InputError(ValueError):
    def __init__(self, message: str, *, details: list[str] | None = None):
        super().__init__(message)
        self.details = details or []


ProviderFactory = Callable[[], LLMProvider]


def _env_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        normalized = value.replace("\r", "\n").replace("，", ",").replace("；", ";")
        pieces: list[str] = []
        for line in normalized.split("\n"):
            pieces.extend(line.replace(";", ",").split(","))
        return list(dict.fromkeys(item.strip() for item in pieces if item.strip()))
    if isinstance(value, (list, tuple, set)):
        return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))
    return [str(value).strip()] if str(value).strip() else []


def _int(value: Any, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise InputError(f"Expected an integer, received {value!r}") from exc


def normalize_spec_payload(payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InputError("The story specification must be a JSON object")
    targets_raw = payload.get("targets")
    if not isinstance(targets_raw, list) or not targets_raw:
        raise InputError("Add at least one target lexical unit")
    graph_raw = payload.get("graph")
    if not isinstance(graph_raw, dict):
        graph_raw = {}
    targets: list[dict[str, Any]] = []
    for index, raw in enumerate(targets_raw):
        if not isinstance(raw, dict):
            raise InputError(f"Target {index + 1} must be an object")
        lemma = str(raw.get("lemma") or raw.get("word") or "").strip()
        target_id = str(raw.get("id") or f"target-{index + 1}").strip()
        min_occurrences = _int(
            raw.get("min_occurrences", raw.get("occurrences")), 3
        )
        provided_modes = raw.get("mode_requirements") or raw.get("mode_counts")
        if isinstance(provided_modes, dict):
            modes = {
                str(key): _int(value, 0)
                for key, value in provided_modes.items()
                if str(key) in {mode.value for mode in PracticeMode}
            }
        else:
            modes = {
                "exposure": _int(raw.get("exposure_count"), max(0, min_occurrences - 1)),
                "judgment": _int(raw.get("judgment_count"), 0),
                "retrieval": _int(raw.get("retrieval_count"), 1),
            }
        contexts = _string_list(raw.get("context_labels") or raw.get("contexts")) or [
            "general"
        ]
        targets.append(
            {
                "id": target_id,
                "lemma": lemma,
                "sense": str(raw.get("sense") or raw.get("meaning") or "").strip(),
                "part_of_speech": str(
                    raw.get("part_of_speech") or raw.get("pos") or ""
                ).strip(),
                "allowed_collocations": _string_list(
                    raw.get("allowed_collocations") or raw.get("collocations")
                ),
                "forbidden_patterns": _string_list(
                    raw.get("forbidden_patterns") or raw.get("forbidden_collocations")
                ),
                "positive_examples": _string_list(
                    raw.get("positive_examples") or raw.get("examples")
                ),
                "negative_examples": _string_list(raw.get("negative_examples")),
                "min_occurrences": min_occurrences,
                "min_gap": _int(raw.get("min_gap"), 0),
                "max_gap": (
                    None
                    if raw.get("max_gap") in (None, "")
                    else _int(raw.get("max_gap"), 0)
                ),
                "min_contexts": _int(raw.get("min_contexts"), min(2, len(contexts))),
                "context_labels": contexts,
                "required_phases": [
                    item.lower() for item in _string_list(raw.get("required_phases"))
                ],
                "mode_requirements": modes,
                "weight": float(raw.get("weight", 1.0)),
            }
        )
    depth = _int(
        payload.get("depth", payload.get("max_depth", graph_raw.get("depth"))), 5
    )
    common_prefix_ratio = payload.get(
        "common_prefix_max_ratio",
        graph_raw.get(
            "common_prefix_max_ratio",
            graph_raw.get("common_prefix_opportunity_limit", 0.5),
        ),
    )
    return {
        "id": str(payload.get("id") or f"spec-{uuid.uuid4().hex[:12]}"),
        "title": str(payload.get("title") or "").strip(),
        "cefr_level": str(payload.get("cefr_level") or payload.get("cefr") or "B1").upper(),
        "known_vocabulary": _string_list(
            payload.get("known_vocabulary") or payload.get("known_words")
        ),
        "base_vocabulary": _string_list(
            payload.get("base_vocabulary") or payload.get("base_words")
        ),
        "targets": targets,
        "theme": str(payload.get("theme") or "").strip(),
        "safety_constraints": _string_list(
            payload.get("safety_constraints") or payload.get("safety_notes")
        ),
        "branch_factor": _int(
            payload.get("branch_factor", graph_raw.get("branch_factor")), 2
        ),
        "depth": depth,
        "max_paths": min(
            _int(payload.get("max_paths", graph_raw.get("max_paths")), settings.max_paths),
            settings.max_paths,
        ),
        "max_nodes": min(
            _int(payload.get("max_nodes", graph_raw.get("max_nodes")), settings.max_nodes),
            settings.max_nodes,
        ),
        "common_prefix_max_ratio": float(common_prefix_ratio),
        "interface_language": "zh" if payload.get("interface_language") == "zh" else "en",
    }


def _default_provider() -> LLMProvider:
    provider = QwenProvider.from_env()
    max_total = _env_int("PATHLEX_MAX_TOTAL_TOKENS", 80_000)
    return BudgetedProvider(
        provider,
        CallBudget(
            max_calls=_env_int("PATHLEX_MAX_LLM_CALLS", 128),
            max_input_tokens=max_total,
            max_output_tokens=max_total,
            max_total_tokens=max_total,
        ),
    )


class PathLexService:
    def __init__(
        self,
        settings: Settings,
        repository: Repository | None = None,
        provider_factory: ProviderFactory | None = None,
        *,
        background_workers: int = 2,
    ) -> None:
        self.settings = settings
        self.repository = repository or Repository(settings.database_path)
        self.provider_factory = provider_factory or _default_provider
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, background_workers), thread_name_prefix="pathlex-compile"
        )
        self._futures: dict[str, Future[None]] = {}
        self._futures_lock = threading.Lock()

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=False)

    def health(self) -> dict[str, Any]:
        configured = bool(os.getenv("PATHLEX_LLM_API_KEY") or os.getenv("V_API_KEY"))
        with self._futures_lock:
            active = sum(not future.done() for future in self._futures.values())
        return {
            "status": "ok",
            "llm_configured": configured,
            "model": os.getenv("PATHLEX_LLM_MODEL", "qwen3.7-flash"),
            "active_compilations": active,
            "schema_version": 1,
        }

    def create_unit(self, payload: dict[str, Any], *, background: bool = True) -> dict[str, Any]:
        normalized = normalize_spec_payload(payload, self.settings)
        try:
            spec = StorySpec.from_dict(normalized)
        except (KeyError, TypeError, ValueError) as exc:
            raise InputError(f"The story specification could not be parsed: {exc}") from exc
        errors = spec.validate()
        if errors:
            raise InputError("The story specification is not valid", details=errors)
        unit = self.repository.create_unit(normalized, status="QUEUED")
        if background:
            self._submit(unit["id"], self._compile_guarded)
        else:
            self._compile_guarded(unit["id"])
        return self._public_unit(self.repository.get_unit(unit["id"]))

    def _submit(self, unit_id: str, worker: Callable[[str], None]) -> None:
        with self._futures_lock:
            existing = self._futures.get(unit_id)
            if existing is not None and not existing.done():
                raise ConflictError("This unit already has an active compilation")
            future = self._executor.submit(worker, unit_id)
            self._futures[unit_id] = future

    def _compile_guarded(self, unit_id: str) -> None:
        try:
            self._compile(unit_id)
        except Exception as exc:
            self.repository.update_unit(
                unit_id,
                status="UNKNOWN",
                error={
                    "code": "COMPILATION_FAILED",
                    "message": str(exc)[:1200],
                },
            )

    def _compile(self, unit_id: str) -> None:
        unit = self.repository.update_unit(unit_id, status="PLANNING", clear_error=True)
        spec = StorySpec.from_dict(unit["spec"])
        plan = plan_story(spec)
        certificate = plan.certificate.to_dict()
        if plan.graph is None or plan.certificate.status is StoryStatus.PLAN_INFEASIBLE:
            self.repository.update_unit(
                unit_id,
                status=str(plan.certificate.status),
                audit={"plan_certificate": certificate},
                error={
                    "code": "PLAN_INFEASIBLE",
                    "message": plan.certificate.explanation,
                    "details": plan.certificate.reason_codes,
                },
            )
            return
        planned_graph = plan.graph
        self.repository.update_unit(
            unit_id,
            status="GENERATING",
            audit={"plan_certificate": certificate},
        )
        try:
            provider = self.provider_factory()
        except LLMConfigurationError as exc:
            self.repository.update_unit(
                unit_id,
                status="UNKNOWN",
                audit={"plan_certificate": certificate},
                error={"code": "LLM_NOT_CONFIGURED", "message": str(exc)},
            )
            return

        generator = PathLexGenerator(
            provider,
            temperature=_env_float("PATHLEX_LLM_TEMPERATURE", 0.2),
            max_tokens_per_node=_env_int("PATHLEX_LLM_MAX_TOKENS", 4096),
        )
        generated = generator.generate(
            spec.to_dict(), planned_graph, interface_language=spec.interface_language
        )
        story = generated.story
        if story.status == "GENERATION_FAILURE":
            audit = audit_generated_story(spec, planned_graph, story)
            self.repository.update_unit(
                unit_id,
                status=str(audit.status),
                graph=story.to_dict(),
                audit=self._audit_payload(certificate, audit),
                runtime=self._runtime(provider, generated.generated_node_count, []),
                error={
                    "code": "GENERATION_FAILURE",
                    "message": "; ".join(story.errors)[:1200],
                },
            )
            return

        self.repository.update_unit(unit_id, status="VERIFYING", graph=story.to_dict())
        verifier = SemanticVerifier(
            provider,
            acceptance_threshold=_env_float("PATHLEX_VERIFIER_ACCEPT_THRESHOLD", 0.95),
        )
        verification = verifier.verify_story(spec.to_dict(), story)
        audit = audit_generated_story(spec, planned_graph, story)
        repair_attempts: list[dict[str, Any]] = []
        if audit.status is StoryStatus.COUNTEREXAMPLE and _env_int(
            "PATHLEX_MAX_REPAIR_ROUNDS", 3
        ):
            repairer = TransactionalRepairer(
                provider,
                verifier,
                max_rounds=_env_int("PATHLEX_MAX_REPAIR_ROUNDS", 3),
            )
            outcome = repairer.repair(
                spec.to_dict(),
                story,
                lambda candidate: repair_audit_payload(spec, planned_graph, candidate),
                interface_language=spec.interface_language,
            )
            story = outcome.story
            repair_attempts = [attempt.to_dict() for attempt in outcome.attempts]
            audit = audit_generated_story(spec, planned_graph, story)

        runtime = self._runtime(provider, generated.generated_node_count, repair_attempts)
        error: dict[str, Any] | None = None
        if audit.status is StoryStatus.UNKNOWN:
            error = {
                "code": "VERIFICATION_UNKNOWN",
                "message": "One or more generated opportunities could not be verified.",
                "details": audit.unknown_reasons,
            }
        elif audit.status is StoryStatus.COUNTEREXAMPLE:
            error = {
                "code": "COUNTEREXAMPLE",
                "message": "At least one reachable path still has lexical opportunity debt.",
            }
        self.repository.update_unit(
            unit_id,
            status=str(audit.status),
            graph=story.to_dict(),
            audit=self._audit_payload(
                certificate,
                audit,
                story=story,
                repair_attempts=repair_attempts,
            ),
            runtime=runtime,
            error=error,
            clear_error=error is None,
        )

    @staticmethod
    def _audit_payload(
        certificate: dict[str, Any],
        audit: Any,
        *,
        story: GeneratedStory | None = None,
        repair_attempts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:


        payload = {"plan_certificate": certificate, **audit.to_dict()}
        payload.update(
            {
                "worst_path_coverage": audit.worst_coverage,
                "path_pass_rate": audit.path_pass_ratio,
                "path_count": len(audit.path_audits),
                "debts": list((audit.counterexample or {}).get("debts") or []),
            }
        )
        if story is not None:
            payload["verification"] = PathLexService._verification_snapshot(story)
        if repair_attempts is not None:
            payload["repair_attempts"] = repair_attempts
        return payload

    def repair_unit(self, unit_id: str) -> dict[str, Any]:


        unit = self.repository.get_unit(unit_id)
        if unit["published"]:
            raise ConflictError("Published units are immutable; create a new draft to revise it")
        if unit["status"] != "COUNTEREXAMPLE" or not unit.get("graph"):
            raise ConflictError("Only an unpublished COUNTEREXAMPLE can be repaired")
        try:
            provider = self.provider_factory()
        except LLMConfigurationError as exc:
            raise ConflictError(str(exc)) from exc
        spec = StorySpec.from_dict(unit["spec"])
        plan = plan_story(spec)
        if plan.graph is None or plan.certificate.status is StoryStatus.PLAN_INFEASIBLE:
            raise ConflictError("The frozen specification no longer has a feasible slot plan")
        story = GeneratedStory.from_dict(unit["graph"])
        certificate = plan.certificate.to_dict()
        self.repository.transition_unit_status(
            unit_id,
            expected="COUNTEREXAMPLE",
            status="VERIFYING",
            clear_error=True,
        )
        try:
            verifier = SemanticVerifier(
                provider,
                acceptance_threshold=_env_float("PATHLEX_VERIFIER_ACCEPT_THRESHOLD", 0.95),
            )
            repairer = TransactionalRepairer(
                provider,
                verifier,
                max_rounds=max(1, _env_int("PATHLEX_MAX_REPAIR_ROUNDS", 3)),
            )
            outcome = repairer.repair(
                spec.to_dict(),
                story,
                lambda candidate: repair_audit_payload(spec, plan.graph, candidate),
                interface_language=spec.interface_language,
            )
            story = outcome.story
            audit = audit_generated_story(spec, plan.graph, story)
            attempts = [attempt.to_dict() for attempt in outcome.attempts]
        except Exception as exc:
            self.repository.update_unit(
                unit_id,
                status="UNKNOWN",
                error={
                    "code": "REPAIR_FAILED",
                    "message": str(exc)[:1200],
                },
            )
            raise
        error: dict[str, Any] | None = None
        if audit.status is StoryStatus.UNKNOWN:
            error = {
                "code": "VERIFICATION_UNKNOWN",
                "message": "The repaired snapshot could not be fully verified.",
                "details": audit.unknown_reasons,
            }
        elif audit.status is StoryStatus.COUNTEREXAMPLE:
            error = {
                "code": "COUNTEREXAMPLE",
                "message": "The attempted patch was rolled back or path debt remains.",
            }
        self.repository.update_unit(
            unit_id,
            status=str(audit.status),
            graph=story.to_dict(),
            audit=self._audit_payload(
                certificate,
                audit,
                story=story,
                repair_attempts=attempts,
            ),
            runtime=self._runtime(provider, len(story.nodes), attempts),
            error=error,
            clear_error=error is None,
        )
        return self._public_unit(self.repository.get_unit(unit_id))

    @staticmethod
    def _runtime(
        provider: LLMProvider, generated_nodes: int, repair_attempts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        budget = provider.budget.to_dict() if isinstance(provider, BudgetedProvider) else {}
        return {
            "provider_model": getattr(provider, "model", "unknown"),
            "engineering_test_double": bool(getattr(provider, "is_test_double", False))
            or bool(getattr(getattr(provider, "provider", None), "is_test_double", False)),
            "generated_node_count": generated_nodes,
            "budget": budget,
            "repair_attempts": repair_attempts,
        }

    @staticmethod
    def _verification_snapshot(story: Any) -> dict[str, Any]:


        nodes: dict[str, Any] = {}
        rejected = 0
        uncertain = 0
        statuses: set[str] = set()
        for node_id, value in story.verifications.items():
            payload = value.to_dict() if hasattr(value, "to_dict") else dict(value)
            nodes[node_id] = payload
            statuses.add(str(payload.get("status") or "UNKNOWN"))
            for verdict in payload.get("verdicts") or []:
                label = str(verdict.get("label") or "uncertain")
                rejected += int(label == "rejected")
                uncertain += int(label == "uncertain")
        if len(nodes) < len(story.nodes) or "UNKNOWN" in statuses:
            status = "UNKNOWN"
        elif "COUNTEREXAMPLE" in statuses:
            status = "COUNTEREXAMPLE"
        else:
            status = "VERIFIED"
        return {
            "status": status,
            "nodes": nodes,
            "rejected_count": rejected,
            "uncertain_count": uncertain,
        }

    @staticmethod
    def _unit_summary(unit: dict[str, Any]) -> dict[str, Any]:
        spec = unit.get("spec") or {}
        audit = unit.get("audit") or {}
        return {
            "id": unit["id"],
            "title": unit["title"],
            "status": unit["status"],
            "published": unit["published"],
            "cefr_level": spec.get("cefr_level"),
            "theme": spec.get("theme"),
            "targets": [item.get("lemma") for item in spec.get("targets", [])],
            "node_count": len((unit.get("graph") or {}).get("nodes", {})),
            "worst_coverage": audit.get("worst_coverage"),
            "worst_path_coverage": audit.get("worst_path_coverage"),
            "path_pass_ratio": audit.get("path_pass_ratio"),
            "path_pass_rate": audit.get("path_pass_rate"),
            "path_count": audit.get("path_count"),
            "updated_at": unit["updated_at"],
            "error": unit.get("error"),
        }

    def list_units(self) -> list[dict[str, Any]]:
        return [self._unit_summary(unit) for unit in self.repository.list_units()]

    def get_unit(self, unit_id: str) -> dict[str, Any]:
        return self._public_unit(self.repository.get_unit(unit_id))

    def publish_unit(self, unit_id: str) -> dict[str, Any]:
        return self._public_unit(self.repository.publish_unit(unit_id))

    def library(self) -> list[dict[str, Any]]:
        return [self._unit_summary(unit) for unit in self.repository.list_library()]

    @staticmethod
    def _public_unit(unit: dict[str, Any]) -> dict[str, Any]:


        public = copy.deepcopy(unit)
        graph = public.get("graph") or {}
        nodes = graph.get("nodes") or {}
        if isinstance(nodes, dict):
            for node in nodes.values():
                if not isinstance(node, dict):
                    continue
                for opportunity in node.get("opportunities") or []:
                    if not isinstance(opportunity, dict):
                        continue
                    retrieval = opportunity.get("retrieval")
                    if isinstance(retrieval, dict):
                        retrieval.pop("accepted_answers", None)
                        retrieval.pop("feedback_en", None)
                        retrieval.pop("feedback_zh", None)
                        retrieval.pop("expected_display", None)
        return public

    def start_session(self, unit_id: str, language: str) -> dict[str, Any]:
        unit = self.repository.get_unit(unit_id)
        graph = unit.get("graph") or {}
        root = root_node_id(graph)
        session = self.repository.create_session(unit_id, language, root, initial_state(root))
        return session_view(unit, session)

    def get_session(self, session_id: str) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        unit = self.repository.get_unit(session["unit_id"])
        return session_view(unit, session)

    def set_session_language(self, session_id: str, language: str) -> dict[str, Any]:
        session = self.repository.update_session_language(session_id, language)
        unit = self.repository.get_unit(session["unit_id"])
        return session_view(unit, session)

    def answer(self, session_id: str, answer: str) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        unit = self.repository.get_unit(session["unit_id"])
        state, event = submit_answer(unit["graph"], session, answer)
        session = self.repository.update_session(
            session_id,
            current_node_id=session["current_node_id"],
            state=state,
            completed=False,
            event_type="retrieval_answered",
            event_payload=event,
        )
        return session_view(unit, session)

    def choose(self, session_id: str, choice_id: str) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        unit = self.repository.get_unit(session["unit_id"])
        next_id, state, completed, event = choose(unit["graph"], session, choice_id)
        session = self.repository.update_session(
            session_id,
            current_node_id=next_id,
            state=state,
            completed=completed,
            event_type="choice_selected",
            event_payload=event,
        )
        return session_view(unit, session)

    def complete_session(self, session_id: str) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        if session.get("completed"):
            raise PlayerError("This story session is already complete")
        unit = self.repository.get_unit(session["unit_id"])
        graph = unit.get("graph") or {}
        nodes = graph.get("nodes") or {}
        node = nodes.get(session["current_node_id"]) if isinstance(nodes, dict) else None
        if not isinstance(node, dict) or node.get("choices"):
            raise PlayerError("The current story node is not a terminal ending")
        state = session.get("state") or {}
        retrievals = node.get("opportunities") or []
        required = {
            str(item.get("slot_id") or "")
            for item in retrievals
            if isinstance(item, dict) and item.get("mode") == "retrieval"
        }
        if required - set(state.get("answered_slots") or []):
            raise PlayerError("Answer the vocabulary prompt before finishing the story")
        session = self.repository.update_session(
            session_id,
            current_node_id=session["current_node_id"],
            state=state,
            completed=True,
            event_type="session_completed",
            event_payload={"node_id": session["current_node_id"]},
        )
        return session_view(unit, session)


__all__ = [
    "ConflictError",
    "InputError",
    "NotFoundError",
    "PathLexService",
    "PlayerError",
    "normalize_spec_payload",
]

