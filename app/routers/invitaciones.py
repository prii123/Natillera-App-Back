from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import InvitacionResponse, InvitacionCreate
from app.models import User, Invitacion, Natillera, InvitacionEstado
from app.auth.dependencies import get_current_user
from datetime import datetime

router = APIRouter(prefix="/invitaciones", tags=["invitaciones"])

@router.post("/", response_model=InvitacionResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    invitacion: InvitacionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crea una invitación para unirse a una natillera"""
    # Verificar que la natillera existe
    natillera = db.query(Natillera).filter(Natillera.id == invitacion.natillera_id).first()
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    
    # Solo el creador puede enviar invitaciones
    if natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede enviar invitaciones")
    
    # Buscar el usuario por email
    invited_user = db.query(User).filter(User.email == invitacion.invited_email).first()
    if not invited_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado con ese email")
    
    # Verificar que no sea el creador
    if invited_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes invitarte a ti mismo")
    
    # Verificar que no sea ya miembro
    if invited_user in natillera.members:
        raise HTTPException(status_code=400, detail="El usuario ya es miembro de esta natillera")
    
    # Verificar que no haya una invitación pendiente
    existing_invitation = db.query(Invitacion).filter(
        Invitacion.natillera_id == invitacion.natillera_id,
        Invitacion.invited_user_id == invited_user.id,
        Invitacion.estado == InvitacionEstado.PENDIENTE
    ).first()
    if existing_invitation:
        raise HTTPException(status_code=400, detail="Ya hay una invitación pendiente para este usuario")
    
    # Crear invitación
    nueva_invitacion = Invitacion(
        natillera_id=invitacion.natillera_id,
        invited_user_id=invited_user.id,
        inviter_user_id=current_user.id
    )
    
    db.add(nueva_invitacion)
    db.commit()
    db.refresh(nueva_invitacion)
    
    return nueva_invitacion

@router.get("/", response_model=List[InvitacionResponse])
def get_my_invitations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene las invitaciones pendientes del usuario actual"""
    invitaciones = db.query(Invitacion).filter(
        Invitacion.invited_user_id == current_user.id,
        Invitacion.estado == InvitacionEstado.PENDIENTE
    ).all()
    return invitaciones

@router.get("/count", response_model=dict)
def get_invitations_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene el conteo de invitaciones pendientes"""
    count = db.query(Invitacion).filter(
        Invitacion.invited_user_id == current_user.id,
        Invitacion.estado == InvitacionEstado.PENDIENTE
    ).count()
    return {"count": count}

@router.post("/{invitacion_id}/accept", response_model=InvitacionResponse)
def accept_invitation(
    invitacion_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Acepta una invitación a una natillera"""
    invitacion = db.query(Invitacion).filter(Invitacion.id == invitacion_id).first()
    
    if not invitacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitación no encontrada"
        )
    
    # Verificar que la invitación es para el usuario actual
    if invitacion.invited_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta invitación no es para ti"
        )
    
    # Verificar que la invitación está pendiente
    if invitacion.estado != InvitacionEstado.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta invitación ya fue procesada"
        )
    
    # Obtener la natillera
    natillera = db.query(Natillera).filter(Natillera.id == invitacion.natillera_id).first()
    if not natillera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Natillera no encontrada"
        )
    
    # Verificar si ya es miembro
    if current_user not in natillera.members:
        natillera.members.append(current_user)
    
    # Actualizar estado de invitación
    invitacion.estado = InvitacionEstado.ACEPTADA
    invitacion.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(invitacion)
    return invitacion

@router.post("/{invitacion_id}/reject", response_model=InvitacionResponse)
def reject_invitation(
    invitacion_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rechaza una invitación a una natillera"""
    invitacion = db.query(Invitacion).filter(Invitacion.id == invitacion_id).first()
    
    if not invitacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitación no encontrada"
        )
    
    # Verificar que la invitación es para el usuario actual
    if invitacion.invited_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta invitación no es para ti"
        )
    
    # Verificar que la invitación está pendiente
    if invitacion.estado != InvitacionEstado.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta invitación ya fue procesada"
        )
    
    # Actualizar estado de invitación
    invitacion.estado = InvitacionEstado.RECHAZADA
    invitacion.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(invitacion)
    return invitacion

@router.get("/natillera/{natillera_id}/respondidas/count", response_model=dict)
def get_invitaciones_respondidas_count(
    natillera_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cuenta las invitaciones respondidas (aceptadas/rechazadas) de una natillera (solo creador)"""
    from app.models import Natillera
    natillera = db.query(Natillera).filter(Natillera.id == natillera_id).first()
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    if natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede ver los conteos")
    
    count = db.query(Invitacion).filter(
        Invitacion.natillera_id == natillera_id,
        Invitacion.estado.in_([InvitacionEstado.ACEPTADA, InvitacionEstado.RECHAZADA])
    ).count()
    return {"count": count}
