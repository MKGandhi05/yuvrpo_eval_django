# Yuvro Scoring Rules

Automated scoring harness for the **Django todo signup bugs** engineering lab.

## Structure

- `main_test.py` — Entry point. Sets up Django, runs each task test, aggregates scores, and prints a single JSON object to stdout.
- `test1.py` — Task 1: Signup validation & duplicate email handling (10 marks).
- `test2.py` — Task 2: Todo creation with ownership & validation (10 marks).
- `test3.py` — Task 3: Todo listing with pagination & query efficiency (10 marks).

Each `testN.py` exposes an `evaluate()` function returning:

```json
{ "result": "passed" | "failed", "score": <int>, "message": "..." }
```

## Running Locally

From the project root (where `manage.py` / `settings.py` live):

```bash
python yuvro_scoring_rules/main_test.py
```

The runner will:

1. Add the project root to `sys.path`.
2. Configure `DJANGO_SETTINGS_MODULE` (tries `settings`, `todo_project.settings`, `project.settings`, `config.settings`).
3. Call `django.setup()`.
4. Execute each task test in isolation, catching all exceptions.
5. Print the combined JSON result to stdout.

## Output Contract

```json
{
  "tasks": {
    "task1": { "result": "passed", "score": 10, "message": "..." },
    "task2": { "result": "failed", "score": 0, "message": "..." },
    "task3": { "result": "passed", "score": 10, "message": "..." }
  },
  "total_score": 20,
  "max_possible_score": 30
}
```

## What Each Test Checks

### Task 1 — Signup
- Valid signup returns 200/201 and creates the user.
- Duplicate email (case-insensitive) returns 400.
- Password shorter than 8 chars returns 400 and does not create a user.
- Password without a digit returns 400 and does not create a user.
- Missing fields return 400.

### Task 2 — Todo creation
- Unauthenticated POST returns 401/403.
- Authenticated POST with valid title returns 200/201 and assigns `user` to the authenticated user.
- Empty/whitespace title returns 400.
- Title longer than 200 chars returns 400.

### Task 3 — Todo listing
- Unauthenticated GET returns 401/403.
- Authenticated GET returns paginated response with `count`, `next`, `previous`, `results`.
- Page size is 10; `count` reflects only the authenticated user's todos.
- Page 2 returns the remaining items.
- No cross-user data leakage.

## Notes

- Tests use `django.test.Client` and DRF `Token` authentication.
- All created test data is cleaned up in `finally` blocks.
- Any exception inside a test is caught and reported as `failed` with score 0 — the runner never crashes stdout JSON parsing.
