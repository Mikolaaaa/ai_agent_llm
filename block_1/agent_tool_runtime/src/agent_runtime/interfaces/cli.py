from __future__ import annotations

import argparse
import asyncio
import json

from agent_runtime.core.state import Principal, RunLimits
from agent_runtime.observability.events import JsonStdoutEventSink
from agent_runtime.model.fake import KeywordFakeModel
from agent_runtime.engine.runtime import AgentRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Block 1 Agent Tool Runtime demo.")
    parser.add_argument("message", help="User request")
    parser.add_argument("--max-iterations", type=int, default=6)
    parser.add_argument("--allow", action="append", default=None, help="Allowed tool name. Can be repeated.")
    parser.add_argument("--confirm", action="append", default=None, help="Confirmed side-effect tool name.")
    parser.add_argument("--json", action="store_true", help="Print full run state as JSON.")
    return parser


async def main_async() -> int:
    args = build_parser().parse_args()
    allowed_tools = set(args.allow or ["search_documents", "get_document", "calculator"])
    principal = Principal(
        user_id="demo_user",
        scopes={"documents.read", "calculator.use", "notes.write"},
        owned_document_ids={"doc_1", "doc_2", "doc_3"},
    )
    runtime = AgentRuntime(model=KeywordFakeModel(), events=JsonStdoutEventSink())
    state = await runtime.run(
        args.message,
        principal=principal,
        allowed_tools=allowed_tools,
        limits=RunLimits(max_iterations=args.max_iterations),
        confirmations=set(args.confirm or []),
    )
    if args.json:
        print(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(state.final_answer or state.error.to_dict())
    return 0 if state.final_answer else 1


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
