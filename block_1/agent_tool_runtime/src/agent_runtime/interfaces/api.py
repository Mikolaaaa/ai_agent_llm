from __future__ import annotations

import asyncio
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from agent_runtime.core.state import Principal, RunLimits
from agent_runtime.model.fake import KeywordFakeModel
from agent_runtime.engine.runtime import AgentRuntime


class AgentRunHandler(BaseHTTPRequestHandler):
    runtime = AgentRuntime(model=KeywordFakeModel())

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"status": "ok"})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/runs":
            self._json(404, {"error": "not_found"})
            return
        try:
            body = self._read_json()
            principal = Principal(
                user_id=body.get("user_id", "api_user"),
                scopes=set(body.get("scopes", ["documents.read", "calculator.use"])),
                owned_document_ids=set(body.get("owned_document_ids", ["doc_1", "doc_2", "doc_3"])),
            )
            state = asyncio.run(
                self.runtime.run(
                    body["message"],
                    principal=principal,
                    allowed_tools=set(body.get("allowed_tools", ["search_documents", "get_document", "calculator"])),
                    confirmations=set(body.get("confirmations", [])),
                    limits=RunLimits(max_iterations=int(body.get("max_iterations", 6))),
                )
            )
            self._json(200 if state.final_answer else 400, state.to_dict())
        except Exception as exc:
            self._json(400, {"error": exc.__class__.__name__, "message": str(exc)})

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8080), AgentRunHandler)
    print("Agent Runtime API listening on http://127.0.0.1:8080")
    server.serve_forever()


if __name__ == "__main__":
    main()
