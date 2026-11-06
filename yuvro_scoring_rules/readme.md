# Yuvro Scoring Rules - Django Todo Signup Bugs

This directory contains the automated scoring harness for the **Django Todo Signup Bugs** engineering lab.

## Overview

The lab asks the candidate to fix the user signup flow so that duplicate email addresses are rejected with a clear error message, using case-insensitive comparison, while still allowing valid registrations.

## Structure

- `main_test.py` — Entry point. Sets up Django, runs each task evaluator, aggregates results, and prints a single JSON object to stdout.
- `test1.py` — Evaluator for **Task 1: Prevent Duplicate Email Registration** (10 marks).
- `readme.md` — This file.

## How the tests work

### Task 1 — Prevent Duplicate Email Registration

The evaluator attempts two complementary strategies:

1. **Serializer-level check (preferred).** It tries to import a registration serializer from common locations (`accounts.serializers`, `users.serializers`, `todo.serializers`, `api.serializers`, etc.) using common class names (`UserRegistrationSerializer`, `RegisterSerializer`, `RegistrationSerializer`). If found, it:
   - Submits a valid registration and asserts it is accepted.
   - Submits the same email again and asserts a validation error is raised on the `email` field (or `non_field_errors`).
   - Submits the same email with different casing (e.g. `USER@example.com`) and asserts it is also rejected.

2. **API-level check (fallback).** If no serializer is found, it discovers registration endpoints from the URLconf (or falls back to common paths like `/api/register/`, `/api/signup/`, etc.) and uses `django.test.Client` to:
   - POST a valid registration → expect `200`/`201`.
   - POST the same email → expect `400`.
   - POST the same email with different casing → expect `400`.

All test users created during evaluation are cleaned up in a `finally` block.

## Output contract

`main_test.py` prints exactly one JSON object to stdout:

```json
{
  "tasks": {
    "task1": { "result": "passed", "score": 10, "message": "..." }
  },
  "total_score": 10,
  "max_possible_score": 10
}
```

Each task entry has:
- `result`: `"passed"` or `"failed"`
- `score`: integer marks awarded (0 if failed)
- `message`: human-readable explanation

## Running locally

From the project root (where `manage.py` lives):

```bash
python yuvro_scoring_rules/main_test.py
```

If your Django settings module is not `settings`, set it explicitly:

```bash
DJANGO_SETTINGS_MODULE=myproject.settings python yuvro_scoring_rules/main_test.py
```

The runner will also try common settings module names (`todo.settings`, `config.settings`, `myproject.settings`, `app.settings`) as a fallback.

## Robustness

- Every evaluator wraps its logic in `try/except` and returns a structured failure result instead of raising.
- The runner itself has a top-level `try/except` that emits a valid JSON fallback if anything unexpected happens, so stdout is always parseable.
- Test data is cleaned up in `finally` blocks to avoid polluting the database between runs.
