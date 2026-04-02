from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User, RoleEnum
from app.repositories.user_repo import get_user_by_email, create_user
from app.schemas.user import UserCreate, UserOut, Token

router = APIRouter()


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
)
def register(
    body: UserCreate,
    db  : Session = Depends(get_db),
):
    if get_user_by_email(db, body.email):
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )
    user = User(
        email     = body.email,
        name      = body.name,
        hashed_pw = hash_password(body.password),
        role      = RoleEnum.user,
    )
    return create_user(db, user)


@router.post(
    "/login",
    response_model=Token,
)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db  : Session = Depends(get_db),
):
    user = get_user_by_email(db, form.username)
    if not user or not verify_password(form.password, user.hashed_pw):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )
    token = create_access_token(str(user.id), user.role.value)
    return Token(
        access_token = token,
        token_type   = "bearer",
        user         = UserOut.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserOut,
)
def me(current_user=Depends(get_current_user)):
    return current_user