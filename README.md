# LLM / AI Agent Engineer Roadmap

Личный репозиторий для подготовки по LLM / AI Agent engineering.

Сейчас в работе первый блок — `Agent Tool Runtime`: небольшой backend-прототип, который показывает, как runtime управляет agent loop, tools, validation, permissions, limits и ошибками.

## Текущий статус

Сделал рабочий Strong-прототип по блоку `Agent Tool Runtime`.

Что уже есть:

- agent state и lifecycle run;
- tool loop: `model decision -> validation -> permission check -> tool execution -> final answer`;
- tool registry и tool schemas;
- input/output validation;
- structured errors;
- allowlist, permissions и limits;
- timeout/retry policy;
- logs с `trace_id`;
- CLI/API запуск;
- SQLite persistent run store;
- idempotency для side-effect tool;
- unit, integration и API component tests.

Оцениваю блок как практически закрытый по реализации:

- базовый runtime работает;
- failure cases покрыты тестами;
- side-effect tool требует confirmation и поддерживает idempotency key;
- state можно хранить in-memory или в SQLite;
- остаётся добрать real LLM adapter уже как следующий слой, не как core runtime.

## Структура

```text
block_1/
  agent_tool_runtime/
    src/agent_runtime/
      core/            # state, errors, validation
      engine/          # runtime loop, executor, permissions
      model/           # fake model
      tools/           # registry and built-in tools
      storage/         # in-memory and SQLite run stores
      observability/   # trace events
      interfaces/      # CLI and HTTP API
    tests/
    pyproject.toml
```

## Как проверить

Перейти в проект:

```bash
cd block_1/agent_tool_runtime
```

Запустить тесты:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Ожидаемый результат:

```text
Ran 28 tests
OK
```

В sandbox-окружениях API socket test может быть `skipped`, если запрещён bind
на локальный порт. На обычной машине тест проверяет `GET /health`,
`POST /runs` и `GET /runs/{run_id}`.

Запустить happy path через CLI:

```bash
PYTHONPATH=src python3 -m agent_runtime.interfaces.cli "find agent runtime docs" --json
```

В результате должны быть:

- `status: "completed"`;
- `trace_id`;
- `tool_calls`;
- `tool_results`;
- `summary`;
- `final_answer`.

Проверить persistent state через SQLite:

```bash
PYTHONPATH=src python3 -m agent_runtime.interfaces.cli \
  "find agent runtime docs" \
  --sqlite /tmp/agent_runtime_demo.sqlite3 \
  --json
```

Проверить failure cases:

```bash
PYTHONPATH=src python3 -m agent_runtime.interfaces.cli "invalid search request" --json
PYTHONPATH=src python3 -m agent_runtime.interfaces.cli "please save note" --json
PYTHONPATH=src python3 -m agent_runtime.interfaces.cli "loop forever" --max-iterations 1 --json
```

Ожидаемо:

- invalid arguments дают `validation_error`;
- запрещённый/неподтверждённый side-effect tool даёт `permission_error`;
- превышение iterations даёт `limit_error`.

## Что дальше

Следующие улучшения уже за пределами core runtime блока:

- добавить adapter для реальной LLM;
- расширить observability;
- заменить stdlib HTTP API на production-like FastAPI/Pydantic слой при необходимости.
