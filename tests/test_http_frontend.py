from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from pathlex.service import PathLexService
from pathlex.web import PathLexHTTPServer

from tests.helpers import provider_factory, settings_for, story_payload


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def json_request(url: str, *, method: str = "GET", payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read())


class HttpAndFrontendEngineeringTests(unittest.TestCase):
    def test_home_health_and_security_headers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pathlex-http-engineering-") as directory:
            service = PathLexService(
                settings_for(Path(directory)),
                provider_factory=provider_factory,
                background_workers=1,
            )
            server = PathLexHTTPServer(("127.0.0.1", 0), service)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                with urlopen(base + "/", timeout=5) as response:
                    html = response.read().decode("utf-8")
                    self.assertIn('<html lang="en">', html)
                    self.assertIn("English", html)
                    self.assertIn("中文", html)
                    self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
                with urlopen(base + "/api/health", timeout=5) as response:
                    health = json.loads(response.read())
                    self.assertEqual(health["status"], "ok")
                    self.assertEqual(health["schema_version"], 1)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()
                service.close()

    def test_http_authoring_publish_session_and_language_routes_connect(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pathlex-http-journey-") as directory:
            service = PathLexService(
                settings_for(Path(directory)),
                provider_factory=provider_factory,
                background_workers=1,
            )
            server = PathLexHTTPServer(("127.0.0.1", 0), service)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                status, created = json_request(
                    base + "/api/units", method="POST", payload=story_payload()
                )
                self.assertEqual(status, 202)
                unit_id = created["id"]
                deadline = time.monotonic() + 5
                unit = created
                while unit["status"] not in {
                    "VERIFIED",
                    "COUNTEREXAMPLE",
                    "UNKNOWN",
                    "GENERATION_FAILURE",
                    "PLAN-INFEASIBLE(UNSAT)",
                } and time.monotonic() < deadline:
                    time.sleep(0.02)
                    _, unit = json_request(base + f"/api/units/{unit_id}")
                self.assertEqual(unit["status"], "VERIFIED")
                _, published = json_request(
                    base + f"/api/units/{unit_id}/publish", method="POST", payload={}
                )
                self.assertTrue(published["published"])
                status, session = json_request(
                    base + "/api/sessions",
                    method="POST",
                    payload={"unit_id": unit_id, "interface_language": "zh"},
                )
                self.assertEqual(status, 201)
                self.assertEqual(session["language"], "zh")
                _, switched = json_request(
                    base + f"/api/sessions/{session['id']}/language",
                    method="POST",
                    payload={"interface_language": "en"},
                )
                self.assertEqual(switched["language"], "en")
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()
                service.close()

    def test_frontend_language_parity_and_javascript_syntax(self) -> None:
        script_path = PROJECT_ROOT / "pathlex" / "static" / "app.js"
        text = script_path.read_text(encoding="utf-8")
        en_start = text.index("  en: {") + len("  en: {")
        en_end = text.index("\n  },\n  zh: {", en_start)
        zh_start = en_end + len("\n  },\n  zh: {")
        zh_end = text.index("\n  },\n};", zh_start)
        key_pattern = re.compile(r"^    ([A-Za-z_][A-Za-z0-9_]*):", re.MULTILINE)
        english_keys = set(key_pattern.findall(text[en_start:en_end]))
        chinese_keys = set(key_pattern.findall(text[zh_start:zh_end]))
        self.assertEqual(english_keys, chinese_keys)
        self.assertGreater(len(english_keys), 100)
        self.assertIn(
            'localStorage.getItem("pathlex.language") === "zh" ? "zh" : "en"',
            text,
        )
        self.assertIn('localStorage.removeItem("pathlex.language")', text)
        self.assertIn("/complete", text)
        node = shutil.which("node")
        if node:
            completed = subprocess.run(
                [node, "--check", str(script_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
