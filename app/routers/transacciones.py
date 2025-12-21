from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from app.database import get_db
from app.models import Transaccion, Natillera, User, TipoTransaccion, Prestamo, Aporte
from app.schemas import TransaccionCreate, TransaccionResponse, TransaccionUpdate, BalanceResponse, TipoTransaccionEnum
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/transacciones", tags=["transacciones"])


@router.get("/natilleras/{natillera_id}/balance", response_model=BalanceResponse)
def get_balance(
    natillera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener balance financiero de una natillera"""
    # Verificar que la natillera existe
    natillera = db.query(Natillera).filter(Natillera.id == natillera_id).first()
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    
    # Verificar que el usuario es miembro o creador
    is_member = current_user in natillera.members
    is_creator = natillera.creator_id == current_user.id
    if not (is_member or is_creator):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta natillera")
    
    # Calcular totales por tipo
    efectivo = db.query(func.sum(Transaccion.monto)).filter(
        and_(Transaccion.natillera_id == natillera_id, Transaccion.tipo == TipoTransaccion.EFECTIVO)
    ).scalar() or Decimal(0)
    
    prestamos = db.query(func.sum(Transaccion.monto)).filter(
        and_(Transaccion.natillera_id == natillera_id, Transaccion.tipo == TipoTransaccion.PRESTAMO)
    ).scalar() or Decimal(0)
    
    ingresos = db.query(func.sum(Transaccion.monto)).filter(
        and_(Transaccion.natillera_id == natillera_id, Transaccion.tipo == TipoTransaccion.INGRESO)
    ).scalar() or Decimal(0)
    
    gastos = db.query(func.sum(Transaccion.monto)).filter(
        and_(Transaccion.natillera_id == natillera_id, Transaccion.tipo == TipoTransaccion.GASTO)
    ).scalar() or Decimal(0)
    
    # Capital disponible = Efectivo - Préstamos + Ingresos - Gastos
    capital_disponible = efectivo - prestamos + ingresos - gastos
    
    return BalanceResponse(
        efectivo=efectivo,
        prestamos=prestamos,
        ingresos=ingresos,
        gastos=gastos,
        capital_disponible=capital_disponible
    )


@router.get("/natilleras/{natillera_id}/transacciones", response_model=List[TransaccionResponse])
def get_transacciones(
    natillera_id: int,
    tipo: Optional[str] = Query(None),
    mes: Optional[int] = Query(None, ge=1, le=12),
    anio: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener transacciones de una natillera con filtros opcionales"""
    # Verificar que la natillera existe
    natillera = db.query(Natillera).filter(Natillera.id == natillera_id).first()
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    
    # Verificar que el usuario es miembro o creador
    is_member = current_user in natillera.members
    is_creator = natillera.creator_id == current_user.id
    if not (is_member or is_creator):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta natillera")
    
    # Query base con joins para cargar relaciones
    query = db.query(Transaccion).options(
        joinedload(Transaccion.creador),
        joinedload(Transaccion.aporte).joinedload(Aporte.user),
        joinedload(Transaccion.prestamo).joinedload(Prestamo.referente)
    ).filter(Transaccion.natillera_id == natillera_id)
    
    # Aplicar filtros
    if tipo:
        query = query.filter(Transaccion.tipo == tipo)
    if mes:
        query = query.filter(func.extract('month', Transaccion.fecha) == mes)
    if anio:
        query = query.filter(func.extract('year', Transaccion.fecha) == anio)
    
    # Ordenar por fecha descendente
    transacciones = query.order_by(Transaccion.fecha.desc()).all()
    
    # Asignar miembro a cada transacción
    for transaccion in transacciones:
        if transaccion.aporte:
            transaccion.miembro = transaccion.aporte.user
        elif transaccion.prestamo:
            transaccion.miembro = transaccion.prestamo.referente
    
    return transacciones


@router.post("/", response_model=TransaccionResponse, status_code=status.HTTP_201_CREATED)
def create_transaccion(
    transaccion: TransaccionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear una nueva transacción (manual, no efectivo)"""
    # Verificar que la natillera existe
    natillera = db.query(Natillera).filter(Natillera.id == transaccion.natillera_id).first()
    if not natillera:
        raise HTTPException(status_code=404, detail="Natillera no encontrada")
    
    # Solo el creador puede crear transacciones
    if natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede registrar transacciones")
    
    # No permitir crear transacciones de tipo efectivo (esas son automáticas)
    if transaccion.tipo == TipoTransaccionEnum.EFECTIVO:
        raise HTTPException(
            status_code=400, 
            detail="Las transacciones de tipo 'efectivo' se crean automáticamente al aprobar aportes"
        )
    
    # Validar que el monto es positivo
    if transaccion.monto <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser positivo")
    
    # Crear transacción
    nueva_transaccion = Transaccion(
        natillera_id=transaccion.natillera_id,
        tipo=transaccion.tipo,
        categoria=transaccion.categoria,
        monto=transaccion.monto,
        descripcion=transaccion.descripcion,
        fecha=transaccion.fecha or datetime.utcnow(),
        creado_por=current_user.id
    )
    
    db.add(nueva_transaccion)
    db.commit()
    db.refresh(nueva_transaccion)
    
    return nueva_transaccion


@router.patch("/{transaccion_id}", response_model=TransaccionResponse)
def update_transaccion(
    transaccion_id: int,
    transaccion_update: TransaccionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualizar una transacción (solo las manuales)"""
    # Buscar transacción
    transaccion = db.query(Transaccion).filter(Transaccion.id == transaccion_id).first()
    if not transaccion:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    
    # Verificar que el usuario es el creador de la natillera
    natillera = db.query(Natillera).filter(Natillera.id == transaccion.natillera_id).first()
    if natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede editar transacciones")
    
    # No permitir editar transacciones de tipo efectivo
    if transaccion.tipo == TipoTransaccion.EFECTIVO:
        raise HTTPException(
            status_code=400,
            detail="Las transacciones de tipo 'efectivo' no se pueden editar (vienen de aportes)"
        )
    
    # Actualizar campos
    if transaccion_update.categoria is not None:
        transaccion.categoria = transaccion_update.categoria
    if transaccion_update.monto is not None:
        if transaccion_update.monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser positivo")
        transaccion.monto = transaccion_update.monto
    if transaccion_update.descripcion is not None:
        transaccion.descripcion = transaccion_update.descripcion
    if transaccion_update.fecha is not None:
        transaccion.fecha = transaccion_update.fecha
    
    db.commit()
    db.refresh(transaccion)
    
    return transaccion


@router.delete("/{transaccion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaccion(
    transaccion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Eliminar una transacción (solo las manuales)"""
    # Buscar transacción
    transaccion = db.query(Transaccion).filter(Transaccion.id == transaccion_id).first()
    if not transaccion:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    
    # Verificar que el usuario es el creador de la natillera
    natillera = db.query(Natillera).filter(Natillera.id == transaccion.natillera_id).first()
    if natillera.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede eliminar transacciones")
    
    # No permitir eliminar transacciones de tipo efectivo
    if transaccion.tipo == TipoTransaccion.EFECTIVO:
        raise HTTPException(
            status_code=400,
            detail="Las transacciones de tipo 'efectivo' no se pueden eliminar (vienen de aportes)"
        )
    
    db.delete(transaccion)
    db.commit()
    
    return None
