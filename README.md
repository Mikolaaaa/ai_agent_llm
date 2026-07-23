# LLM / AI Agent Engineer Roadmap

Личный репозиторий для подготовки по LLM / AI Agent engineering.

Сейчас закрываются первые два практических блока:

- `block_1/agent_tool_runtime` — backend-прототип agent runtime;
- `block_2/mcp_tool_server` — MCP-style tool server и интеграция с runtime из блока 1.

## Статус

### Блок 1 — Agent Tool Runtime

Сделан Strong-прототип runtime:

- agent state и run lifecycle;
- tool loop: `model decision -> validation -> permission check -> tool execution -> final answer`;
- tool registry и schemas;
- input/output validation;
- structured errors;
- permissions/allowlist/limits;
- timeout/retry policy;
- trace logs;
- CLI/API запуск;
- in-memory и SQLite storage;
- unit/integration/API tests.

### Блок 2 — MCP Tool Server + Agent Integration

Сделан Strong-прототип внешнего tool contract:

- MCP-style server с `initialize`, `tools/list`, `tools/call`, `server/info`;
- 6 tools: `search_documents`, `get_document`, `save_note`, `calculate_metric`, `get_user_context`, `unstable_dependency`;
- явные input/output schemas;
- direct client/demo;
- adapter к agent runtime из блока 1;
- validation, permissions, side-effect confirmation;
- structured errors и trace logs;
- contract tests, permission tests, direct server/client tests;
- e2e agent integration tests подготовлены.

Важно: блок 2 — учебный MCP-compatible prototype без official MCP SDK. Он показывает архитектурную границу, contracts и integration flow. Production-следующий шаг — заменить custom server/client layer на официальный MCP Python SDK.

## Структура

```text
block_1/
  agent_tool_runtime/
    src/agent_runtime/
    tests/
    pyproject.toml

block_2/
  mcp_tool_server/
    src/mcp_tool_server/
    tests/
    README.md
    TECHNICAL_WALKTHROUGH.md
    PROJECT_EXPLANATION.md
    DESIGN.md
    VERSIONING.md
    pyproject.toml
```

## Быстрая проверка

### Блок 1

```bash
cd /Users/user/Documents/llm_ai_agent_engeneer/block_1/agent_tool_runtime
PYTHONPATH=src python3 -m unittest discover -s tests
```

CLI happy path:

```bash
PYTHONPATH=src python3 -m agent_runtime.interfaces.cli "find agent runtime docs" --json
```

Ожидаемо:

- `status: "completed"`;
- есть `trace_id`;
- есть `tool_calls`;
- есть `tool_results`;
- есть `summary`;
- есть `final_answer`.

### Блок 2

```bash
cd /Users/user/Documents/llm_ai_agent_engeneer/block_2/mcp_tool_server
```

Server info:

```bash
PYTHONPATH=src:../../block_1/agent_tool_runtime/src python3 -m mcp_tool_server.cli info
```

Ожидаемо:

- `protocolVersion: "2025-11-25"`;
- `tools_count: 6`.

Список tool contracts:

```bash
PYTHONPATH=src:../../block_1/agent_tool_runtime/src python3 -m mcp_tool_server.cli list-tools
```

Direct tool call:

```bash
PYTHONPATH=src:../../block_1/agent_tool_runtime/src python3 -m mcp_tool_server.cli call-tool search_documents '{"query":"mcp","limit":2}'
```

Invalid arguments:

```bash
PYTHONPATH=src:../../block_1/agent_tool_runtime/src python3 -m mcp_tool_server.cli call-tool search_documents '{"query":"","limit":100}'
```

Permission error:

```bash
PYTHONPATH=src:../../block_1/agent_tool_runtime/src python3 -m mcp_tool_server.cli \
  --allowed-tools search_documents \
  --scopes documents.read \
  call-tool save_note '{"title":"x","content":"y"}'
```

Unit/direct tests:

```bash
PYTHONPATH=src:../../block_1/agent_tool_runtime/src python3 -m unittest tests.test_contracts tests.test_server_client tests.test_permissions
```

Full check, including agent integration:

```bash
PYTHONPATH=src:../../block_1/agent_tool_runtime/src python3 -m unittest discover
```

## Документы для разбора

Главные документы блока 2:

- `block_2/mcp_tool_server/TECHNICAL_WALKTHROUGH.md` — подробное объяснение проекта для себя;
- `block_2/mcp_tool_server/PROJECT_EXPLANATION.md` — объяснение, почему проект закрывает roadmap;
- `block_2/mcp_tool_server/DESIGN.md` — граница agent runtime / MCP server;
- `block_2/mcp_tool_server/VERSIONING.md` — versioning и compatibility policy.

## Что дальше

Логичные следующие улучшения:

- заменить MCP-style subset на официальный MCP Python SDK;
- добавить real stdio/HTTP transport integration;
- подключить real LLM adapter;
- добавить persistent storage для блока 2;
- расширить observability до OpenTelemetry-style traces.
