from fastapi import Depends, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User


def current_user(
    x_internal_key: str = Header(default=""),
    x_user_id: str = Header(default=""),
    x_user_email: str = Header(default=""),
    x_user_name: str = Header(default=""),
    x_user_role: str = Header(default="explorer"),
    x_user_department: str = Header(default="General"),
    db: Session = Depends(get_db),
) -> User:
    """Identity is asserted by the web app's route handlers, which hold the session.

    The shared internal key prevents direct callers from spoofing headers.
    """
    if x_internal_key != settings.internal_key:
        raise HTTPException(status_code=401, detail="Missing or invalid internal key")
    if not x_user_id or not x_user_email:
        raise HTTPException(status_code=401, detail="Missing user identity")
    user = db.get(User, x_user_id)
    if user is None:
        user = User(id=x_user_id, email=x_user_email, name=x_user_name or x_user_email, role=x_user_role, department=x_user_department)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            # Two first requests from the same browser can race on a fresh database; the other one won.
            db.rollback()
            user = db.get(User, x_user_id)
            if user is None:
                raise
    elif (user.name, user.role, user.department) != (x_user_name or user.name, x_user_role, x_user_department):
        user.name = x_user_name or user.name
        user.role = x_user_role
        user.department = x_user_department
        db.commit()
    return user
