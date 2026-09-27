# designproof — File Sharing Demo with Formal Policy Verification

A minimal FastAPI file-sharing app with an in-memory data store, used as the
subject of a formal verification exercise using the
[Alloy 6 Analyzer](https://alloytools.org/).

Entities: User, Team (with `members` and `removed` sets), File, ShareLink.

---

## DesignProof

**DesignProof** is a workflow that checks whether application code obeys a
written policy document. It uses:

- **Alloy 6** for exhaustive formal checking (finds counterexamples up to a
  bounded scope).
- **`designproof.py`** — a CLI tool that runs the model and prints a
  VERIFIED / VIOLATED table.
- **pytest** for regression tests that reproduce each counterexample concretely.

The policy lives in [`policy/permission_policy.md`](policy/permission_policy.md).
The Alloy model lives in [`models/permissions.als`](models/permissions.als).
The verification report lives in [`report.md`](report.md).

### Quick start

```bash
pip install -r requirements.txt

# Run formal checker (requires Java 11+)
python designproof.py models/permissions.als

# Run all tests
pytest demo_app/tests/ -v
```

`designproof.py` exits **0** if all checks are UNSAT (every rule holds) and
**1** if any check is SAT (a rule is violated).

### designproof.py options

```
usage: python designproof.py MODEL [--jar PATH] [--output-dir DIR] [--results-json PATH]

positional arguments:
  MODEL              Path to the .als Alloy model file

options:
  --jar PATH         Path to the Alloy jar
                     (default: org.alloytools.alloy.dist.jar in the project root)
  --output-dir DIR   Directory for Alloy output files (default: permissions/)
  --results-json     Path to write the machine-readable JSON results
                     (default: results.json)
```

Results are also written to `results.json` for use by CI or other tools.

### The Bob DesignProof mode

This project includes a custom Bob mode called **DesignProof**
(`.bob/custom_modes.yaml`). Switch to it in the mode picker to get an
assistant that follows the full nine-step verification workflow:

1. Read the policy and extract rules.
2. Read the code and describe enforcement.
3. Write an Alloy 6 model of the **actual** code behavior.
4. Run `designproof.py` and report actual results.
5. Translate counterexamples into failing pytest tests.
6. Apply minimal fixes.
7. Re-check for cascades (e.g. a removed-user guard that blocks re-added members).
8. Update the Alloy model to match the fixed code; rerun until all UNSAT.
9. Write `report.md`.

The mode is workspace-scoped — it only appears when this project is open.

---

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

## CI

The GitHub Actions workflow at
[`.github/workflows/designproof.yml`](.github/workflows/designproof.yml):

1. Installs Java 21 and Python 3.11.
2. Downloads the Alloy 6.2.0 jar from the official GitHub release.
3. Runs `pytest demo_app/tests/ -v`.
4. Runs `python designproof.py models/permissions.als`.
5. **Fails the build** if any check is SAT (a rule is violated).
6. Uploads `results.json` and the `permissions/` output folder as artifacts.

Push any branch or open a pull request to trigger the checks automatically.

## Project structure

```
demo_app/
  __init__.py
  models.py          # dataclasses + in-memory store dicts
  permissions.py     # can_edit(user_id, file_id)
  main.py            # FastAPI app and endpoints
  tests/
    test_permissions.py          # API-level permission tests
    test_designproof_parsing.py  # unit tests for designproof.py parsing
models/
  permissions.als    # Alloy 6 model (fixed code)
policy/
  permission_policy.md
.bob/
  custom_modes.yaml  # DesignProof Bob mode (workspace-scoped)
.github/
  workflows/
    designproof.yml  # CI workflow
designproof.py       # Alloy runner + result parser CLI
report.md            # Verification report
requirements.txt
```
