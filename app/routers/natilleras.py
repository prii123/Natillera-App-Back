from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import NatilleraCreate, NatilleraResponse, NatilleraWithMembers, NatilleraUpdate
from app.models import User
from app.auth.dependencies import get_current_user
from app.services.natillera_service import NatilleraService

router = APIRouter(prefix="/natilleras", tags=["natilleras"])

@router.post("/", response_model=NatilleraResponse, status_code=status.HTTP_201_CREATED)
def create_natillera(
    natillera: NatilleraCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crea una nueva natillera"""
    return NatilleraService.create_natillera(db, natillera, current_user)

@router.get("/", response_model=List[NatilleraResponse])
def get_my_natilleras(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene todas las natilleras del usuario actual"""
    return NatilleraService.get_user_natilleras(db, current_user)

@router.get("/activas", response_model=List[NatilleraResponse])
def get_my_active_natilleras(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene solo las natilleras activas del usuario actual"""
    return NatilleraService.get_user_active_natilleras(db, current_user)

@router.get("/created", response_model=List[NatilleraResponse])
def get_created_natilleras(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene las natilleras creadas por el usuario actual"""
    return NatilleraService.get_created_natilleras(db, current_user)

@router.get("/{natillera_id}", response_model=NatilleraWithMembers)
def get_natillera(
    natillera_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene una natillera por ID"""
    natillera = NatilleraService.get_natillera_by_id(db, natillera_id)
    if not natillera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Natillera no encontrada")
    
    # Verificar que el usuario es miembro
    if not NatilleraService.is_member(natillera, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No eres miembro de esta natillera")
    
    # Si el usuario NO es el creador, devolver la natillera sin la lista de miembros
    if natillera.creator_id != current_user.id:
        # Crear una respuesta personalizada sin miembros
        natillera_data = NatilleraWithMembers.from_orm(natillera)
        # Convertir a dict para modificar
        natillera_dict = natillera_data.dict()
        natillera_dict['members'] = []
        return natillera_dict
    
    # Si es el creador, devolver toda la información
    return natillera

@router.post("/{natillera_id}/members/{user_id}")
def add_member(
    natillera_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Envía una invitación a un usuario para unirse a la natillera"""
    return NatilleraService.add_member_to_natillera(db, natillera_id, user_id, current_user)

@router.patch("/{natillera_id}", response_model=NatilleraResponse)
def update_natillera(
    natillera_id: int,
    natillera_update: NatilleraUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualiza una natillera (incluyendo su estado)"""
    natillera = NatilleraService.get_natillera_by_id(db, natillera_id)
    if not natillera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Natillera no encontrada")
    
    # Solo el creador puede actualizar
    if natillera.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el creador puede actualizar la natillera")
    
    # Actualizar campos
    if natillera_update.estado is not None:
        from app.models import NatilleraEstado
        natillera.estado = NatilleraEstado(natillera_update.estado.value)
    if natillera_update.name is not None:
        natillera.name = natillera_update.name
    if natillera_update.monthly_amount is not None:
        natillera.monthly_amount = natillera_update.monthly_amount
    
    db.commit()
    db.refresh(natillera)
    return natillera

@router.get("/{natillera_id}/estadisticas")
def get_natillera_estadisticas(
    natillera_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene estadísticas de una natillera"""
    from app.models import Aporte, AporteStatus
    from sqlalchemy import func
    
    natillera = NatilleraService.get_natillera_by_id(db, natillera_id)
    if not natillera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Natillera no encontrada")
    
    # Verificar que el usuario es miembro
    if not NatilleraService.is_member(natillera, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No eres miembro de esta natillera")
    
    # Calcular total ahorrado por el usuario actual (aportes aprobados)
    total_ahorrado = db.query(func.sum(Aporte.amount)).filter(
        Aporte.natillera_id == natillera_id,
        Aporte.user_id == current_user.id,
        Aporte.status == AporteStatus.APROBADO
    ).scalar() or 0
    
    # Calcular total global ahorrado por todos los usuarios (aportes aprobados)
    total_global_ahorrado = db.query(func.sum(Aporte.amount)).filter(
        Aporte.natillera_id == natillera_id,
        Aporte.status == AporteStatus.APROBADO
    ).scalar() or 0
    
    # Contar aportes pendientes del usuario actual
    aportes_pendientes = db.query(func.count(Aporte.id)).filter(
        Aporte.natillera_id == natillera_id,
        Aporte.user_id == current_user.id,
        Aporte.status == AporteStatus.PENDIENTE
    ).scalar() or 0
    
    return {
        "total_ahorrado": float(total_ahorrado),
        "total_global_ahorrado": float(total_global_ahorrado),
        "aportes_pendientes": aportes_pendientes,
        "es_creador": natillera.creator_id == current_user.id
    }

@router.get("/{natillera_id}/participacion")
def get_natillera_participacion(
    natillera_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene estadísticas de participación de cada miembro en la natillera"""
    from app.models import Aporte, AporteStatus
    from sqlalchemy import func
    
    natillera = NatilleraService.get_natillera_by_id(db, natillera_id)
    if not natillera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Natillera no encontrada")
    
    # Verificar que el usuario es creador
    if natillera.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el creador puede ver esta información")
    
    # Calcular total global ahorrado
    total_global = db.query(func.sum(Aporte.amount)).filter(
        Aporte.natillera_id == natillera_id,
        Aporte.status == AporteStatus.APROBADO
    ).scalar() or 0
    
    # Calcular total por cada miembro
    participacion = []
    for miembro in natillera.members:
        total_miembro = db.query(func.sum(Aporte.amount)).filter(
            Aporte.natillera_id == natillera_id,
            Aporte.user_id == miembro.id,
            Aporte.status == AporteStatus.APROBADO
        ).scalar() or 0
        
        porcentaje = (float(total_miembro) / float(total_global) * 100) if total_global > 0 else 0
        
        participacion.append({
            "user_id": miembro.id,
            "full_name": miembro.full_name,
            "username": miembro.username,
            "total_aportado": float(total_miembro),
            "porcentaje": round(porcentaje, 2)
        })
    
    # Ordenar por mayor aporte
    participacion.sort(key=lambda x: x["total_aportado"], reverse=True)
    
    return {
        "total_global": float(total_global),
        "participacion": participacion
    }
