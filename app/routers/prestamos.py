

# Endpoint para ver pagos de un préstamo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models import User, Natillera
from app.schemas import PrestamoCreate, PrestamoUpdate, PrestamoResponse, PrestamoDetalle, PagoRequest, PagoPendienteResponse, PagosPrestamoResponse
from app.services.prestamo_service import PrestamoService

router = APIRouter(prefix="/prestamos", tags=["prestamos"])


# Schema para respuesta de resumen
class ResumenPrestamos(BaseModel):
    total_activos: int
    monto_prestado: Decimal
    monto_por_recuperar: Decimal
    monto_recuperado: Decimal

class PrestamosAgrupadosResponse(BaseModel):
    aprobados: List[PrestamoResponse]
    rechazados: List[PrestamoResponse]
    pendientes: List[PrestamoResponse]

@router.post("/", response_model=PrestamoResponse)
def create_prestamo(
    prestamo: PrestamoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea un nuevo préstamo y genera una transacción asociada.
    El creador de la natillera lo crea como aprobado, los miembros como pendiente.
    """
    natillera = PrestamoService.get_natillera_by_id(db, prestamo.natillera_id)
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    # Permitir que el creador o cualquier miembro cree préstamos
    is_member = PrestamoService.user_is_natillera_member(natillera, current_user)
    if not is_member:
        raise HTTPException(status_code=403, detail="Solo miembros de la natillera pueden crear préstamos")
    try:
        nuevo_prestamo = PrestamoService.create_prestamo(db, prestamo, current_user.id)
        return nuevo_prestamo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/natilleras/{natillera_id}", response_model=PrestamosAgrupadosResponse)
def get_prestamos_by_natillera(
    natillera_id: int,
    estado: Optional[str] = Query(None, description="Filtrar por estado: activo, pagado, vencido, cancelado"),
    referente_id: Optional[int] = Query(None, description="Filtrar por ID del referente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todos los préstamos de una natillera con filtros opcionales.
    Solo miembros de la natillera pueden ver los préstamos.
    """
    # Verificar que la natillera existe y el usuario es miembro
    natillera = PrestamoService.get_natillera_by_id(db, natillera_id)
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    if not PrestamoService.user_is_natillera_member(natillera, current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para ver los préstamos de esta natillera"
        )
    
    prestamos = PrestamoService.get_prestamos_by_natillera(
        db, natillera_id, estado, referente_id
    )

    # Agrupar préstamos por estado de aprobación
    aprobados = [p for p in prestamos if getattr(p, 'aprobado', None) is True]
    rechazados = [p for p in prestamos if getattr(p, 'aprobado', None) is False]
    pendientes = [p for p in prestamos if getattr(p, 'aprobado', None) is None]

    return {
        "aprobados": aprobados,
        "rechazados": rechazados,
        "pendientes": pendientes
    }


@router.get("/{prestamo_id}", response_model=PrestamoDetalle)
def get_prestamo_detalle(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene los detalles completos de un préstamo con cálculos de interés y saldo pendiente.
    """
    prestamo_detalle = PrestamoService.get_prestamo_by_id(db, prestamo_id)
    
    if not prestamo_detalle:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    # Verificar que el usuario tiene permiso para ver este préstamo
    natillera = PrestamoService.get_natillera_by_id(db, prestamo_detalle.natillera_id)
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    if not PrestamoService.user_is_natillera_member(natillera, current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para ver este préstamo"
        )
    
    return prestamo_detalle


@router.patch("/{prestamo_id}", response_model=PrestamoResponse)
def update_prestamo(
    prestamo_id: int,
    prestamo_update: PrestamoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza un préstamo (estado, monto pagado, notas).
    Solo el creador de la natillera puede actualizar préstamos.
    """
    # Verificar que el préstamo existe
    prestamo_obj = PrestamoService.get_prestamo_by_id_simple(db, prestamo_id)
    if not prestamo_obj:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    natillera = PrestamoService.get_natillera_by_id(db, prestamo_obj.natillera_id)
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    if not PrestamoService.user_is_natillera_creator(natillera, current_user):
        raise HTTPException(
            status_code=403,
            detail="Solo el creador de la natillera puede actualizar préstamos"
        )
    
    try:
        prestamo_actualizado = PrestamoService.update_prestamo(
            db, prestamo_id, prestamo_update, current_user.id
        )
        
        if not prestamo_actualizado:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")
        
        return prestamo_actualizado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{prestamo_id}/pagos", response_model=PagosPrestamoResponse)
def get_pagos_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Devuelve el historial de pagos de un préstamo.
    El creador de la natillera puede ver todos los pagos. Un miembro solo puede ver los pagos si es el referente del préstamo.
    """
    # print("Entrando a get_pagos_prestamo", current_user)
    from app.services.prestamo_service import PrestamoService
    pagos = PrestamoService.get_pagos_prestamo_autorizado(db, prestamo_id, current_user)
    # print(pagos)
    return pagos

@router.post("/{prestamo_id}/pagos", response_model=PrestamoResponse)
def registrar_pago_prestamo(
    prestamo_id: int,
    pago_request: PagoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registra un pago parcial o total de un préstamo.
    Los miembros pueden registrar pagos pendientes, el creador puede registrar pagos directamente.
    """
    
    prestamo = PrestamoService.get_prestamo_by_id_simple(db, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    natillera = PrestamoService.get_natillera_by_id(db, prestamo.natillera_id)
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    is_creator = PrestamoService.user_is_natillera_creator(natillera, current_user)
    is_member = PrestamoService.user_is_natillera_member(natillera, current_user)
    if not is_member:
        raise HTTPException(
            status_code=403,
            detail="Solo miembros de la natillera pueden registrar pagos"
        )
    
    try:
        prestamo_actualizado = PrestamoService.registrar_pago(
            db, prestamo_id, pago_request.monto_pago, current_user.id
        )
        return prestamo_actualizado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/pagos/{pago_id}/aprobar", response_model=PrestamoResponse)
def aprobar_pago_pendiente(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aprueba un pago pendiente de un préstamo (solo el creador de la natillera puede hacerlo).
    """
    try:
        prestamo_actualizado = PrestamoService.aprobar_pago_pendiente(db, pago_id, current_user.id)
        return prestamo_actualizado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{prestamo_id}/aprobar", response_model=PrestamoResponse)
def aprobar_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aprueba un préstamo (solo el creador de la natillera puede hacerlo).
    Crea la transacción de ingreso por intereses si no existe.
    """
    try:
        prestamo_aprobado = PrestamoService.aprobar_prestamo(db, prestamo_id, current_user.id)
        return prestamo_aprobado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{prestamo_id}/rechazar", response_model=PrestamoResponse)
def rechazar_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rechaza un préstamo pendiente (solo el creador de la natillera puede hacerlo).
    """
    try:
        prestamo_rechazado = PrestamoService.rechazar_prestamo(db, prestamo_id, current_user.id)
        return prestamo_rechazado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pagos/pendientes", response_model=List[PagoPendienteResponse])
def get_pagos_pendientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todos los pagos pendientes de aprobación para las natilleras donde el usuario es creador.
    """
    try:
        pagos_pendientes = PrestamoService.get_pagos_pendientes_por_creador(db, current_user.id)
        return pagos_pendientes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/natilleras/{natillera_id}/resumen", response_model=ResumenPrestamos)
def get_resumen_prestamos(
    natillera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene el resumen agregado de préstamos de una natillera (optimizado).
    Retorna estadísticas calculadas en el backend para mejor rendimiento.
    """
    # Verificar que la natillera existe y el usuario es miembro
    natillera = PrestamoService.get_natillera_by_id(db, natillera_id)
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    if not PrestamoService.user_is_natillera_member(natillera, current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para ver el resumen de esta natillera"
        )
    
    resumen = PrestamoService.get_resumen_prestamos(db, natillera_id)
    return resumen

@router.get("/natillera/{natillera_id}/pendientes/count", response_model=dict)
def get_prestamos_pendientes_count(
    natillera_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cuenta los préstamos pendientes de una natillera (solo creador)"""
    from app.models import Prestamo
    natillera = PrestamoService.get_natillera_by_id(db, natillera_id)
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    if natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede ver los conteos")
    
    count = db.query(Prestamo).filter(
        Prestamo.natillera_id == natillera_id,
        Prestamo.aprobado.is_(None)
    ).count()
    return {"count": count}

@router.get("/my-prestamos/aprobados/count", response_model=dict)
def get_prestamos_aprobados_count(
    natillera_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cuenta los préstamos aprobados del usuario actual"""
    from app.models import Prestamo, EstadoPrestamo
    query = db.query(Prestamo).filter(
        Prestamo.referente_id == current_user.id,
        Prestamo.estado == EstadoPrestamo.ACTIVO
    )
    if natillera_id:
        query = query.filter(Prestamo.natillera_id == natillera_id)
    count = query.count()
    return {"count": count}

@router.get("/pagos/natillera/{natillera_id}/pendientes/count", response_model=dict)
def get_pagos_pendientes_count(
    natillera_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cuenta los pagos pendientes de una natillera (solo creador)"""
    from app.models import PagoPrestamo, EstadoPago, Prestamo
    natillera = PrestamoService.get_natillera_by_id(db, natillera_id)
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    if natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede ver los conteos")
    
    count = db.query(PagoPrestamo).join(Prestamo).filter(
        Prestamo.natillera_id == natillera_id,
        PagoPrestamo.estado == EstadoPago.PENDIENTE
    ).count()
    return {"count": count}

@router.get("/pagos/my-pagos/aprobados/count", response_model=dict)
def get_pagos_aprobados_count(
    natillera_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cuenta los pagos aprobados del usuario actual"""
    from app.models import PagoPrestamo, EstadoPago, Prestamo
    query = db.query(PagoPrestamo).join(Prestamo).filter(
        Prestamo.referente_id == current_user.id,
        PagoPrestamo.estado == EstadoPago.APROBADO
    )
    if natillera_id:
        query = query.filter(Prestamo.natillera_id == natillera_id)
    count = query.count()
    return {"count": count}
