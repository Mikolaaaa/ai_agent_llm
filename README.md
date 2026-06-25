# LLM / AI Agent Engineer Roadmap

Личный репозиторий для подготовки по LLM / AI Agent engineering.

Сейчас в работе первый блок — `Agent Tool Runtime`: небольшой backend-прототип, который показывает, как runtime управляет agent loop, tools, validation, permissions, limits и ошибками.

## Текущий статус

За первую неделю сделал рабочий MVP/Normal-прототип по блоку `Agent Tool Runtime`.

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
- unit и integration tests.

Оцениваю блок примерно на 70%:

- базовый runtime работает;
- основные failure cases покрыты тестами;
- продолжаю добирать теорию и архитектурные trade-offs;
- дальше хочу лучше закрепить edge cases, side-effect tools, persistent state и real LLM adapter.

## Структура

```text
block_1/
  agent_tool_runtime/
    src/agent_runtime/
      core/            # state, errors, validation
      engine/          # runtime loop, executor, permissions
      model/           # fake model
      tools/           # registry and built-in tools
      storage/         # in-memory run store
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
Ran 23 tests
OK
```

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

Проверить failure cases:

```bash
PYTHONPATH=src python3 -m agent_runtime.interfaces.cli "invalid search request" --json
PYTHONPATH=src python3 -m agent_runtime.interfaces.cli "please save note" --json
PYTHONPATH=src python3 -m agent_runtime.interfaces.cli "loop forever" --max-iterations 1 --json
```

Ожидаемо:

- invalid arguments дают `validation_error`;
- запрещённый tool даёт `permission_error`;
- превышение iterations даёт `limit_error`.

## Что дальше

Следующие улучшения по блоку:

- лучше разобрать side-effect tools и idempotency;
- добавить persistent storage;
- добавить adapter для реальной LLM;
- расширить observability;
- пройти edge cases руками и через тесты.

