"""Exercise the Rust CLI against the real FastAPI fixture over loopback."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import uvicorn
from eval.fixture.app import create_app

ROOT = Path(__file__).resolve().parents[1]


class EndToEndTests(unittest.TestCase):
    def test_owner_peer_and_anonymous_observations(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", log_level="critical", access_log=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(server.started, "Fixture server failed to start")
            config = json.loads((ROOT / "examples/replay.json").read_text())
            config["scope_origin"] = f"http://127.0.0.1:{port}"
            config["url"] = config["scope_origin"] + "/invoices/inv-b"
            with tempfile.TemporaryDirectory() as directory:
                request = Path(directory) / "request.json"
                report = Path(directory) / "report.json"
                request.write_text(json.dumps(config))
                binary = ROOT / "target/debug" / ("seca.exe" if os.name == "nt" else "seca")
                result = subprocess.run([str(binary), "replay", str(request), str(report), "--authorized"],
                    env=dict(os.environ, SECA_BOB_TOKEN="fixture-bob", SECA_ALICE_TOKEN="fixture-alice"),
                    capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                observations = json.loads(report.read_text())["observations"]
                self.assertEqual([o["status"] for o in observations], [200, 200, 401])
                self.assertTrue(observations[0]["json_matches"])
                self.assertFalse(observations[1]["status_matches"])
                self.assertTrue(observations[2]["status_matches"])
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            listener.close()
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
