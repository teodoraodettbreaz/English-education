from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from enum import StrEnum
from typing import Any, Mapping


class StoryStatus(StrEnum):
    DRAFT = "DRAFT"
    PLAN_FEASIBLE = "PLAN-FEASIBLE"
    PLAN_INFEASIBLE = "PLAN-INFEASIBLE(UNSAT)"
    VERIFIED = "VERIFIED"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    GENERATION_FAILURE = "GENERATION_FAILURE"
    UNKNOWN = "UNKNOWN"


class VerificationDecision(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"


class PracticeMode(StrEnum):
    EXPOSURE = "exposure"
    JUDGMENT = "judgment"
    RETRIEVAL = "retrieval"


class StoryPhase(StrEnum):
    OPENING = "opening"
    MIDDLE = "middle"
    ENDING = "ending"


def _plain(value: Any) -> Any:


    if isinstance(value, StrEnum):
        return str(value)
    if is_dataclass(value):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(item) for item in value]
    return value


@dataclass(slots=True)
class Serializable:
    def to_dict(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(slots=True)
class TargetConstraint(Serializable):
    id: str
    lemma: str
    sense: str
    part_of_speech: str
    allowed_collocations: list[str] = field(default_factory=list)
    forbidden_patterns: list[str] = field(default_factory=list)
    positive_examples: list[str] = field(default_factory=list)
    negative_examples: list[str] = field(default_factory=list)
    min_occurrences: int = 3
    min_gap: int = 0
    max_gap: int | None = None
    min_contexts: int = 1
    context_labels: list[str] = field(default_factory=lambda: ["general"])
    required_phases: list[StoryPhase] = field(default_factory=list)
    mode_requirements: dict[PracticeMode, int] = field(
        default_factory=lambda: {PracticeMode.EXPOSURE: 1, PracticeMode.RETRIEVAL: 1}
    )
    weight: float = 1.0

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.id.strip():
            errors.append("target.id is required")
        if not self.lemma.strip():
            errors.append(f"target {self.id!r}: lemma is required")
        if not self.sense.strip():
            errors.append(f"target {self.id!r}: a target sense/gloss is required")
        if not self.part_of_speech.strip():
            errors.append(f"target {self.id!r}: part_of_speech is required")
        if self.min_occurrences < 1:
            errors.append(f"target {self.id!r}: min_occurrences must be >= 1")
        if self.min_gap < 0:
            errors.append(f"target {self.id!r}: min_gap must be >= 0")
        if self.max_gap is not None and self.max_gap < self.min_gap:
            errors.append(f"target {self.id!r}: max_gap must be >= min_gap")
        if self.min_contexts < 1:
            errors.append(f"target {self.id!r}: min_contexts must be >= 1")
        if self.min_contexts > self.min_occurrences:
            errors.append(
                f"target {self.id!r}: min_contexts cannot exceed min_occurrences"
            )
        if self.min_contexts > len(set(self.context_labels)):
            errors.append(
                f"target {self.id!r}: min_contexts exceeds explicit context_labels"
            )
        mode_total = 0
        for mode, count in self.mode_requirements.items():
            if count < 0:
                errors.append(f"target {self.id!r}: mode count for {mode} is negative")
            mode_total += max(0, count)
        if mode_total > self.min_occurrences:
            errors.append(
                f"target {self.id!r}: required practice modes ({mode_total}) exceed "
                f"min_occurrences ({self.min_occurrences})"
            )
        if self.weight <= 0:
            errors.append(f"target {self.id!r}: weight must be positive")
        return errors

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TargetConstraint":
        modes = {
            PracticeMode(key): int(value)
            for key, value in dict(data.get("mode_requirements", {})).items()
        }
        phases = [StoryPhase(item) for item in data.get("required_phases", [])]
        return cls(
            id=str(data["id"]),
            lemma=str(data["lemma"]),
            sense=str(data.get("sense", "")),
            part_of_speech=str(data.get("part_of_speech", "")),
            allowed_collocations=list(data.get("allowed_collocations", [])),
            forbidden_patterns=list(data.get("forbidden_patterns", [])),
            positive_examples=list(data.get("positive_examples", [])),
            negative_examples=list(data.get("negative_examples", [])),
            min_occurrences=int(data.get("min_occurrences", 3)),
            min_gap=int(data.get("min_gap", 0)),
            max_gap=(
                None if data.get("max_gap") in (None, "") else int(data["max_gap"])
            ),
            min_contexts=int(data.get("min_contexts", 1)),
            context_labels=list(data.get("context_labels", ["general"])),
            required_phases=phases,
            mode_requirements=(
                modes
                if modes
                else {PracticeMode.EXPOSURE: 1, PracticeMode.RETRIEVAL: 1}
            ),
            weight=float(data.get("weight", 1.0)),
        )


@dataclass(slots=True)
class StorySpec(Serializable):
    id: str
    title: str
    cefr_level: str
    known_vocabulary: list[str]
    base_vocabulary: list[str]
    targets: list[TargetConstraint]
    theme: str
    safety_constraints: list[str] = field(default_factory=list)
    branch_factor: int = 2
    depth: int = 5
    max_paths: int = 64
    max_nodes: int = 255
    common_prefix_max_ratio: float = 0.5
    interface_language: str = "en"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.id.strip():
            errors.append("spec.id is required")
        if not self.title.strip():
            errors.append("spec.title is required")
        if self.cefr_level not in {"A1", "A2", "B1", "B2", "C1", "C2"}:
            errors.append("cefr_level must be one of A1, A2, B1, B2, C1, C2")
        if not self.theme.strip():
            errors.append("theme is required")
        if not self.targets:
            errors.append("at least one target lexical unit is required")
        target_ids = [item.id for item in self.targets]
        if len(target_ids) != len(set(target_ids)):
            errors.append("target ids must be unique")
        if self.branch_factor < 2 or self.branch_factor > 4:
            errors.append("branch_factor must be between 2 and 4")
        if self.depth < 3 or self.depth > 12:
            errors.append("depth must be between 3 and 12")
        if self.max_paths < 1:
            errors.append("max_paths must be positive")
        if self.max_nodes < self.depth:
            errors.append("max_nodes must be at least depth")
        if not 0 <= self.common_prefix_max_ratio <= 1:
            errors.append("common_prefix_max_ratio must be between 0 and 1")
        if self.interface_language not in {"en", "zh"}:
            errors.append("interface_language must be en or zh")
        for target in self.targets:
            errors.extend(target.validate())
        return errors

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StorySpec":
        return cls(
            id=str(data["id"]),
            title=str(data.get("title", "")),
            cefr_level=str(data.get("cefr_level", "B1")),
            known_vocabulary=list(data.get("known_vocabulary", [])),
            base_vocabulary=list(data.get("base_vocabulary", [])),
            targets=[TargetConstraint.from_dict(item) for item in data.get("targets", [])],
            theme=str(data.get("theme", "")),
            safety_constraints=list(data.get("safety_constraints", [])),
            branch_factor=int(data.get("branch_factor", 2)),
            depth=int(data.get("depth", 5)),
            max_paths=int(data.get("max_paths", 64)),
            max_nodes=int(data.get("max_nodes", 255)),
            common_prefix_max_ratio=float(data.get("common_prefix_max_ratio", 0.5)),
            interface_language=str(data.get("interface_language", "en")),
        )


@dataclass(slots=True)
class OpportunitySlot(Serializable):
    id: str
    target_id: str
    node_id: str
    occurrence_index: int
    mode: PracticeMode
    context_label: str
    phase: StoryPhase
    required_surface: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OpportunitySlot":
        return cls(
            id=str(data["id"]),
            target_id=str(data["target_id"]),
            node_id=str(data["node_id"]),
            occurrence_index=int(data["occurrence_index"]),
            mode=PracticeMode(data["mode"]),
            context_label=str(data["context_label"]),
            phase=StoryPhase(data["phase"]),
            required_surface=str(data.get("required_surface", "")),
        )


@dataclass(slots=True)
class Choice(Serializable):
    id: str
    target_node_id: str
    label_en: str = "Continue"
    label_zh: str = "继续"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Choice":
        return cls(
            id=str(data["id"]),
            target_node_id=str(data["target_node_id"]),
            label_en=str(data.get("label_en", "Continue")),
            label_zh=str(data.get("label_zh", "继续")),
        )


@dataclass(slots=True)
class RetrievalPrompt(Serializable):
    slot_id: str
    prompt_en: str
    prompt_zh: str
    accepted_answers: list[str]
    feedback_en: str
    feedback_zh: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RetrievalPrompt":
        return cls(
            slot_id=str(data["slot_id"]),
            prompt_en=str(data.get("prompt_en", "")),
            prompt_zh=str(data.get("prompt_zh", "")),
            accepted_answers=list(data.get("accepted_answers", [])),
            feedback_en=str(data.get("feedback_en", "")),
            feedback_zh=str(data.get("feedback_zh", "")),
        )


@dataclass(slots=True)
class StoryNode(Serializable):
    id: str
    depth: int
    phase: StoryPhase
    terminal: bool = False
    text: str = ""
    title: str = ""
    choices: list[Choice] = field(default_factory=list)
    slots: list[OpportunitySlot] = field(default_factory=list)
    retrieval_prompts: list[RetrievalPrompt] = field(default_factory=list)
    plot_state: dict[str, Any] = field(default_factory=dict)
    version: int = 0
    verification_stale: bool = True

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StoryNode":
        return cls(
            id=str(data["id"]),
            depth=int(data.get("depth", 0)),
            phase=StoryPhase(data.get("phase", StoryPhase.OPENING)),
            terminal=bool(data.get("terminal", False)),
            text=str(data.get("text", "")),
            title=str(data.get("title", "")),
            choices=[Choice.from_dict(item) for item in data.get("choices", [])],
            slots=[OpportunitySlot.from_dict(item) for item in data.get("slots", [])],
            retrieval_prompts=[
                RetrievalPrompt.from_dict(item) for item in data.get("retrieval_prompts", [])
            ],
            plot_state=dict(data.get("plot_state", {})),
            version=int(data.get("version", 0)),
            verification_stale=bool(data.get("verification_stale", True)),
        )


@dataclass(slots=True)
class PlanCertificate(Serializable):
    status: StoryStatus
    reason_codes: list[str]
    explanation: str
    selected_depths: dict[str, list[int]] = field(default_factory=dict)
    requirements: dict[str, Any] = field(default_factory=dict)
    witness: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PlanCertificate":
        return cls(
            status=StoryStatus(data["status"]),
            reason_codes=list(data.get("reason_codes", [])),
            explanation=str(data.get("explanation", "")),
            selected_depths={
                str(key): [int(item) for item in values]
                for key, values in dict(data.get("selected_depths", {})).items()
            },
            requirements=dict(data.get("requirements", {})),
            witness=dict(data.get("witness", {})),
        )


@dataclass(slots=True)
class VerifiedOpportunity(Serializable):
    slot_id: str
    target_id: str
    node_id: str
    decision: VerificationDecision
    confidence: float
    observed_mode: PracticeMode
    observed_context: str
    observed_phase: StoryPhase
    reason: str = ""
    checks: dict[str, bool | None] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "VerifiedOpportunity":
        return cls(
            slot_id=str(data["slot_id"]),
            target_id=str(data["target_id"]),
            node_id=str(data["node_id"]),
            decision=VerificationDecision(data["decision"]),
            confidence=float(data.get("confidence", 0.0)),
            observed_mode=PracticeMode(data.get("observed_mode", PracticeMode.EXPOSURE)),
            observed_context=str(data.get("observed_context", "")),
            observed_phase=StoryPhase(data.get("observed_phase", StoryPhase.MIDDLE)),
            reason=str(data.get("reason", "")),
            checks=dict(data.get("checks", {})),
        )


@dataclass(slots=True)
class ConstraintCheck(Serializable):
    id: str
    target_id: str
    kind: str
    satisfied: bool
    weight: float
    detail: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ConstraintCheck":
        return cls(
            id=str(data["id"]),
            target_id=str(data["target_id"]),
            kind=str(data["kind"]),
            satisfied=bool(data["satisfied"]),
            weight=float(data["weight"]),
            detail=str(data.get("detail", "")),
        )


@dataclass(slots=True)
class PathAudit(Serializable):
    path: list[str]
    coverage: float
    passed: bool
    checks: list[ConstraintCheck]
    debts: list[dict[str, Any]] = field(default_factory=list)
    uncertain_slots: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PathAudit":
        return cls(
            path=list(data.get("path", [])),
            coverage=float(data.get("coverage", 0.0)),
            passed=bool(data.get("passed", False)),
            checks=[ConstraintCheck.from_dict(item) for item in data.get("checks", [])],
            debts=list(data.get("debts", [])),
            uncertain_slots=list(data.get("uncertain_slots", [])),
        )


@dataclass(slots=True)
class AuditReport(Serializable):
    status: StoryStatus
    worst_path: list[str]
    worst_coverage: float
    path_pass_ratio: float
    path_audits: list[PathAudit]
    counterexample: dict[str, Any] | None = None
    unknown_reasons: list[str] = field(default_factory=list)
    graph_version: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AuditReport":
        return cls(
            status=StoryStatus(data["status"]),
            worst_path=list(data.get("worst_path", [])),
            worst_coverage=float(data.get("worst_coverage", 0.0)),
            path_pass_ratio=float(data.get("path_pass_ratio", 0.0)),
            path_audits=[PathAudit.from_dict(item) for item in data.get("path_audits", [])],
            counterexample=data.get("counterexample"),
            unknown_reasons=list(data.get("unknown_reasons", [])),
            graph_version=int(data.get("graph_version", 0)),
        )


@dataclass(slots=True)
class StoryGraph(Serializable):
    id: str
    spec_id: str
    root_id: str
    nodes: dict[str, StoryNode]
    status: StoryStatus = StoryStatus.DRAFT
    plan_certificate: PlanCertificate | None = None
    audit_report: AuditReport | None = None
    version: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StoryGraph":
        return cls(
            id=str(data["id"]),
            spec_id=str(data["spec_id"]),
            root_id=str(data["root_id"]),
            nodes={
                str(key): StoryNode.from_dict(value)
                for key, value in dict(data.get("nodes", {})).items()
            },
            status=StoryStatus(data.get("status", StoryStatus.DRAFT)),
            plan_certificate=(
                PlanCertificate.from_dict(data["plan_certificate"])
                if data.get("plan_certificate")
                else None
            ),
            audit_report=(
                AuditReport.from_dict(data["audit_report"])
                if data.get("audit_report")
                else None
            ),
            version=int(data.get("version", 0)),
            metadata=dict(data.get("metadata", {})),
        )


def accepted_fields(instance_type: type[Serializable]) -> set[str]:


    return {item.name for item in fields(instance_type)}

