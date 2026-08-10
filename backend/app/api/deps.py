from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.core.security import decode_access_token
from app.models import OrganizationMember, Role, User

bearer = HTTPBearer(auto_error=False)
DbDep = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.get(User, UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or missing")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_membership(db: Session, user: User, organization_id: UUID) -> OrganizationMember:
    membership = (
        db.query(OrganizationMember)
        .options(joinedload(OrganizationMember.organization))
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")
    return membership


def require_roles(*roles: Role) -> Callable:
    allowed = set(roles)

    def dependency(
        db: DbDep,
        user: CurrentUser,
        x_organization_id: Annotated[UUID | None, Header(alias="X-Organization-Id")] = None,
    ) -> OrganizationMember:
        if x_organization_id is None:
            raise HTTPException(status_code=400, detail="X-Organization-Id header required")
        membership = get_membership(db, user, x_organization_id)
        if membership.role not in allowed and membership.role != Role.admin:
            raise HTTPException(status_code=403, detail="Insufficient role permissions")
        return membership

    return dependency
