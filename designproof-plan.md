# DesignProof Plan — Permission Policy Verification

## Top-Level Overview

**Goal:** Formally verify that `demo_app/` obeys the three rules in `policy/permission_policy.md` using the Alloy 6 Analyzer, identify any violated rules via counterexamples, reproduce violations as pytest tests, fix the code minimally, and document everything in `report.md`.

**Scope:**
- `demo_app/permissions.py` — the single permission-check function `can_edit`
- `demo_app/models.py` — data model (User, Team with members/removed sets, File, ShareLink)
- `demo_app/main.py` — REST endpoints (member add/remove, file edit, share-link creation)
- `demo_app/tests/test_permissions.py` — existing tests
- `models/permissions.als` — Alloy model to be created
- `report.md` — final summary to be created

**Known bug (pre-identified):** `can_edit` checks share-link access without consulting `team.removed`, so a user removed from a team can still edit that team's files if they hold a share link. This violates Rule 3.

**Policy Rules:**
1. Current members of a file's owning team may edit that file.
2. A share link lets its holder edit the file, so outside collaborators can be invited.
3. A user who has been removed from a team must never edit that team's files by any route, including share links they still hold.

---

## Sub-Task 1 — Write the Alloy 6 Model

**Status:** `[ ] pending`

**Intent:** Create `models/permissions.als` that faithfully models the *current (buggy)* code behavior, with one `assert` per policy rule and a `check <Name> for 4` command for each. This lets the Alloy Analyzer find counterexamples automatically.

**Expected Outcomes:**
- `models/permissions.als` exists and is valid Alloy 6 syntax.
- Three `assert` blocks: `MembersCanEdit`, `ShareLinkHoldersCanEdit`, `RemovedUsersCannotEdit`.
- Three `check` commands: `check MembersCanEdit for 4`, `check ShareLinkHoldersCanEdit for 4`, `check RemovedUsersCannotEdit for 4`.
- The model encodes `can_edit` exactly as written: membership OR share-link, with no removed-user gate on share links.

**Todo List:**
1. Create `models/permissions.als` with sigs: `User`, `Team` (with `members` and `removed` relations to `User`), `File` (with `team` relation to `Team`), `ShareLink` (with `file` and `holder` relations).
2. Add a `fact Consistency` to enforce structural invariants (e.g., members and removed are disjoint, each file belongs to exactly one team).
3. Add a predicate `canEdit[u: User, f: File]` that mirrors the current code: `u in f.team.members OR (some sl: ShareLink | sl.file = f and sl.holder = u)`. Also model that a user can be in both `members` and `removed` simultaneously (e.g. if they were removed then re-added; `members` and `removed` are NOT enforced as disjoint — they reflect what the code actually stores).
4. Add `assert MembersCanEdit`: for all u, f — if `u in f.team.members` then `canEdit[u,f]`. (Rule 1 — inclusive: members may edit, not exclusively)
5. Add `assert ShareLinkHoldersCanEdit`: for all u, f — if a ShareLink exists for (u,f) AND `u not in f.team.removed` then `canEdit[u,f]`. (Rule 2 as clarified: share-link access is valid unless the holder is a removed user — Rule 3 takes priority)
6. Add `assert RemovedUsersCannotEdit`: for all u, f — if `u in f.team.removed` then `not canEdit[u,f]`. (Rule 3 — will be VIOLATED by current model)
7. Add three `check` commands for 4.

**Relevant Context:**
- `demo_app/permissions.py:4` — `can_edit` logic to mirror exactly
- `demo_app/models.py` — Team has `members` and `removed` sets

---

## Sub-Task 2 — Run the Alloy Analyzer

**Status:** `[ ] pending`

**Intent:** Execute the Alloy model using the bundled JAR and interpret the output: SAT = counterexample found (rule violated), UNSAT = rule holds.

**Expected Outcomes:**
- Rules 1 and 2 report UNSAT (hold).
- Rule 3 (`RemovedUsersCannotEdit`) reports SAT with a counterexample showing a removed user with a share link can still edit.
- The output folder path is captured and added to `.gitignore`.

**Todo List:**
1. Run: `java --enable-native-access=ALL-UNNAMED -jar org.alloytools.alloy.dist.jar exec models/permissions.als`
2. Identify the output folder produced by the JAR.
3. Read `receipt.json` in that folder; inspect `skolems` section for the counterexample of `RemovedUsersCannotEdit`.
4. Add the output folder pattern to `.gitignore`.

**Relevant Context:**
- JAR is at `./org.alloytools.alloy.dist.jar`
- Model will be at `models/permissions.als`

---

## Sub-Task 3 — Add a Failing Pytest for the Violated Rule

**Status:** `[ ] pending`

**Intent:** Translate the Alloy counterexample for Rule 3 into a concrete pytest test that demonstrates the bug on the live code, and confirm it fails before any fix is applied.

**Expected Outcomes:**
- New test function `test_removed_member_with_share_link_cannot_edit` added to `demo_app/tests/test_permissions.py`.
- Test scenario: add user to team, create file, create share link for that user, remove user from team, attempt edit → should return 403 but currently returns 200.
- Running `pytest demo_app/tests/test_permissions.py` shows this new test FAILING and all prior tests passing.

**Todo List:**
1. Add `test_removed_member_with_share_link_cannot_edit` to `demo_app/tests/test_permissions.py`:
   - Create a team, add "eve" as member.
   - Create a file in that team.
   - Create a share link for "eve" on that file.
   - Remove "eve" from the team.
   - Assert `_edit(file_id, "eve") == 403` (currently returns 200 — test fails).
2. Run `pytest demo_app/tests/test_permissions.py -v` and verify only the new test fails.

**Relevant Context:**
- Existing helpers `_create_team`, `_add_member`, `_create_file`, `_create_share_link`, `_edit` are already in the test file at `demo_app/tests/test_permissions.py:21-50`.
- `demo_app/main.py:56-65` shows the remove endpoint.

---

## Sub-Task 4 — Fix the Code

**Status:** `[ ] pending`

**Intent:** Apply the minimal fix to `demo_app/permissions.py` so that Rule 3 holds: a removed user is denied edit access even if they hold a share link.

**Expected Outcomes:**
- `can_edit` now returns `False` immediately if the user is in `team.removed`, before checking share links.
- All five existing tests still pass.
- The new test from Sub-Task 3 now passes.
- No other code changes are needed.

**Todo List:**
1. In `demo_app/permissions.py`, after the `team` lookup, add an early-return guard: `if user_id in team.removed: return False`.
2. Run `pytest demo_app/tests/test_permissions.py -v` and confirm all five tests pass.

**Relevant Context:**
- Fix site: `demo_app/permissions.py:14-19` — insert guard after `team` is looked up, before the membership check.
- `team.removed` is already populated by `main.py:64` when a member is removed.

---

## Sub-Task 5 — Update the Alloy Model to Match Fixed Code

**Status:** `[ ] pending`

**Intent:** Update `canEdit` in `models/permissions.als` to mirror the fixed code, so that all three checks now return UNSAT (no counterexample).

**Expected Outcomes:**
- `canEdit` predicate in the Alloy model now includes: `u not in f.team.removed` as a precondition for share-link access (or equivalently: if `u in f.team.removed` then `canEdit` is false regardless).
- Re-running the Alloy Analyzer produces UNSAT for all three checks.

**Todo List:**
1. Update `canEdit` in `models/permissions.als` to add a removed-user guard: access is only possible if `u not in f.team.removed`, then either membership OR share link.
2. Re-run: `java --enable-native-access=ALL-UNNAMED -jar org.alloytools.alloy.dist.jar exec models/permissions.als`
3. Confirm all three checks are UNSAT.

**Relevant Context:**
- `models/permissions.als` written in Sub-Task 1, updated here.

---

## Sub-Task 6 — Write report.md

**Status:** `[ ] pending`

**Intent:** Produce a clear summary document capturing the full verification cycle.

**Expected Outcomes:**
- `report.md` exists at the project root.
- Contains: each rule, verdict before fix, verdict after fix, plain-English counterexample, test added, and code fix applied.

**Todo List:**
1. Create `report.md` with a table or section per rule.
2. For Rule 3: describe the counterexample (removed user "eve" holds a share link; can_edit returns True because the share-link path has no removed-user check), the test added (`test_removed_member_with_share_link_cannot_edit`), and the one-line fix (`if user_id in team.removed: return False`).
3. For Rules 1 and 2: confirm they were UNSAT both before and after (no violation, no fix needed).

**Relevant Context:**
- All information gathered in Sub-Tasks 1–5.
