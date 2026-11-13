from .models import AdminAction, db

ACTIONS = ("login", "create", "update", "delete")


def log_admin(user, action, entity_type, entity_id=None, summary=""):
    if action not in ACTIONS:
        raise ValueError(action)
    text = " ".join(str(summary).split())
    if not text:
        text = action
    db.session.add(AdminAction(
        user_id=user.id if user else None,
        login=user.login if user else "—",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=text[:255],
    ))
