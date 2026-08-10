from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.core.rbac import MemberRole, ROLE_PERMISSIONS, role_has_permission
from app.core.security import decode_access_token
from app.core.utils import slugify
from app.db.session import get_db
from app.models import OrganizationMember, User

bearer_scheme = HTTPBearer(auto_error=False)

__all__ = ["slugify", "get_current_user", "get_membership", "require_permission", "permissions_for_role"]


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or missing")
    return user


def get_membership(
    organization_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationMember:
    membership = (
        db.query(OrganizationMember)
        .options(joinedload(OrganizationMember.organization))
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
        )
        .first()
    )
    if not membership and not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")
    if membership is None:
        # Synthetic admin membership for superusers
        membership = OrganizationMember(
            organization_id=organization_id,
            user_id=user.id,
            role=MemberRole.ADMIN.value,
            is_default=False,
        )
    return membership


def require_permission(permission: str):
    def _dependency(membership: OrganizationMember = Depends(get_membership)) -> OrganizationMember:
        if not role_has_permission(membership.role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return membership

    return _dependency


def permissions_for_role(role: str | MemberRole) -> list[str]:
    try:
        member_role = MemberRole(role)
    except ValueError:
        return []
    return sorted(ROLE_PERMISSIONS.get(member_role, set()))
