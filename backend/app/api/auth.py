from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, permissions_for_role
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas import ActiveContextOut, LoginRequest, TokenResponse, UserOut
from app.services.bootstrap import get_default_context

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    token = create_access_token(user.id, {"email": user.email})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=ActiveContextOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ActiveContextOut:
    membership, brand = get_default_context(db, user)
    role = membership.role if membership else None
    return ActiveContextOut(
        user=UserOut.model_validate(user),
        organization=membership.organization if membership else None,
        brand=brand,
        role=role,
        permissions=permissions_for_role(role) if role else [],
    )


@router.post("/logout")
def logout(user: User = Depends(get_current_user)) -> dict:
    # JWT is client-managed in Phase 1; endpoint exists for safe client logout flows.
    return {"status": "ok", "user_id": user.id}
