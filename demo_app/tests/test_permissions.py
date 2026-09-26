import pytest
from fastapi.testclient import TestClient

from demo_app.main import app
from demo_app import models


@pytest.fixture(autouse=True)
def clear_store():
    """Reset the in-memory store before every test."""
    models.users.clear()
    models.teams.clear()
    models.files.clear()
    models.share_links.clear()
    yield


client = TestClient(app)


def _create_team() -> str:
    r = client.post("/teams", json={})
    assert r.status_code == 201
    return r.json()["team_id"]


def _add_member(team_id: str, user_id: str):
    r = client.post(f"/teams/{team_id}/members", json={"user_id": user_id})
    assert r.status_code == 200


def _create_file(team_id: str) -> str:
    r = client.post("/files", json={"team_id": team_id, "content": "hello"})
    assert r.status_code == 201
    return r.json()["file_id"]


def _create_share_link(file_id: str, holder_id: str) -> str:
    r = client.post("/share-links", json={"file_id": file_id, "holder_id": holder_id})
    assert r.status_code == 201
    return r.json()["link_id"]


def _edit(file_id: str, user_id: str) -> int:
    r = client.put(
        f"/files/{file_id}",
        json={"content": "updated"},
        headers={"x-user-id": user_id},
    )
    return r.status_code


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_team_member_can_edit():
    team_id = _create_team()
    _add_member(team_id, "alice")
    file_id = _create_file(team_id)
    assert _edit(file_id, "alice") == 200


def test_non_member_cannot_edit():
    team_id = _create_team()
    _add_member(team_id, "alice")
    file_id = _create_file(team_id)
    assert _edit(file_id, "bob") == 403


def test_share_link_holder_can_edit():
    team_id = _create_team()
    _add_member(team_id, "alice")
    file_id = _create_file(team_id)
    _create_share_link(file_id, "carol")   # carol is not a team member
    assert _edit(file_id, "carol") == 200


def test_removing_member_revokes_access():
    team_id = _create_team()
    _add_member(team_id, "dave")
    file_id = _create_file(team_id)
    # Dave can edit while a member
    assert _edit(file_id, "dave") == 200
    # Remove dave from the team
    r = client.delete(f"/teams/{team_id}/members/dave")
    assert r.status_code == 200
    # Dave no longer has a share link, so access is revoked
    assert _edit(file_id, "dave") == 403
