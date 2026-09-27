# DesignProof Report — Permission Policy Verification

## Summary

Three policy rules from `policy/permission_policy.md` were checked against
`demo_app/` using the Alloy 6 Analyzer. Two violations were found and fixed.

---

## Results Table

| # | Rule | Before any fix | After fix 1 | After fix 2 |
|---|------|---------------|-------------|-------------|
| 1 | Current members of a file's owning team may edit that file. | **UNSAT ✅** | **SAT ❌** (re-add broken) | **UNSAT ✅** |
| 2 | A share link lets its holder edit the file (unless they are a removed user). | **UNSAT ✅** | **UNSAT ✅** | **UNSAT ✅** |
| 3 | A removed user must never edit that team's files by any route, including share links they still hold. | **SAT ❌** | **UNSAT ✅** | **UNSAT ✅** |

> **SAT** = the Alloy Analyzer found a counterexample → rule is violated.
> **UNSAT** = no counterexample exists → rule holds for all instances up to scope 4.
>
> "After fix 1" is the state after adding the `removed` guard to `can_edit`
> but before fixing `add_member`. Rule 1's SAT result at that stage was found
> by **code analysis and direct runtime testing** (not by a second Alloy run —
> see note below).

---

## Violation 1 — Rule 3: Removed user retains edit access via share link

### How it was found

Alloy check `RemovedUsersCannotEdit for 4` returned **SAT** on the first run
against the original (buggy) Alloy model, which faithfully mirrored the
original `can_edit` code.

### Counterexample (plain English)

The Alloy Analyzer (`check RemovedUsersCannotEdit for 4`) produced the
following witness instance (from `permissions/receipt.json`, `skolems` section):

- Witness user: `User$0`; witness file: `File$0`.
- `File$0` belongs to team `Team$3`, where `User$0` is in `removed` and
  **not** in `members`.
- A `ShareLink` exists with `file = File$0` and `holder = User$0`.

In this state, `can_edit("User$0", "File$0")` returns **True** because the
share-link branch of the `or` succeeds — `team.removed` is never consulted.

In concrete terms: Eve is added to a team, receives a share link to one of
the team's files, is then removed from the team, and can still edit that
file via the share link. Rule 3 is violated.

### Test added

`demo_app/tests/test_permissions.py::test_removed_member_with_share_link_cannot_edit`

```python
def test_removed_member_with_share_link_cannot_edit():
    team_id = _create_team()
    _add_member(team_id, "eve")
    file_id = _create_file(team_id)
    _create_share_link(file_id, "eve")              # share link granted while member
    client.delete(f"/teams/{team_id}/members/eve")  # then removed
    assert _edit(file_id, "eve") == 403             # must be denied
```

Before the fix this test returned `200` (edit was permitted — bug confirmed).

### Fix 1 applied

**File:** `demo_app/permissions.py`

Added an early-return guard immediately after the team lookup, before the
membership and share-link checks:

```python
# Rule 3: removed users are denied via every route, including share links.
if user_id in team.removed:
    return False
```

---

## Violation 2 — Rule 1: Re-added member is incorrectly blocked

### How it was found

**This violation was found by code reading and direct runtime testing, not by
an Alloy SAT result.** After applying fix 1, the Alloy model had not yet been
updated. Before updating it, the following was observed by reading
`add_member` in `main.py`: it calls `team.members.add(user_id)` but does
**not** call `team.removed.discard(user_id)`. This means a removed user who
is re-added ends up in both `members` and `removed` simultaneously. A direct
Python test confirmed this returns 403 instead of the required 200.

The Alloy model was subsequently updated to add `fact MembersRemovedDisjoint`
(reflecting the fixed invariant); the updated model's `check MembersCanEdit`
returned **UNSAT**, confirming the fix is sound.

### Counterexample (plain English)

- Frank is added to a team and can edit (200).
- Frank is removed: `removed = {frank}`, `members = {}`.
- Frank is re-added: `members = {frank}`, but `removed = {frank}` is not
  cleared.
- `can_edit` hits `if user_id in team.removed: return False` and denies Frank,
  even though he is now a current member. Rule 1 is violated.

### Test added

`demo_app/tests/test_permissions.py::test_readded_member_can_edit`

```python
def test_readded_member_can_edit():
    team_id = _create_team()
    _add_member(team_id, "frank")
    file_id = _create_file(team_id)
    assert _edit(file_id, "frank") == 200       # member can edit
    client.delete(f"/teams/{team_id}/members/frank")
    _add_member(team_id, "frank")               # re-added
    assert _edit(file_id, "frank") == 200       # must be allowed again
```

Before fix 2 this test returned `403` (bug confirmed).

### Fix 2 applied

**File:** `demo_app/main.py`, `add_member` endpoint

Added one line to clear `removed` when a user is (re-)added to a team:

```python
team.members.add(body.user_id)
team.removed.discard(body.user_id)   # <- added: clear removed on re-add
```

After this fix `members` and `removed` are always disjoint after any
`add_member` call, which is also reflected as a `fact MembersRemovedDisjoint`
in the updated Alloy model.

---

## Final State

### All tests pass

```
demo_app/tests/test_permissions.py::test_team_member_can_edit                         PASSED
demo_app/tests/test_permissions.py::test_non_member_cannot_edit                       PASSED
demo_app/tests/test_permissions.py::test_share_link_holder_can_edit                   PASSED
demo_app/tests/test_permissions.py::test_removing_member_revokes_access               PASSED
demo_app/tests/test_permissions.py::test_readded_member_can_edit                      PASSED
demo_app/tests/test_permissions.py::test_removed_member_with_share_link_cannot_edit   PASSED

6 passed
```

### All Alloy checks are UNSAT (fixed model)

```
00. check MembersCanEdit           UNSAT
01. check ShareLinkHoldersCanEdit  UNSAT
02. check RemovedUsersCannotEdit   UNSAT
```

---

## Files changed

| File | Change |
|------|--------|
| `demo_app/permissions.py` | Added `if user_id in team.removed: return False` guard |
| `demo_app/main.py` | Added `team.removed.discard(body.user_id)` in `add_member` |
| `demo_app/tests/test_permissions.py` | Added `test_readded_member_can_edit` and `test_removed_member_with_share_link_cannot_edit` |
| `models/permissions.als` | Created (buggy model); updated to fixed model with `fact MembersRemovedDisjoint` |
| `.gitignore` | Added `permissions/` (Alloy output folder) |
