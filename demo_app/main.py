import uuid
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from demo_app import models
from demo_app.permissions import can_edit

app = FastAPI(title="File Sharing Demo")


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class CreateTeamRequest(BaseModel):
    name: str | None = None

class AddMemberRequest(BaseModel):
    user_id: str

class CreateFileRequest(BaseModel):
    team_id: str
    content: str = ""

class CreateShareLinkRequest(BaseModel):
    file_id: str
    holder_id: str

class EditFileRequest(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

@app.post("/teams", status_code=201)
def create_team(body: CreateTeamRequest | None = None):
    team_id = str(uuid.uuid4())
    models.teams[team_id] = models.Team(id=team_id)
    return {"team_id": team_id}


@app.post("/teams/{team_id}/members", status_code=200)
def add_member(team_id: str, body: AddMemberRequest):
    team = models.teams.get(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    team.members.add(body.user_id)
    # If this user was previously removed, clear that flag so Rule 3 does not
    # block them now that they are a current member again.
    team.removed.discard(body.user_id)
    # ensure the user exists in the users store
    if body.user_id not in models.users:
        models.users[body.user_id] = models.User(id=body.user_id)
    return {"team_id": team_id, "user_id": body.user_id}


@app.delete("/teams/{team_id}/members/{user_id}", status_code=200)
def remove_member(team_id: str, user_id: str):
    team = models.teams.get(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    if user_id not in team.members:
        raise HTTPException(status_code=404, detail="User is not a member")
    team.members.discard(user_id)
    team.removed.add(user_id)
    return {"team_id": team_id, "user_id": user_id, "removed": True}


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

@app.post("/files", status_code=201)
def create_file(body: CreateFileRequest):
    if body.team_id not in models.teams:
        raise HTTPException(status_code=404, detail="Team not found")
    file_id = str(uuid.uuid4())
    models.files[file_id] = models.File(id=file_id, team_id=body.team_id, content=body.content)
    return {"file_id": file_id}


@app.put("/files/{file_id}", status_code=200)
def edit_file(file_id: str, body: EditFileRequest, x_user_id: str = Header(...)):
    if file_id not in models.files:
        raise HTTPException(status_code=404, detail="File not found")
    if not can_edit(x_user_id, file_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    models.files[file_id].content = body.content
    return {"file_id": file_id, "content": body.content}


# ---------------------------------------------------------------------------
# Share links
# ---------------------------------------------------------------------------

@app.post("/share-links", status_code=201)
def create_share_link(body: CreateShareLinkRequest):
    if body.file_id not in models.files:
        raise HTTPException(status_code=404, detail="File not found")
    link_id = str(uuid.uuid4())
    models.share_links[link_id] = models.ShareLink(
        id=link_id,
        file_id=body.file_id,
        holder_id=body.holder_id,
    )
    return {"link_id": link_id}
