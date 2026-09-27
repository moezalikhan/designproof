-- DesignProof: Alloy 6 model of demo_app/permissions.py (FIXED code)
--
-- Fixed canEdit logic (demo_app/permissions.py):
--   if user in team.removed  -> False  (Rule 3 guard, added in fix 1)
--   elif user in team.members -> True
--   elif user holds any share link for the file -> True
--   else -> False
--
-- Fixed add_member logic (demo_app/main.py):
--   team.members.add(user)
--   team.removed.discard(user)   <- added in fix 2
--
-- Because add_member clears removed, members and removed ARE now disjoint
-- at any point when the system is in a consistent state after add_member.
-- We model this as a fact to match the fixed invariant.

sig User {}

sig Team {
    members : set User,   -- current member set
    removed : set User    -- ex-member set; DISJOINT from members after fix
}

sig File {
    team : one Team
}

sig ShareLink {
    file   : one File,
    holder : one User
}

-- Invariant enforced by the fixed add_member: members and removed are disjoint.
fact MembersRemovedDisjoint {
    all t : Team | no (t.members & t.removed)
}

-- Mirror of fixed demo_app/permissions.py:can_edit.
-- Removed users are blocked first; then membership; then share links.
pred canEdit [u : User, f : File] {
    u not in f.team.removed
    and
    (
        u in f.team.members
        or
        (some sl : ShareLink | sl.file = f and sl.holder = u)
    )
}

-- Rule 1: Current members may edit their team's files (inclusive).
assert MembersCanEdit {
    all u : User, f : File |
        u in f.team.members => canEdit[u, f]
}

-- Rule 2 (with Rule 3 priority): A share-link holder may edit the file,
-- UNLESS they are a removed user of the owning team.
assert ShareLinkHoldersCanEdit {
    all u : User, f : File |
        (some sl : ShareLink | sl.file = f and sl.holder = u)
        and u not in f.team.removed
        => canEdit[u, f]
}

-- Rule 3: A removed user must never edit the team's files by any route,
-- including share links they still hold.
assert RemovedUsersCannotEdit {
    all u : User, f : File |
        u in f.team.removed => not canEdit[u, f]
}

check MembersCanEdit           for 4
check ShareLinkHoldersCanEdit  for 4
check RemovedUsersCannotEdit   for 4
