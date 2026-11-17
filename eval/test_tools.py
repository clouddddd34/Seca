"""Black-box CLI tests. All HTTP requests stay on literal loopback."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "target" / "debug" / ("seca.exe" if os.name == "nt" else "seca")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.requests.append((self.path, self.headers.get("Authorization")))
        if self.path == "/drop":
            self.close_connection = True
            return
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/destination")
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        if self.path == "/large":
            body = b"x" * 70000
        else:
            body = json.dumps({"owner": "bob", "credential": self.headers.get("Authorization")}).encode()
        self.wfile.write(body)


class ToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BINARY.is_file():
            raise RuntimeError("Build the CLI first with cargo build --locked")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.server.requests = []
        self.config = {"scope_origin": self.origin, "url": self.origin + "/resource",
                       "safe_to_read": True, "accounts": [
                           {"label": "bob", "token_env": "SECA_TEST_B", "expected_status": 200,
                            "expect_json": {"pointer": "/owner", "value": "bob"}},
                           {"label": "alice", "token_env": "SECA_TEST_A", "expected_status": 403},
                           {"label": "anonymous", "expected_status": 401}]}

    def invoke(self, *args):
        environment = dict(os.environ, SECA_TEST_A="fake-secret-A", SECA_TEST_B="fake-secret-B")
        return subprocess.run([str(BINARY), *map(str, args)], env=environment, capture_output=True, text=True, timeout=20)

    def replay(self, authorized=True):
        config = self.directory / "config.json"
        config.write_text(json.dumps(self.config), encoding="utf-8")
        report = self.directory / "report.json"
        args = ["replay", config, report]
        if authorized:
            args.append("--authorized")
        result = self.invoke(*args)
        return result, json.loads(report.read_text()) if report.exists() else None

    def test_distinct_credentials_and_redacted_report(self):
        result, report = self.replay()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([token for _, token in self.server.requests],
                         ["Bearer fake-secret-B", "Bearer fake-secret-A", None])
        self.assertTrue(report["observations"][0]["json_matches"])
        self.assertFalse(report["observations"][1]["status_matches"])
        serialized = json.dumps(report) + result.stdout + result.stderr
        for sensitive in ("fake-secret", self.origin):
            self.assertNotIn(sensitive, serialized)

    def test_redirect_is_not_followed(self):
        self.config["url"] = self.origin + "/redirect"
        self.config["accounts"] = [self.config["accounts"][0]]
        result, report = self.replay()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["observations"][0]["status"], 302)
        self.assertEqual(len(self.server.requests), 1)

    def test_truncated_body_is_not_scored_as_json(self):
        self.config["url"] = self.origin + "/large"
        self.config["accounts"] = [self.config["accounts"][0]]
        result, report = self.replay()
        self.assertEqual(result.returncode, 0)
        item = report["observations"][0]
        self.assertTrue(item["body_truncated"])
        self.assertFalse(item["json_check_evaluated"])
        self.assertIsNone(item["json_matches"])
        self.assertEqual(item["bytes_read"], 65537)

    def test_failure_stops_without_retry(self):
        self.config["url"] = self.origin + "/drop"
        result, report = self.replay()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["accounts_attempted"], 1)
        self.assertEqual(len(self.server.requests), 1)
        self.assertIn("error", report["observations"][0])

    def test_authorization_required(self):
        result, report = self.replay(authorized=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(report)
        self.assertEqual(self.server.requests, [])

    def test_scope_mismatch_sends_nothing(self):
        self.config["scope_origin"] = "http://127.0.0.1:1"
        result, _ = self.replay()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.server.requests, [])

    def test_missing_later_credential_sends_nothing(self):
        self.config["accounts"][1]["token_env"] = "SECA_TEST_VARIABLE_THAT_DOES_NOT_EXIST"
        result, _ = self.replay()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.server.requests, [])

    def test_existing_report_is_preserved_without_requests(self):
        report = self.directory / "report.json"
        report.write_text('{"existing":true}')
        result, _ = self.replay()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report.read_text(), '{"existing":true}')
        self.assertEqual(self.server.requests, [])

    def test_log_add_validates_and_preserves_original(self):
        original = self.directory / "log.json"
        record = self.directory / "finding.json"
        updated = self.directory / "log-next.json"
        self.assertEqual(self.invoke("log-init", original, "fixture", "local").returncode, 0)
        before = original.read_bytes()
        self.assertNotEqual(self.invoke("log-init", original, "other", "local").returncode, 0)
        finding = {"id": "F-1", "title": "Fixture", "status": "confirmed", "severity": "low",
                   "expected": "Denied", "observed": "Allowed", "impact": "Fixture",
                   "remediation": "Enforce rule", "evidence": [], "reproduction": [],
                   "preconditions": [], "uncertainty": []}
        record.write_text(json.dumps(finding))
        self.assertNotEqual(self.invoke("log-add", original, record, updated).returncode, 0)
        self.assertFalse(updated.exists())
        finding.update(evidence=["Local test"], reproduction=["Run test"])
        record.write_text(json.dumps(finding))
        self.assertEqual(self.invoke("log-add", original, record, updated).returncode, 0)
        self.assertEqual(original.read_bytes(), before)
        self.assertEqual(self.invoke("log-check", updated).returncode, 0)
        self.assertNotEqual(self.invoke("log-add", updated, record, self.directory / "duplicate.json").returncode, 0)


if __name__ == "__main__":
    unittest.main()
