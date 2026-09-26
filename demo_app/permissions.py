from demo_app import models


def can_edit(user_id: str, file_id: str) -> bool:
    """Return True if the user may edit the file.

    Grants access if the user is a current member of the file's owning team
    OR if the user holds any share link for that file.
    """
    f = models.files.get(file_id)
    if f is None:
        return False

    team = models.teams.get(f.team_id)
    if team is None:
        return False

    if user_id in team.members:
        return True

    return any(
        sl.holder_id == user_id
        for sl in models.share_links.values()
        if sl.file_id == file_id
    )
