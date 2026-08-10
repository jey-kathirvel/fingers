from enum import Enum


class MemberRole(str, Enum):
    ADMIN = "admin"
    CREATOR = "creator"
    REVIEWER = "reviewer"
    APPROVER = "approver"
    ANALYST = "analyst"


ROLE_PERMISSIONS: dict[MemberRole, set[str]] = {
    MemberRole.ADMIN: {
        "org:manage",
        "brand:manage",
        "brand:read",
        "user:manage",
        "content:manage",
        "content:approve",
        "publish:manage",
        "analytics:read",
        "integrations:manage",
        "audit:read",
    },
    MemberRole.CREATOR: {
        "brand:read",
        "content:manage",
        "analytics:read",
    },
    MemberRole.REVIEWER: {
        "brand:read",
        "content:manage",
        "content:approve",
        "analytics:read",
    },
    MemberRole.APPROVER: {
        "brand:read",
        "content:approve",
        "publish:manage",
        "analytics:read",
    },
    MemberRole.ANALYST: {
        "brand:read",
        "analytics:read",
    },
}


def role_has_permission(role: MemberRole | str, permission: str) -> bool:
    try:
        member_role = MemberRole(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS.get(member_role, set())
