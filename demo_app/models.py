from dataclasses import dataclass, field

@dataclass
class User:
    id: str

@dataclass
class Team:
    id: str
    members: set = field(default_factory=set)   # current member user ids
    removed: set = field(default_factory=set)   # ex-member user ids

@dataclass
class File:
    id: str
    team_id: str
    content: str = ""

@dataclass
class ShareLink:
    id: str
    file_id: str
    holder_id: str   # user id of the share-link holder

# In-memory store
users: dict[str, User] = {}
teams: dict[str, Team] = {}
files: dict[str, File] = {}
share_links: dict[str, ShareLink] = {}
