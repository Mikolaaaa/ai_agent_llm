import unittest

from agent_runtime.core.errors import (
    DependencyRuntimeError,
    ErrorType,
    PermissionRuntimeError,
    TimeoutRuntimeError,
    ValidationRuntimeError,
    map_exception,
)


class ErrorMappingTests(unittest.TestCase):
    def test_validation_error_is_not_retryable(self) -> None:
        info = map_exception(ValidationRuntimeError("bad input"))
        self.assertEqual(info.type, ErrorType.VALIDATION)
        self.assertFalse(info.retryable)

    def test_permission_error_is_not_retryable(self) -> None:
        info = map_exception(PermissionRuntimeError("denied"))
        self.assertEqual(info.type, ErrorType.PERMISSION)
        self.assertFalse(info.retryable)

    def test_timeout_error_is_retryable(self) -> None:
        info = map_exception(TimeoutRuntimeError("slow"))
        self.assertEqual(info.type, ErrorType.TIMEOUT)
        self.assertTrue(info.retryable)

    def test_dependency_error_is_retryable(self) -> None:
        info = map_exception(DependencyRuntimeError("temporary"))
        self.assertEqual(info.type, ErrorType.RUNTIME)
        self.assertTrue(info.retryable)

    def test_unknown_exception_is_sanitized(self) -> None:
        info = map_exception(RuntimeError("secret stack detail"))
        self.assertEqual(info.type, ErrorType.RUNTIME)
        self.assertEqual(info.code, "unhandled_exception")
        self.assertNotIn("secret", info.message)


if __name__ == "__main__":
    unittest.main()
