-- DesignProof: Alloy 6 model of demo_app/permissions.py (ORIGINAL BUGGY code)
--
-- Original (buggy) canEdit logic (before either fix):
--   if user in team.members -> True
--   elif user holds any share link for the file -> True   ← no removed check!
--   else -> False
--
-- Original (buggy) add_member logic:
--   team.members.add(user)
--   (team.removed was NOT cleared — removed.discard was missing)
--
-- Because add_member did NOT clear removed, a user could end up in BOTH
-- members and removed simultaneously (e.g. removed, then re-added without
-- clearing).  No disjoint fact here — that is intentional.

sig User {}

sig Team {
    members : set User,   -- current member set
    removed : set User    -- ex-member set; NOT enforced disjoint (bug)
}

sig File {
    team : one Team
}

sig ShareLink {
    file   : one File,
    holder : one User
}

-- No MembersRemovedDisjoint fact: the buggy add_member never cleared removed,
-- so overlap was possible in practice.

-- Mirror of the ORIGINAL (buggy) demo_app/permissions.py:can_edit.
-- Share links grant access unconditionally — team.removed is never consulted.
pred canEdit [u : User, f : File] {
    u in f.team.members
    or
    (some sl : ShareLink | sl.file = f and sl.holder = u)
}

-- Rule 1: Current members may edit their team's files.
assert MembersCanEdit {
    all u : User, f : File |
        u in f.team.members => canEdit[u, f]
}

-- Rule 2: A share-link holder may edit the file (unless removed — Rule 3 takes
-- priority, but the buggy code does not enforce this).
assert ShareLinkHoldersCanEdit {
    all u : User, f : File |
        (some sl : ShareLink | sl.file = f and sl.holder = u)
        and u not in f.team.removed
        => canEdit[u, f]
}

-- Rule 3: A removed user must NEVER edit the team's files by any route.
-- This check will return SAT (counterexample found) because canEdit lets
-- removed users through via the share-link branch.
assert RemovedUsersCannotEdit {
    all u : User, f : File |
        u in f.team.removed => not canEdit[u, f]
}

check MembersCanEdit           for 4
check ShareLinkHoldersCanEdit  for 4
check RemovedUsersCannotEdit   for 4
