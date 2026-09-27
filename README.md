# DesignProof

**Checks that your code does what your policy says.**

**Live demo:** https://designproof.streamlit.app (click "Run Live Check" to run Alloy on the server)

Built with **IBM Bob 2.0** and the **Alloy 6 Analyzer** for the IBM Bob 2.0 Hackathon.

## The problem

66% of developers say AI generated code is "almost right, but not quite" (Stack Overflow Developer Survey 2025). The most dangerous "not quite" hides in permission logic: who can access what. These bugs pass unit tests and code review, because tests only check the cases someone thought of, and they end up as data leaks.

DesignProof improves the **code review workflow for permission logic**: it checks the code against the written policy across every possible combination of users, teams, files, and links, up to a chosen size.

## How it works

1. **Bob reads the policy** (document understanding) and **the code** (subagents working in parallel).
2. **Bob writes an Alloy model** of what the code actually does, with one assertion per policy rule.
3. **`designproof.py` runs Alloy**, which searches every combination up to scope 4 for a counterexample.
4. For each violation, **Bob writes a failing test, applies a minimal fix, and rechecks** until every rule is verified.
5. **CI runs the check on every push** and fails the build if any rule is violated.

## Results on the sample app

The sample FastAPI file sharing app was built with one deliberate permission bug as a test subject. Its 4 original tests all passed.

| Rule | Before any fix | After fix 1 | After fix 2 |
|---|---|---|---|
| 1. Current members may edit | VERIFIED | **VIOLATED** | VERIFIED |
| 2. Share link holders may edit (unless removed) | VERIFIED | VERIFIED | VERIFIED |
| 3. Removed users can never edit | **VIOLATED** | VERIFIED | VERIFIED |

- **Violation 1 (Rule 3):** a user removed from a team could still edit the team's files through a share link they held. Found by Alloy.
- **Violation 2 (Rule 1):** the fix for violation 1 introduced a new bug: a removed user who was added back was wrongly blocked. This bug was **not planted**. Bob found it by reading the code and running a test, and Alloy confirmed it by rechecking the "after fix 1" model.

All three snapshots were checked by real Alloy runs: see `models/` and `results_before.json`, `results_fix1.json`, `results.json`. Full details are in [`report.md`](report.md).

## Use DesignProof on your own project

1. Copy `designproof.py`, `.bob/custom_modes.yaml`, and `.github/workflows/designproof.yml` into your project.
2. Write your rules in a markdown file, for example `policy/permission_policy.md`.
3. Open the project in IBM Bob, switch to the **DesignProof** mode, and ask it to verify the code against the policy.
4. Commit the Alloy model Bob writes. From then on, CI checks every push and blocks rule violations.

Requirements: Python 3.11+, Java 11+, and the Alloy 6.2.0 jar (CI and the dashboard download it automatically; for local use, download `org.alloytools.alloy.dist.jar` from alloytools.org into the project root).

## Quick start (sample app)

```bash
pip install -r requirements.txt
python designproof.py models/permissions.als   # formal check, needs Java
pytest demo_app/tests/ -v                      # 20 tests
streamlit run dashboard/app.py                 # dashboard
```

`designproof.py` exits **0** if every check is UNSAT (all rules hold) and **1** if any check is SAT (a rule is violated).

```
usage: python designproof.py MODEL [--jar PATH] [--output-dir DIR] [--results-json PATH]
```

## How IBM Bob was used

- **Plan mode:** planned the verification in sub tasks before touching code.
- **Subagents in parallel:** one read the policy, another traced how permissions are enforced in the code.
- **Document understanding:** turned the policy document into formal Alloy assertions.
- **Agent mode:** ran the full loop: model, check, failing test, fix, recheck, report.
- **Custom mode:** the workflow is packaged as the reusable DesignProof mode in `.bob/custom_modes.yaml`.
- Bob also built `designproof.py` with its 14 parser tests, the CI workflow, and the dashboard.

## Limits

- Alloy checks are complete **up to the chosen scope** (4 of each thing), not for unlimited sizes. In practice, design bugs almost always appear in small examples.
- An Alloy model can misdescribe the code, so every counterexample is confirmed by a real failing test against the actual code.

## Project structure

```
demo_app/                 sample FastAPI app (the test subject) and its tests
policy/                   permission_policy.md, the rules
models/                   Alloy models: permissions_before.als, permissions_fix1.als, permissions.als
designproof.py            Alloy runner and result parser (CLI)
dashboard/app.py          Streamlit dashboard with live check
.bob/custom_modes.yaml    DesignProof Bob mode
.github/workflows/        CI workflow
results*.json             saved Alloy results for each snapshot
report.md                 full verification report
packages.txt              installs Java on Streamlit Community Cloud
```