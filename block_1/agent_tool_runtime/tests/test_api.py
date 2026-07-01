import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from agent_runtime.engine.runtime import AgentRuntime
from agent_runtime.interfaces.api import AgentRunHandler
from agent_runtime.model.fake import KeywordFakeModel


class ApiTests(unittest.TestCase):
    def test_health_post_run_and_get_run(self) -> None:
        class TestHandler(AgentRunHandler):
            runtime = AgentRuntime(model=KeywordFakeModel())

        try:
            server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
        except PermissionError as exc:
            self.skipTest(f"Local socket binding is not permitted in this environment: {exc}")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            base_url = f"http://127.0.0.1:{server.server_address[1]}"

            health = _get_json(f"{base_url}/health")
            self.assertEqual(health["status"], "ok")

            created = _post_json(
                f"{base_url}/runs",
                {"message": "find agent runtime docs"},
            )
            self.assertEqual(created["status"], "completed")
            self.assertEqual(created["summary"]["terminal_reason"], "completed")

            loaded = _get_json(f"{base_url}/runs/{created['id']}")
            self.assertEqual(loaded["id"], created["id"])
            self.assertEqual(loaded["trace_id"], created["trace_id"])
            self.assertEqual(loaded["final_answer"], created["final_answer"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


def _get_json(url: str) -> dict:
    with urlopen(url, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
