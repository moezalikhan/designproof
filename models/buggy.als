sig User {}
sig Team { members: set User }
sig Link { holder: one User }
sig File { owner: one Team, links: set Link }

pred canEdit[u: User, f: File] {
  u in f.owner.members or some l: f.links | l.holder = u
}

assert OnlyMembersCanEdit {
  all u: User, f: File | canEdit[u, f] implies u in f.owner.members
}

check OnlyMembersCanEdit for 4
