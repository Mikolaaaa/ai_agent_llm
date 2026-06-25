import unittest

from agent_runtime.core.errors import ValidationRuntimeError
from agent_runtime.tools.registry import ToolRegistry
from agent_runtime.tools.builtin import build_default_registry


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()

    def test_valid_tool_input_passes(self) -> None:
        tool = self.registry.get("search_documents")
        payload = tool.validate_input({"query": "agent", "top_k": 2})
        self.assertEqual(payload["query"], "agent")

    def test_invalid_tool_input_fails(self) -> None:
        tool = self.registry.get("search_documents")
        with self.assertRaises(ValidationRuntimeError):
            tool.validate_input({"query": "", "top_k": 100})

    def test_unknown_fields_are_rejected(self) -> None:
        tool = self.registry.get("calculator")
        with self.assertRaises(ValidationRuntimeError):
            tool.validate_input({"expression": "2 + 2", "extra": True})

    def test_invalid_tool_output_fails(self) -> None:
        tool = self.registry.get("calculator")
        with self.assertRaises(ValidationRuntimeError):
            tool.validate_output({"value": 4})

    def test_duplicate_tool_registration_fails(self) -> None:
        registry = ToolRegistry()
        tool = self.registry.get("calculator")
        registry.register(tool)
        with self.assertRaises(ValidationRuntimeError):
            registry.register(tool)


if __name__ == "__main__":
    unittest.main()
