from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import UserResponse
from app.services.user_service import UserService
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class SyncUserRequest(BaseModel):
    firebase_uid: str
    email: str
    username: str
    full_name: str

@router.post("/sync-user", response_model=UserResponse, status_code=status.HTTP_200_OK)
def sync_firebase_user(request: SyncUserRequest, db: Session = Depends(get_db)):
    """
    Sincroniza un usuario de Firebase con la base de datos local.
    Se llama desde el frontend después de que el usuario se registra/autentica en Firebase.
    Crea automáticamente el usuario si no existe.
    """
    # Verificar si el usuario ya existe por Firebase UID
    user = UserService.get_user_by_firebase_uid(db, request.firebase_uid)
    
    if user:
        # Usuario ya existe, retornarlo
        return user
    
    # Verificar si el email ya está en uso por otro firebase_uid
    existing_email = UserService.get_user_by_email(db, request.email)
    if existing_email:
        # El email existe pero con diferente firebase_uid
        # Esto podría ser un problema de configuración de Firebase
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado con otra cuenta"
        )
    
    # Crear nuevo usuario (el servicio manejará username duplicado automáticamente)
    try:
        user = UserService.create_user(
            db=db,
            firebase_uid=request.firebase_uid,
            email=request.email,
            username=request.username,
            full_name=request.full_name
        )
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear usuario: {str(e)}"
        )
