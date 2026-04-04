from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, require_admin
from app.repositories.user_repo import get_all_users, deactivate_user
from app.repositories.chat_repo import clean_expired_cache
from app.schemas.user import UserOut
import subprocess, os, tempfile
from fastapi import UploadFile, File

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

@router.post("/restore-db")
async def restore_db(
    file: UploadFile = File(...),
):
    db_url = os.getenv('DATABASE_URL')
    content = await file.read()
    
    with tempfile.NamedTemporaryFile(suffix='.sql', delete=False) as f:
        f.write(content)
        tmp_path = f.name
    
    try:
        # Drop all tables first
        drop_result = subprocess.run(
            ['psql', db_url, '-c', 
             'DROP SCHEMA public CASCADE; CREATE SCHEMA public; CREATE EXTENSION IF NOT EXISTS vector;'],
            capture_output=True, text=True
        )
        
        # Restore
        result = subprocess.run(
            ['psql', db_url, '-f', tmp_path],
            capture_output=True, text=True, timeout=300
        )
        return {
            "returncode": result.returncode,
            "drop": drop_result.stderr[-500:],
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-1000:]
        }
    finally:
        os.unlink(tmp_path)