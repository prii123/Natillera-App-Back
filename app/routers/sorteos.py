from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from app.database import get_db
from app.schemas import SorteoCreate, SorteoResponse, SorteoFinalizadoResponse, BilleteLoteriaResponse, BilleteLoteriaAdmin, FinalizarSorteoRequest
from app.models import User
from app.auth.dependencies import get_current_user
from app.services.sorteo_service import SorteoService

router = APIRouter(prefix="/sorteos", tags=["sorteos"])

@router.post("/", response_model=SorteoResponse, status_code=status.HTTP_201_CREATED)
def create_sorteo(
    sorteo: SorteoCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crea un nuevo sorteo"""
    print(f"Datos recibidos: {sorteo}")
    print(f"Usuario: {current_user.id}")
    return SorteoService.create_sorteo(db, sorteo, current_user)

@router.get("/activos", response_model=List[SorteoResponse])
def get_active_sorteos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene todos los sorteos activos de las natilleras del usuario"""
    return SorteoService.get_active_sorteos_for_user(db, current_user)

@router.get("/finalizados", response_model=Any)
def get_finalized_sorteos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene todos los sorteos finalizados de las natilleras del usuario"""
    print(f"Obteniendo sorteos finalizados para el usuario {current_user.id}")
    result = SorteoService.get_finalized_sorteos_for_user(db, current_user)
    return result

@router.get("/{sorteo_id}", response_model=SorteoResponse)
def get_sorteo(
    sorteo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene un sorteo por ID"""
    sorteo = SorteoService.get_sorteo_by_id(db, sorteo_id)
    if not sorteo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sorteo no encontrado")
    
    # Verificar que el usuario pertenece a la natillera
    if sorteo.natillera_id not in [n.id for n in current_user.natilleras]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a este sorteo")
    
    return sorteo

@router.get("/{sorteo_id}/billetes", response_model=List[BilleteLoteriaResponse])
def get_billetes_loteria(
    sorteo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene todos los billetes de una lotería"""
    # Verificar acceso al sorteo
    sorteo = SorteoService.get_sorteo_by_id(db, sorteo_id)
    if not sorteo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sorteo no encontrado")
    
    if sorteo.natillera_id not in [n.id for n in current_user.natilleras]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a este sorteo")
    
    return SorteoService.get_billetes_loteria(db, sorteo_id)

@router.post("/{sorteo_id}/billetes/{numero}/tomar", response_model=BilleteLoteriaResponse)
def tomar_billete_loteria(
    sorteo_id: int,
    numero: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permite tomar un billete de lotería"""
    return SorteoService.tomar_billete_loteria(db, sorteo_id, numero, current_user)

@router.put("/{sorteo_id}/finalizar", response_model=SorteoResponse)
def finalizar_sorteo(
    sorteo_id: int,
    request: FinalizarSorteoRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Finaliza un sorteo seleccionando un número ganador (aleatoriamente o especificado)"""
    return SorteoService.finalizar_sorteo(db, sorteo_id, current_user, request.numero_ganador)

@router.put("/{sorteo_id}/billetes/{numero}/marcar-pagado", response_model=BilleteLoteriaResponse)
def marcar_billete_pagado(
    sorteo_id: int,
    numero: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marca un billete como pagado (solo para el creador)"""
    return SorteoService.marcar_billete_pagado(db, sorteo_id, numero, current_user)

@router.get("/{sorteo_id}/billetes/admin", response_model=List[BilleteLoteriaResponse])
def get_billetes_admin(
    sorteo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene todos los billetes con información completa para el admin/creador"""
    print(f"Endpoint admin llamado para sorteo {sorteo_id}, usuario {current_user.id}")
    result = SorteoService.get_billetes_admin(db, sorteo_id, current_user)
    print(f"Retornando {len(result)} billetes")
    return result