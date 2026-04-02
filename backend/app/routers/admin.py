from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, require_admin
from app.repositories.user_repo import get_all_users, deactivate_user
from app.repositories.chat_repo import clean_expired_cache
from app.schemas.user import UserOut

router = APIRouter()


@router.get(
    "/users",
    response_model=list[UserOut],
)
def list_all_users(
    db: Session = Depends(get_db),
    _          = Depends(require_admin),
):
    return get_all_users(db)


@router.delete(
    "/users/{user_id}",
    status_code=204,
)
def deactivate(
    user_id: str,
    db     : Session = Depends(get_db),
    _              = Depends(require_admin),
):
    success = deactivate_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")


@router.post(
    "/cache/clean",
    summary="Delete expired AI cache rows",
)
def clean_cache(
    db: Session = Depends(get_db),
    _          = Depends(require_admin),
):
    deleted = clean_expired_cache(db)
    return {"deleted": deleted}