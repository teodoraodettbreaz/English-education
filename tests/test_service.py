from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from pathlex.llm import ScriptedTestProvider
from pathlex.service import PathLexService, normalize_spec_payload
from pathlex.player import PlayerError

from tests.helpers import (
    _json_after,
    engineering_responder,
    provider_factory,
    settings_for,
    story_payload,
)


class ServiceJourneyEngineeringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="pathlex-engineering-")
        self.root = Path(self.temporary.name)
        self.settings = settings_for(self.root)
        self.service = PathLexService(
            self.settings,
            provider_factory=provider_factory,
            background_workers=1,
        )

    def tearDown(self) -> None:
        self.service.close()
        self.temporary.cleanup()

    def test_normalization_accepts_the_bilingual_web_contract(self) -> None:
        normalized = normalize_spec_payload(story_payload(language="zh"), self.settings)
        self.assertEqual(normalized["depth"], 3)
        self.assertEqual(normalized["branch_factor"], 2)
        self.assertEqual(normalized["interface_language"], "zh")
        self.assertEqual(normalized["targets"][0]["mode_requirements"]["retrieval"], 1)
        self.assertEqual(normalized["targets"][0]["forbidden_patterns"], ["navigate a person"])
        self.assertEqual(normalized["safety_constraints"], ["No violence", "no stereotypes"])

    def test_compile_publish_and_play_complete_bilingual_journey(self) -> None:
        unit = self.service.create_unit(story_payload(), background=False)
        self.assertEqual(unit["status"], "VERIFIED")
        self.assertEqual(unit["audit"]["path_count"], 4)
        self.assertEqual(unit["audit"]["worst_path_coverage"], 1.0)
        self.assertTrue(unit["runtime"]["engineering_test_double"])
        unit = self.service.publish_unit(unit["id"])
        self.assertTrue(unit["published"])
        retrievals = [
            opportunity.get("retrieval", {})
            for node in unit["graph"]["nodes"].values()
            for opportunity in node.get("opportunities", [])
            if opportunity.get("mode") == "retrieval"
        ]
        self.assertTrue(retrievals)
        self.assertTrue(all("accepted_answers" not in item for item in retrievals))

        english = self.service.start_session(unit["id"], "en")
        self.assertEqual(english["language"], "en")
        self.assertEqual(english["node"]["support"], "Use the route clues before choosing.")
        self.assertEqual(len(english["node"]["choices"]), 2)

        english = self.service.choose(english["id"], english["node"]["choices"][0]["id"])
        self.assertIsNotNone(english["node"]["retrieval"])
        self.assertFalse(english["node"]["retrieval"]["answered"])
        english = self.service.answer(english["id"], "navigate")
        self.assertTrue(english["last_answer_correct"])
        self.assertIn("navigate", english["last_feedback"])
        self.assertTrue(english["node"]["retrieval"]["answered"])

        english = self.service.choose(english["id"], english["node"]["choices"][0]["id"])
        self.assertTrue(english["node"]["terminal"])
        self.assertFalse(english["completed"], "terminal prose must be visible before completion")
        self.assertIn("**navigate**", english["node"]["text"])
        english = self.service.complete_session(english["id"])
        self.assertTrue(english["completed"])
        with self.assertRaises(PlayerError):
            self.service.complete_session(english["id"])

        chinese = self.service.start_session(unit["id"], "zh")
        self.assertEqual(chinese["node"]["support"], "选择前请先利用路线线索。")
        self.assertTrue(chinese["node"]["choices"][0]["label"].startswith("选择路线"))
        switched = self.service.set_session_language(chinese["id"], "en")
        self.assertEqual(switched["language"], "en")
        self.assertEqual(switched["node"]["support"], "Use the route clues before choosing.")

    def test_persisted_counterexample_can_resume_transactional_repair(self) -> None:
        rejected_once = False

        def rejecting_responder(messages):
            nonlocal rejected_once
            response = engineering_responder(messages)
            if "conservative semantic verifier" in messages[0]["content"] and not rejected_once:
                payload = json.loads(response)
                if payload["verdicts"]:
                    payload["verdicts"][0]["label"] = "rejected"
                    payload["verdicts"][0]["sense_ok"] = False
                    payload["verdicts"][0]["reason"] = "ENGINEERING_TEST explicit defect"
                    rejected_once = True
                    return json.dumps(payload)
            return response

        def repair_responder(messages):
            if "transactional local story repairer" in messages[0]["content"]:
                current = _json_after(messages[-1]["content"], "Current node JSON:\n")
                return json.dumps(current, ensure_ascii=False)
            return engineering_responder(messages)

        factory_calls = 0

        def staged_factory():
            nonlocal factory_calls
            factory_calls += 1
            responder = rejecting_responder if factory_calls == 1 else repair_responder
            return ScriptedTestProvider(responder=responder)

        service = PathLexService(
            self.settings,
            provider_factory=staged_factory,
            background_workers=1,
        )
        try:
            with patch.dict(os.environ, {"PATHLEX_MAX_REPAIR_ROUNDS": "0"}):
                unit = service.create_unit(story_payload(), background=False)
            self.assertEqual(unit["status"], "COUNTEREXAMPLE")
            repaired = service.repair_unit(unit["id"])
            self.assertEqual(repaired["status"], "VERIFIED")
            self.assertTrue(
                any(item["committed"] for item in repaired["audit"]["repair_attempts"])
            )
        finally:
            service.close()


if __name__ == "__main__":
    unittest.main()
