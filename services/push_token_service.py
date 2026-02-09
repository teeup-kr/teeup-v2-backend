from datetime import datetime

from sqlalchemy.orm import Session

from models import UserDeviceToken


def sync_user_push_token(
    db: Session,
    user_id: int,
    push_token: str,
    token_type: str = "FCM",
    enabled: bool = True,
) -> UserDeviceToken:
    now = datetime.now()
    token_row = db.query(UserDeviceToken).filter(UserDeviceToken.push_token == push_token).first()

    if token_row:
        token_row.user_id = user_id
        token_row.token_type = token_type
        token_row.is_active = enabled
        token_row.last_synced_at = now
    else:
        token_row = UserDeviceToken(
            user_id=user_id,
            push_token=push_token,
            token_type=token_type,
            is_active=enabled,
            last_synced_at=now,
        )
        db.add(token_row)

    db.commit()
    db.refresh(token_row)
    return token_row


def deactivate_user_push_tokens(db: Session, user_id: int, push_token: str | None = None) -> int:
    now = datetime.now()
    query = db.query(UserDeviceToken).filter(
        UserDeviceToken.user_id == user_id,
        UserDeviceToken.is_active.is_(True),
    )

    if push_token:
        query = query.filter(UserDeviceToken.push_token == push_token)

    token_rows = query.all()
    for token_row in token_rows:
        token_row.is_active = False
        token_row.last_synced_at = now

    db.commit()
    return len(token_rows)
