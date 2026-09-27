# Dashboard Plan — DesignProof Streamlit Dashboard

## Approved Amendments (post-review)

1. **JAR download on button click only** — do not download on page load; the
   hosted page must open fast. Download only when "Run Live Check" is clicked.
2. **No hard-coded before-results** — Sub-Task 1 must run `designproof.py` on
   `permissions_before.als` and save real output as `results_before.json`.
   The dashboard uses `results_before.json` + `results.json` as fallback
   saved results. Both files are committed to the repo.
3. **Verify `designproof.py` already supports `--output-dir` and
   `--results-json`** — it does (confirmed in codebase research). If any
   option is missing, add it and update tests.
4. **Use `sys.executable` instead of `"python"`** when calling
   `designproof.py` from the dashboard subprocess, so it works on Streamlit
   Community Cloud.

## Top-Level Overview

**Goal:** Build a Streamlit dashboard at `dashboard/app.py` that presents the
DesignProof verification results for this repository in a clean, readable UI.

**Scope:**
- New file: `models/permissions_before.als` — Alloy model of the **original buggy**
  `can_edit` (no removed-user guard; share links grant access unconditionally).
- New file: `dashboard/app.py` — Streamlit dashboard with all required sections.
- New file: `packages.txt` — declares `default-jre` for Streamlit Community Cloud.
- Updated: `requirements.txt` — add `streamlit`.
- Confirm with `designproof.py` that `models/permissions_before.als` produces
  SAT for `RemovedUsersCannotEdit`.

**Sections of the dashboard:**
1. **Header** — "DesignProof" + subtitle.
2. **Policy** — render `policy/permission_policy.md`.
3. **Results table** — per-rule verdict: before / after fix 1 / after fix 2
   (VIOLATED or VERIFIED).
4. **Violation cards** — one card per violation with counterexample in plain
   English, how it was detected, failing test code, and the fix.
5. **Alloy models side by side** — `models/permissions_before.als` vs
   `models/permissions.als` as code blocks.
6. **Live check** — button that runs `designproof.py` on both models, shows
   result tables. Falls back to saved results if Java/jar is missing.
   Downloads the Alloy 6.2.0 jar from GitHub on first run if absent.

**Design constraint:** Clean and readable in both light and dark mode
(no hard-coded light-only colors; rely on Streamlit's CSS variables or
neutral palettes).

---

## Sub-Task 1 — Create models/permissions_before.als

**Status:** `[ ] pending`

**Intent:** Save an Alloy model of the original buggy `can_edit` function
(before either fix) as `models/permissions_before.als`, so the dashboard can
show the failing model alongside the fixed one. Confirm it actually produces
SAT for `RemovedUsersCannotEdit` via `designproof.py`.

**Expected Outcomes:**
- `models/permissions_before.als` exists with:
  - No `fact MembersRemovedDisjoint` (members and removed can overlap).
  - `canEdit` predicate mirrors the original buggy code: `u in f.team.members OR
    some ShareLink holds` — no `u not in f.team.removed` guard.
  - Asserts and check commands for all three rules (same as the fixed model).
- Running `python designproof.py models/permissions_before.als` produces SAT for
  `RemovedUsersCannotEdit` and UNSAT for the other two.

**Todo List:**
1. Create `models/permissions_before.als` with sigs `User`, `Team` (members/removed),
   `File`, `ShareLink` — identical signatures to `models/permissions.als`.
2. No `fact MembersRemovedDisjoint` (the buggy code never enforced disjointness
   and `add_member` didn't call `removed.discard`, so overlap was possible).
3. Write `pred canEdit` that mirrors the original buggy `permissions.py`:
   `u in f.team.members or (some sl : ShareLink | sl.file = f and sl.holder = u)` —
   no removed-user check whatsoever.
4. Add the same three asserts (`MembersCanEdit`, `ShareLinkHoldersCanEdit`,
   `RemovedUsersCannotEdit`) and three `check ... for 4` commands.
5. Run `python designproof.py models/permissions_before.als --output-dir permissions_before`
   and verify the console shows SAT for `RemovedUsersCannotEdit` and UNSAT for
   the other two checks.

**Relevant Context:**
- `models/permissions.als` — the fixed model to derive the buggy version from.
- `demo_app/permissions.py` original (before fix): no `if user_id in team.removed` guard.
- `designproof.py` CLI — used to confirm SAT.

---

## Sub-Task 2 — Update requirements.txt and add packages.txt

**Status:** `[ ] pending`

**Intent:** Add `streamlit` to `requirements.txt` so the dashboard can be
installed. Add `packages.txt` at the project root declaring `default-jre` so
Streamlit Community Cloud installs Java automatically.

**Expected Outcomes:**
- `requirements.txt` contains `streamlit` (appended).
- `packages.txt` exists at the project root containing `default-jre` on its own line.

**Todo List:**
1. Append `streamlit` to `requirements.txt`.
2. Create `packages.txt` at the project root with the single line `default-jre`.

**Relevant Context:**
- Current `requirements.txt`: `fastapi`, `uvicorn[standard]`, `pytest`, `httpx`.

---

## Sub-Task 3 — Build dashboard/app.py

**Status:** `[ ] pending`

**Intent:** Implement the complete Streamlit dashboard with all six required
sections. The dashboard must be self-contained, robust when Java/jar is absent,
and look clean in both light and dark mode.

**Expected Outcomes:**
- `dashboard/app.py` exists and `streamlit run dashboard/app.py` starts without
  errors.
- All six sections render correctly:
  1. Header with title and subtitle.
  2. Policy section rendering `policy/permission_policy.md`.
  3. Results table (3 rules × 3 columns) with color-coded VIOLATED/VERIFIED
     labels.
  4. Two violation cards with all required detail.
  5. Side-by-side Alloy model comparison (`st.columns`).
  6. Live check button with JAR download, result tables, and fallback.

**Todo List:**

### Section 1 — Header
1. `st.title("DesignProof")` + `st.caption("Checks that your code does what your policy says.")`.

### Section 2 — Policy
2. Read `policy/permission_policy.md` and render with `st.markdown`.

### Section 3 — Results Table
3. Hard-code the results table data (3 rules, verdicts for before/after-fix-1/after-fix-2)
   derived from `report.md`. Use `st.dataframe` or an HTML table rendered via
   `st.markdown` for styling flexibility. Use colored badges: 🔴 VIOLATED / 🟢 VERIFIED.

### Section 4 — Violation Cards
4. Violation 1 (Rule 3 — RemovedUsersCannotEdit):
   - Plain-English counterexample: Eve is added to a team, gets a share link,
     is then removed — she can still edit via the share link.
   - Detection: Alloy check `RemovedUsersCannotEdit for 4` returned SAT on
     the original model.
   - Failing test: `test_removed_member_with_share_link_cannot_edit` (show code).
   - Fix: `if user_id in team.removed: return False` in `permissions.py`.
5. Violation 2 (Rule 1 — MembersCanEdit broken by fix 1):
   - Plain-English counterexample: Frank is removed and re-added, but
     `add_member` doesn't clear `team.removed`, so he's in both sets; the
     removed guard fires and blocks him.
   - Detection: found by **code reading and a direct runtime test** (not Alloy
     SAT) after fix 1 was applied; Alloy later confirmed fix 2 with UNSAT.
   - Failing test: `test_readded_member_can_edit` (show code).
   - Fix: `team.removed.discard(body.user_id)` in `main.py`.

### Section 5 — Alloy Models Side by Side
6. Two `st.columns(2)`:
   - Left: `models/permissions_before.als` (buggy).
   - Right: `models/permissions.als` (fixed).
   - Each column has a label and a `st.code(..., language="alloy")` block.

### Section 6 — Live Check
7. On page load, check for the Alloy jar at `org.alloytools.alloy.dist.jar`
   (project root). If missing, download Alloy 6.2.0 from
   `https://github.com/AlloyTools/org.alloytools.alloy/releases/download/v6.2.0/org.alloytools.alloy.dist.jar`
   using `urllib.request` and save to the project root. Show a progress
   indicator while downloading.
8. Add a "Run Live Check" button. On click:
   a. Check for `java` on PATH using `shutil.which("java")`.
   b. If Java is missing: display a warning and show saved results from
      `results.json` for the fixed model and hard-coded SAT results for the
      before model.
   c. If Java is present: run `python designproof.py models/permissions_before.als
      --output-dir permissions_before --results-json results_before.json` and
      `python designproof.py models/permissions.als` via `subprocess.run` with
      `st.spinner`. Parse the written JSON files and display two result tables
      side by side.
9. Result table displays: Check name, SAT/UNSAT, and a VIOLATED/VERIFIED badge.

**Design notes:**
- Use `st.expander` for the violation details inside each card to keep the
  page scannable.
- Path resolution: use `Path(__file__).parent.parent` to resolve project-root
  paths reliably regardless of working directory.
- No hard-coded colors beyond neutral grey backgrounds (`st.info`, `st.warning`,
  `st.success`, `st.error` use Streamlit's theme-aware colors).

**Relevant Context:**
- `designproof.py` — CLI that writes `results.json`; use it as a subprocess.
- `results.json` — saved UNSAT results for the fixed model (fallback).
- `report.md` — source of truth for all verdicts and narrative text.
- `models/permissions_before.als` — created in Sub-Task 1.
- `models/permissions.als` — the fixed model.

---

## Sub-Task 4 — Verify the Dashboard Runs Locally

**Status:** `[ ] pending`

**Intent:** Confirm `streamlit run dashboard/app.py` starts successfully and
all sections render without Python errors.

**Expected Outcomes:**
- `streamlit run dashboard/app.py` starts the server with no import or runtime
  errors.
- All six sections visible in the browser.

**Todo List:**
1. Install streamlit if not already installed (`pip install streamlit`).
2. Run `streamlit run dashboard/app.py --server.headless true` and capture
   any startup errors.
3. Fix any import paths or file-not-found errors.
4. Confirm clean startup.

**Relevant Context:**
- Path resolution must work from any working directory; use
  `Path(__file__).parent.parent` for the project root.
