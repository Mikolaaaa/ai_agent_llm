import unittest

from agent_runtime.core.state import Principal
from agent_runtime.core.errors import PermissionRuntimeError
from agent_runtime.engine.permissions import PermissionService, RunPolicy
from agent_runtime.tools.builtin import build_default_registry


class PermissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()
        self.permissions = PermissionService()

    def test_tool_not_in_allowlist_denied(self) -> None:
        tool = self.registry.get("calculator")
        policy = RunPolicy(
            allowed_tools={"search_documents"},
            principal=Principal(user_id="u1", scopes={"calculator.use"}),
        )
        with self.assertRaises(PermissionRuntimeError):
            self.permissions.assert_allowed(tool=tool, arguments={"expression": "2+2"}, policy=policy)

    def test_missing_scope_denied(self) -> None:
        tool = self.registry.get("search_documents")
        policy = RunPolicy(
            allowed_tools={"search_documents"},
            principal=Principal(user_id="u1", scopes=set()),
        )
        with self.assertRaises(PermissionRuntimeError):
            self.permissions.assert_allowed(tool=tool, arguments={"query": "agent"}, policy=policy)

    def test_foreign_resource_denied(self) -> None:
        tool = self.registry.get("get_document")
        policy = RunPolicy(
            allowed_tools={"get_document"},
            principal=Principal(
                user_id="u1",
                scopes={"documents.read"},
                owned_document_ids={"doc_1"},
            ),
        )
        with self.assertRaises(PermissionRuntimeError):
            self.permissions.assert_allowed(tool=tool, arguments={"document_id": "doc_2"}, policy=policy)

    def test_side_effect_requires_confirmation(self) -> None:
        tool = self.registry.get("save_note")
        policy = RunPolicy(
            allowed_tools={"save_note"},
            principal=Principal(user_id="u1", scopes={"notes.write"}),
        )
        with self.assertRaises(PermissionRuntimeError):
            self.permissions.assert_allowed(
                tool=tool,
                arguments={"title": "t", "content": "c"},
                policy=policy,
            )

    def test_allowed_read_flow(self) -> None:
        tool = self.registry.get("get_document")
        policy = RunPolicy(
            allowed_tools={"get_document"},
            principal=Principal(
                user_id="u1",
                scopes={"documents.read"},
                owned_document_ids={"doc_1"},
            ),
        )
        self.permissions.assert_allowed(tool=tool, arguments={"document_id": "doc_1"}, policy=policy)


if __name__ == "__main__":
    unittest.main()
