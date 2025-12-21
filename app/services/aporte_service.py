from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from app.models import Aporte, Natillera, User, AporteStatus, Transaccion, TipoTransaccion
from app.schemas import AporteCreate, AporteUpdate
from typing import List, Optional
from fastapi import HTTPException, status
from datetime import datetime
from app.services.natillera_service import NatilleraService

class AporteService:
    @staticmethod
    def create_aporte(db: Session, aporte: AporteCreate, user: User) -> Aporte:
        """Crea un nuevo aporte"""
        # Verificar que la natillera existe
        natillera = NatilleraService.get_natillera_by_id(db, aporte.natillera_id)
        if not natillera:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Natillera no encontrada")
        
        # Verificar que el usuario es miembro
        if not NatilleraService.is_member(natillera, user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No eres miembro de esta natillera")
        
        # Permitir múltiples aportes por mes - comentamos la validación
        # existing = db.query(Aporte).filter(
        #     and_(
        #         Aporte.user_id == user.id,
        #         Aporte.natillera_id == aporte.natillera_id,
        #         Aporte.month == aporte.month,
        #         Aporte.year == aporte.year
        #     )
        # ).first()
        # 
        # if existing:
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="Ya existe un aporte para este mes y año"
        #     )
        
        db_aporte = Aporte(
            user_id=user.id,
            natillera_id=aporte.natillera_id,
            amount=aporte.amount,
            month=aporte.month,
            year=aporte.year,
            status=AporteStatus.PENDIENTE
        )
        
        db.add(db_aporte)
        db.commit()
        db.refresh(db_aporte)
        return db_aporte
    
    @staticmethod
    def get_user_aportes(db: Session, user: User, natillera_id: Optional[int] = None) -> List[Aporte]:
        """Obtiene los aportes de un usuario"""
        query = db.query(Aporte).filter(Aporte.user_id == user.id)
        if natillera_id:
            query = query.filter(Aporte.natillera_id == natillera_id)
        
        # Debug: Mostrar la consulta SQL
        # print(f"DEBUG SQL: {query}")
        
        aportes = query.all()
        # print(f"DEBUG: Encontrados {len(aportes)} aportes para user_id={user.id}, natillera_id={natillera_id}")
        # for a in aportes:
        #     print(f"  - Aporte ID={a.id}, status={a.status.value}, month={a.month}/{a.year}, amount={a.amount}")
        
        return aportes
    
    @staticmethod
    def get_natillera_aportes(db: Session, natillera_id: int, current_user: User) -> List[Aporte]:
        """Obtiene todos los aportes de una natillera (solo creador)"""
        natillera = NatilleraService.get_natillera_by_id(db, natillera_id)
        if not natillera:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Natillera no encontrada")
        
        # Verificar que es el creador
        if not NatilleraService.is_creator(natillera, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el creador puede ver todos los aportes"
            )
        
        return db.query(Aporte).filter(Aporte.natillera_id == natillera_id).all()
    
    @staticmethod
    def update_aporte_status(
        db: Session,
        aporte_id: int,
        update: AporteUpdate,
        current_user: User
    ) -> Aporte:
        """Actualiza el estado de un aporte (solo creador)"""
        # Cargar aporte con la relación user para evitar lazy loading
        aporte = db.query(Aporte).options(joinedload(Aporte.user)).filter(Aporte.id == aporte_id).first()
        if not aporte:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aporte no encontrado")
        
        # Verificar que es el creador de la natillera
        natillera = NatilleraService.get_natillera_by_id(db, aporte.natillera_id)
        if not NatilleraService.is_creator(natillera, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el creador puede aprobar/rechazar aportes"
            )
        
        # Guardar estado anterior (comparar valores del enum correctamente)
        previous_status = aporte.status
        
        # Convertir el update.status a AporteStatus enum si es string
        new_status = AporteStatus(update.status) if isinstance(update.status, str) else update.status
        
        # Actualizar el estado del aporte primero
        aporte.status = new_status
        if new_status == AporteStatus.RECHAZADO:
            aporte.rejection_reason = update.rejection_reason
        
        # Si el aporte fue aprobado y no tenía ese estado antes, crear transacción de tipo efectivo
        if new_status == AporteStatus.APROBADO and previous_status != AporteStatus.APROBADO:
            # Verificar que no exista ya una transacción para este aporte
            existing_transaccion = db.query(Transaccion).filter(
                Transaccion.aporte_id == aporte.id
            ).first()
            
            if not existing_transaccion:
                transaccion = Transaccion(
                    natillera_id=aporte.natillera_id,
                    tipo=TipoTransaccion.EFECTIVO,
                    categoria=f"Aporte {aporte.user.full_name}",
                    monto=aporte.amount,
                    descripcion=f"Aporte del mes {aporte.month}/{aporte.year}",
                    fecha=datetime.utcnow(),
                    creado_por=current_user.id,
                    aporte_id=aporte.id
                )
                db.add(transaccion)
        
        try:
            db.commit()
            db.refresh(aporte)
        except IntegrityError as e:
            # Si hay error de duplicado en transacción, hacer rollback y solo actualizar el aporte
            db.rollback()
            # La transacción ya existe, solo actualizamos el estado del aporte
            aporte.status = new_status
            if new_status == AporteStatus.RECHAZADO:
                aporte.rejection_reason = update.rejection_reason
            db.commit()
            db.refresh(aporte)
        
        return aporte
    
    @staticmethod
    def get_aporte_by_id(db: Session, aporte_id: int) -> Optional[Aporte]:
        """Obtiene un aporte por ID"""
        return db.query(Aporte).filter(Aporte.id == aporte_id).first()
