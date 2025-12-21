from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas import AporteCreate, AporteResponse, AporteUpdate, AporteWithNatillera
from app.models import User
from app.auth.dependencies import get_current_user
from app.services.aporte_service import AporteService

router = APIRouter(prefix="/aportes", tags=["aportes"])

@router.post("/", response_model=AporteResponse, status_code=status.HTTP_201_CREATED)
def create_aporte(
    aporte: AporteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crea un nuevo aporte"""
    return AporteService.create_aporte(db, aporte, current_user)

@router.get("/my-aportes", response_model=List[AporteWithNatillera])
def get_my_aportes(
    natillera_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene los aportes del usuario actual"""
    return AporteService.get_user_aportes(db, current_user, natillera_id)

@router.get("/natillera/{natillera_id}", response_model=List[AporteResponse])
def get_natillera_aportes(
    natillera_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene todos los aportes de una natillera (solo creador)"""
    return AporteService.get_natillera_aportes(db, natillera_id, current_user)

@router.patch("/{aporte_id}", response_model=AporteResponse)
def update_aporte_status(
    aporte_id: int,
    update: AporteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualiza el estado de un aporte (aprobar/rechazar)"""
    return AporteService.update_aporte_status(db, aporte_id, update, current_user)

@router.get("/natillera/{natillera_id}/pendientes/count", response_model=dict)
def get_aportes_pendientes_count(
    natillera_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cuenta los aportes pendientes de una natillera (solo creador)"""
    from app.models import Natillera, Aporte, AporteStatus
    natillera = db.query(Natillera).filter(Natillera.id == natillera_id).first()
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    if natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede ver los conteos")
    
    count = db.query(Aporte).filter(
        Aporte.natillera_id == natillera_id,
        Aporte.status == AporteStatus.PENDIENTE
    ).count()
    return {"count": count}

@router.get("/my-aportes/aprobados/count", response_model=dict)
def get_aportes_aprobados_count(
    natillera_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cuenta los aportes aprobados del usuario actual"""
    from app.models import Aporte, AporteStatus
    query = db.query(Aporte).filter(
        Aporte.user_id == current_user.id,
        Aporte.status == AporteStatus.APROBADO
    )
    if natillera_id:
        query = query.filter(Aporte.natillera_id == natillera_id)
    count = query.count()
    return {"count": count}
