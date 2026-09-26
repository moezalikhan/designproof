# designproof — File Sharing Demo

A minimal FastAPI file-sharing app with an in-memory data store.
Entities: User, Team, File, ShareLink.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn demo_app.main:app --reload
```

Interactive API docs available at <http://127.0.0.1:8000/docs>.

## Test

```bash
pytest demo_app/tests/ -v
```

## Structure

```
demo_app/
  __init__.py
  models.py        # dataclasses + in-memory store dicts
  permissions.py   # can_edit(user_id, file_id)
  main.py          # FastAPI app and endpoints
  tests/
    test_permissions.py
policy/
  permission_policy.md
requirements.txt
```
