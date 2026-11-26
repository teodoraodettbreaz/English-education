from __future__ import annotations

import unittest

from pathlex.audit import audit_story
from pathlex.generator import GeneratedNode
from pathlex.llm import ScriptedTestProvider
from pathlex.models import (
    PracticeMode,
    StoryPhase,
    StorySpec,
    StoryStatus,
    VerificationDecision,
    VerifiedOpportunity,
)
from pathlex.planner import plan_story
from pathlex.repair import TransactionalRepairer
from pathlex.verifier import SemanticVerifier


def _spec(*, occurrences: int = 2) -> StorySpec:
    return StorySpec.from_dict(
        {
            "id": "ENGINEERING-CORE",
            "title": "Engineering fixture",
            "cefr_level": "B1",
            "known_vocabulary": ["route"],
            "base_vocabulary": ["the"],
            "theme": "A route puzzle",
            "branch_factor": 2,
            "depth": 3,
            "max_paths": 4,
            "max_nodes": 32,
            "common_prefix_max_ratio": 0.5,
            "interface_language": "en",
            "targets": [
                {
                    "id": "target-1",
                    "lemma": "navigate",
                    "sense": "find or plan a route",
                    "part_of_speech": "verb",
                    "min_occurrences": occurrences,
                    "min_gap": 0,
                    "max_gap": 0,
                    "min_contexts": min(occurrences, 2),
                    "context_labels": ["route", "directions"],
                    "mode_requirements": {"retrieval": 1, "exposure": 1},
                }
            ],
        }
    )


class PlannerAndAuditEngineeringTests(unittest.TestCase):
    def test_finite_plan_and_conservative_audit_states(self) -> None:
        spec = _spec()
        plan = plan_story(spec)
        self.assertEqual(plan.certificate.status, StoryStatus.PLAN_FEASIBLE)
        self.assertIsNotNone(plan.graph)
        graph = plan.graph
        assert graph is not None
        verifications: list[VerifiedOpportunity] = []
        for node in graph.nodes.values():
            node.verification_stale = False
            for slot in node.slots:
                verifications.append(
                    VerifiedOpportunity(
                        slot_id=slot.id,
                        target_id=slot.target_id,
                        node_id=node.id,
                        decision=VerificationDecision.ACCEPTED,
                        confidence=0.99,
                        observed_mode=slot.mode,
                        observed_context=slot.context_label,
                        observed_phase=slot.phase,
                        checks={
                            "sense": True,
                            "part_of_speech": True,
                            "pattern": True,
                            "grammar": True,
                            "context": True,
                            "mode": True,
                        },
                    )
                )
        verified = audit_story(spec, graph, verifications)
        self.assertEqual(verified.status, StoryStatus.VERIFIED)
        self.assertEqual(len(verified.path_audits), 4)
        self.assertEqual(verified.path_pass_ratio, 1.0)

        unresolved = audit_story(spec, graph, verifications[:-1])
        self.assertEqual(unresolved.status, StoryStatus.UNKNOWN)
        rejected_records = list(verifications)
        last = rejected_records[-1]
        rejected_records[-1] = VerifiedOpportunity(
            slot_id=last.slot_id,
            target_id=last.target_id,
            node_id=last.node_id,
            decision=VerificationDecision.REJECTED,
            confidence=0.99,
            observed_mode=PracticeMode.EXPOSURE,
            observed_context=last.observed_context,
            observed_phase=StoryPhase.ENDING,
            reason="ENGINEERING_TEST explicit rejection",
            checks={"sense": False},
        )
        counterexample = audit_story(spec, graph, rejected_records)
        self.assertEqual(counterexample.status, StoryStatus.COUNTEREXAMPLE)
        self.assertTrue(counterexample.counterexample)

    def test_unsatisfiable_depth_returns_certificate_without_model_call(self) -> None:
        plan = plan_story(_spec(occurrences=3))
        self.assertEqual(plan.certificate.status, StoryStatus.PLAN_INFEASIBLE)
        self.assertIn("INSUFFICIENT_DISTINCT_DEPTHS", plan.certificate.reason_codes)

    def test_malformed_verifier_values_fail_closed(self) -> None:
        verifier = SemanticVerifier(ScriptedTestProvider(responses=[]))
        slot = {"id": "slot-1", "target_id": "target-1"}
        raw = {
            "slot_id": "slot-1",
            "target_id": "target-1",
            "label": "accepted",
            "confidence": float("nan"),
            "sense_ok": "false",
            "pos_ok": "false",
            "pattern_ok": "false",
            "grammar_ok": "false",
            "context_ok": "false",
            "mode_ok": "false",
        }
        verdict = verifier._normalize_verdict(raw, slot)
        self.assertEqual(verdict.label, "uncertain")
        self.assertEqual(verdict.confidence, 0.0)
        self.assertFalse(any((verdict.sense_ok, verdict.pos_ok, verdict.mode_ok)))

    def test_realized_slot_must_match_the_planned_dimensions(self) -> None:
        planned = {
            "id": "slot-1",
            "target_id": "target-1",
            "required_surface": "navigate",
            "mode": "retrieval",
            "context_label": "travel",
            "phase": "middle",
        }
        node = GeneratedNode.from_payload(
            {
                "node_id": "n1",
                "title": "Engineering mismatch",
                "story_markdown": "We **navigate** the route.",
                "support": {"en": "Help", "zh": "提示"},
                "plot_state": {},
                "choices": [],
                "opportunities": [
                    {
                        "slot_id": "slot-1",
                        "target_id": "WRONG",
                        "surface": "navigate",
                        "mode": "exposure",
                        "context": "WRONG",
                        "phase": "opening",
                        "evidence_span": "navigate",
                        "retrieval": {},
                    }
                ],
                "safety_notes": [],
            },
            expected_id="n1",
            depth=1,
            expected_next_ids=[],
            planned_slots=[planned],
        )
        self.assertTrue(node.structural_errors)
        self.assertTrue(any("does not match planned" in item for item in node.structural_errors))

    def test_repair_reuses_a_rejected_planned_slot_instead_of_duplicating_it(self) -> None:
        slots = [{"id": "slot-1", "slot_id": "slot-1", "target_id": "target-1"}]
        debts = [
            {
                "target_id": "target-1",
                "kind": "occurrences",
                "rejected_slots": ["slot-1"],
            }
        ]
        TransactionalRepairer._attach_debt_slots(slots, debts, 1, "n1")
        self.assertEqual([item["id"] for item in slots], ["slot-1"])


if __name__ == "__main__":
    unittest.main()
