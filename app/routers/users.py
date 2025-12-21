from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import UserResponse
from app.models import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Obtiene la información del usuario actual"""
    return current_user

@router.get("/search", response_model=UserResponse)
def search_user(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Busca un usuario por ID o email"""
    # Intentar buscar por ID
    if identifier.isdigit():
        user = db.query(User).filter(User.id == int(identifier)).first()
    else:
        # Buscar por email
        user = db.query(User).filter(User.email == identifier).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return user
