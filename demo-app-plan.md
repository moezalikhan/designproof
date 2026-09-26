# Demo App Plan

## Top-Level Overview

Build a minimal Python FastAPI file-sharing demo inside `demo_app/`, with an in-memory data store, permission logic, tests, a policy document, supporting files (requirements.txt, README.md, .gitignore), and no database or Alloy files.

The existing `models/` folder and `org.alloytools.alloy.dist.jar` must not be touched.

### Intentional Policy Mismatch (do not fix)

`can_edit` is implemented as: team member **OR** share link holder — regardless of whether the share link holder was removed from the team. The policy document, by contrast, states that removed users must never edit by any route, including share links they still hold. This mismatch is deliberate: the app is a demo whose policy violation will be detected by an external tool later.

---

## Sub-Tasks

---

### Sub-Task 1 — Core Application (`demo_app/`)

**Status:** [ ] pending

**Intent:**
Scaffold the FastAPI application with in-memory models, permission logic, and all required API endpoints.

**Expected Outcomes:**
- `demo_app/__init__.py` exists (empty)
- `demo_app/models.py` defines `User`, `Team`, `File`, and `ShareLink` as simple dataclasses held in module-level dicts acting as the in-memory store. `Team` has two sets: `members` (current) and `removed` (ex-members).
- `demo_app/permissions.py` exports `can_edit(user_id, file_id)` — returns `True` if the user is in `team.members` OR holds any share link for that file. Does NOT check `team.removed`.
- `demo_app/main.py` defines a FastAPI app with these endpoints:
  - `POST /teams` — create a team
  - `POST /teams/{team_id}/members` — add a member (adds to `members` set)
  - `DELETE /teams/{team_id}/members/{user_id}` — remove a member (moves from `members` to `removed`)
  - `POST /files` — create a file owned by a team
  - `POST /share-links` — create a share link (file → holder user)
  - `PUT /files/{file_id}` — edit file; acting user id passed in `X-User-Id` header; returns 403 if `can_edit` is False

**Todo List:**
1. Create `demo_app/__init__.py` (empty)
2. Create `demo_app/models.py` — define `User`, `Team` (with `members` and `removed` sets), `File`, `ShareLink` dataclasses and in-memory store dicts
3. Create `demo_app/permissions.py` — implement `can_edit` exactly: `user_id in team.members OR any share link held by user for file`
4. Create `demo_app/main.py` — wire up all six endpoints using the in-memory store

**Relevant Context:**
- In-memory store: module-level dicts in `models.py`, imported by `main.py` and `permissions.py`
- `Team` dataclass fields: `id: str`, `members: set[str]`, `removed: set[str]`
- `can_edit` logic (implement exactly): `return user_id in team.members or any(sl.holder_id == user_id for sl in share_links.values() if sl.file_id == file_id)`
- `can_edit` does NOT check `team.removed` — that is the intentional bug
- The `PUT /files/{file_id}` endpoint reads `X-User-Id` from request headers, calls `can_edit`, returns 403 or 200

---

### Sub-Task 2 — Tests (`demo_app/tests/`)

**Status:** [ ] pending

**Intent:**
Write four pytest tests using FastAPI's `TestClient` that exercise the permission logic end-to-end via the HTTP API.

**Expected Outcomes:**
- `demo_app/tests/__init__.py` exists (empty)
- `demo_app/tests/test_permissions.py` contains exactly four tests:
  1. A team member can edit a file (expects 200)
  2. A non-member cannot edit a file (expects 403)
  3. A share link holder can edit a file (expects 200)
  4. Removing a member revokes their edit access (expects 403 after removal)
- All four tests pass when run with `pytest`

**Todo List:**
1. Create `demo_app/tests/__init__.py` (empty)
2. Create `demo_app/tests/test_permissions.py` with a `client` fixture and the four tests
3. Each test must reset the in-memory store so tests are isolated (clear the store dicts between tests)

**Relevant Context:**
- Use `from fastapi.testclient import TestClient` and `from demo_app.main import app`
- The in-memory store dicts live in `demo_app/models.py`; import and `.clear()` them in a pytest `autouse` fixture
- The four tests exercise the *implemented* `can_edit` (OR logic), not the policy. All four must pass.
- Test 4 (remove member): after removal the user is in `team.removed`, not in `team.members`, and holds no share link, so `can_edit` returns False and the endpoint returns 403.

---

### Sub-Task 3 — Policy Document (`policy/permission_policy.md`)

**Status:** [ ] pending

**Intent:**
Capture the intended permission policy in a human-readable markdown document, exactly as specified by the user.

**Expected Outcomes:**
- `policy/permission_policy.md` contains exactly these three rules (no additions, no omissions):
  1. Current members of a file's owning team may edit that file.
  2. A share link lets its holder edit the file, so outside collaborators can be invited.
  3. A user who has been removed from a team must never edit that team's files by any route, including share links they still hold.

**Todo List:**
1. Create `policy/` directory (implicit via file creation)
2. Write `policy/permission_policy.md` with the three rules verbatim

**Relevant Context:**
- This document is a policy statement, not code. Keep it plain and direct.
- Rule 3 conflicts with the `can_edit` implementation. This is intentional — do not reconcile.

---

### Sub-Task 4 — Supporting Files

**Status:** [ ] pending

**Intent:**
Add `requirements.txt`, `README.md`, and `.gitignore` to make the project runnable and well-documented.

**Expected Outcomes:**
- `requirements.txt` lists `fastapi`, `uvicorn`, `pytest`, and `httpx`
- `README.md` includes:
  - Brief project description
  - Install command (`pip install -r requirements.txt`)
  - Run command (`uvicorn demo_app.main:app --reload`)
  - Test command (`pytest demo_app/tests/`)
- `.gitignore` excludes:
  - `org.alloytools.alloy.dist.jar`
  - `buggy/`
  - `__pycache__/`
  - `*.pyc`
  - `.venv/`, `venv/`, `env/`

**Todo List:**
1. Create `requirements.txt`
2. Create `README.md`
3. Create `.gitignore`

**Relevant Context:**
- FastAPI's `TestClient` requires `httpx` as a dependency since FastAPI 0.95+
- `.gitignore` must explicitly name the jar file and `buggy/` as requested

---

### Sub-Task 5 — Run Tests and Confirm Pass

**Status:** [ ] pending

**Intent:**
Execute the test suite and verify all four tests pass with no errors.

**Expected Outcomes:**
- `pytest demo_app/tests/` exits with code 0
- Output shows 4 passed, 0 failed, 0 errors

**Todo List:**
1. Install dependencies (`pip install -r requirements.txt`)
2. Run `pytest demo_app/tests/ -v`
3. If any test fails, diagnose and fix before marking complete

**Relevant Context:**
- Tests must be run from the workspace root so that `demo_app` is importable as a package
- If there are import errors, check that all `__init__.py` files exist
