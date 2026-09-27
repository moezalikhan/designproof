-- DesignProof: Alloy 6 model of the codebase AFTER FIX 1 ONLY.
--
-- Fix 1 was applied to demo_app/permissions.py:can_edit:
--   if user in team.removed  -> False   ← guard added
--   elif user in team.members -> True
--   elif user holds any share link for the file -> True
--   else -> False
--
-- Fix 2 was NOT yet applied to demo_app/main.py:add_member:
--   team.members.add(user)
--   (team.removed.discard NOT called — missing until fix 2)
--
-- Because add_member does NOT clear removed, a re-added user can be in BOTH
-- members and removed simultaneously.  The can_edit guard fires on removed
-- first and wrongly denies the now-current member.
-- No MembersRemovedDisjoint fact: overlap is still possible at this stage.

sig User {}

sig Team {
    members : set User,   -- current member set
    removed : set User    -- ex-member set; NOT disjoint (add_member bug still present)
}

sig File {
    team : one Team
}

sig ShareLink {
    file   : one File,
    holder : one User
}

-- No MembersRemovedDisjoint fact: add_member still does not clear removed,
-- so a user re-added after removal ends up in both sets.

-- Mirror of demo_app/permissions.py:can_edit AFTER FIX 1.
-- Removed users are blocked first (guard added), then membership, then share links.
pred canEdit [u : User, f : File] {
    u not in f.team.removed
    and
    (
        u in f.team.members
        or
        (some sl : ShareLink | sl.file = f and sl.holder = u)
    )
}

-- Rule 1: Current members may edit their team's files.
-- SAT: a user in BOTH members and removed is denied by the guard, so this
-- assert is violated — the counterexample is a user who was removed then
-- re-added without clearing removed.
assert MembersCanEdit {
    all u : User, f : File |
        u in f.team.members => canEdit[u, f]
}

-- Rule 2: A share-link holder may edit, unless removed (Rule 3 takes priority).
assert ShareLinkHoldersCanEdit {
    all u : User, f : File |
        (some sl : ShareLink | sl.file = f and sl.holder = u)
        and u not in f.team.removed
        => canEdit[u, f]
}

-- Rule 3: A removed user must never edit by any route.
-- UNSAT: the guard in can_edit now enforces this correctly.
assert RemovedUsersCannotEdit {
    all u : User, f : File |
        u in f.team.removed => not canEdit[u, f]
}

check MembersCanEdit           for 4
check ShareLinkHoldersCanEdit  for 4
check RemovedUsersCannotEdit   for 4
