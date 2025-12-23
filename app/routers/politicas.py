from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import PoliticaCreate, PoliticaResponse, PoliticaUpdate
from app.models import User, Natillera
from app.auth.dependencies import get_current_user
from app.services.politica_service import PoliticaService
from app.services.natillera_service import NatilleraService

router = APIRouter(prefix="/politicas", tags=["politicas"])

@router.get("/natillera/{natillera_id}", response_model=List[PoliticaResponse])
def get_politicas_by_natillera(
    natillera_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene todas las políticas de una natillera"""
    # Verificar que el usuario pertenece a la natillera
    natillera = NatilleraService.get_natillera_by_id(db, natillera_id)
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    
    if current_user.id not in [member.id for member in natillera.members] and natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta natillera")
    
    return PoliticaService.get_politicas_by_natillera(db, natillera_id)

@router.post("/", response_model=PoliticaResponse, status_code=status.HTTP_201_CREATED)
def create_politica(
    politica: PoliticaCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crea una nueva política (solo para creadores de la natillera)"""
    # Verificar que el usuario es el creador de la natillera
    natillera = NatilleraService.get_natillera_by_id(db, politica.natillera_id)
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    
    if natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede gestionar las políticas")
    
    return PoliticaService.create_politica(db, politica)

@router.put("/{politica_id}", response_model=PoliticaResponse)
def update_politica(
    politica_id: int,
    politica_update: PoliticaUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualiza una política (solo para creadores de la natillera)"""
    # Obtener la política
    politica = PoliticaService.get_politica_by_id(db, politica_id)
    if not politica:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    
    # Verificar que el usuario es el creador de la natillera
    if politica.natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede gestionar las políticas")
    
    updated_politica = PoliticaService.update_politica(db, politica_id, politica_update)
    if not updated_politica:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    
    return updated_politica

@router.delete("/{politica_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_politica(
    politica_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Elimina una política (solo para creadores de la natillera)"""
    # Obtener la política
    politica = PoliticaService.get_politica_by_id(db, politica_id)
    if not politica:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    
    # Verificar que el usuario es el creador de la natillera
    if politica.natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede gestionar las políticas")
    
    if not PoliticaService.delete_politica(db, politica_id):
        raise HTTPException(status_code=404, detail="Política no encontrada")

@router.post("/reorder/{natillera_id}")
def reorder_politicas(
    natillera_id: int,
    politica_orders: List[dict],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reordena las políticas de una natillera (solo para creadores)"""
    # Verificar que el usuario es el creador de la natillera
    natillera = NatilleraService.get_natillera_by_id(db, natillera_id)
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    
    if natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede gestionar las políticas")
    
    if not PoliticaService.reorder_politicas(db, natillera_id, politica_orders):
        raise HTTPException(status_code=400, detail="Error al reordenar las políticas")