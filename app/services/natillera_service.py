from sqlalchemy.orm import Session
from app.models import Natillera, User, NatilleraEstado, Invitacion, InvitacionEstado
from app.schemas import NatilleraCreate, NatilleraUpdate
from typing import List, Optional
from fastapi import HTTPException, status

class NatilleraService:
    @staticmethod
    def create_natillera(db: Session, natillera: NatilleraCreate, creator: User) -> Natillera:
        """Crea una nueva natillera"""
        db_natillera = Natillera(
            name=natillera.name,
            monthly_amount=natillera.monthly_amount,
            creator_id=creator.id,
            estado=NatilleraEstado.ACTIVO
        )
        # Agregar al creador como miembro
        db_natillera.members.append(creator)
        
        db.add(db_natillera)
        db.commit()
        db.refresh(db_natillera)
        return db_natillera
    
    @staticmethod
    def get_natillera_by_id(db: Session, natillera_id: int) -> Optional[Natillera]:
        """Obtiene una natillera por ID"""
        return db.query(Natillera).filter(Natillera.id == natillera_id).first()
    
    @staticmethod
    def get_user_natilleras(db: Session, user: User) -> List[Natillera]:
        """Obtiene todas las natilleras de un usuario"""
        return user.natilleras
    
    @staticmethod
    def get_user_active_natilleras(db: Session, user: User) -> List[Natillera]:
        """Obtiene solo las natilleras activas de un usuario"""
        return [n for n in user.natilleras if n.estado == NatilleraEstado.ACTIVO]
    
    @staticmethod
    def get_created_natilleras(db: Session, user: User) -> List[Natillera]:
        """Obtiene las natilleras creadas por un usuario"""
        return db.query(Natillera).filter(Natillera.creator_id == user.id).all()
    
    @staticmethod
    def update_natillera_estado(db: Session, natillera_id: int, estado: NatilleraEstado, current_user: User) -> Natillera:
        """Actualiza el estado de una natillera"""
        natillera = NatilleraService.get_natillera_by_id(db, natillera_id)
        if not natillera:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Natillera no encontrada")
        
        # Solo el creador puede cambiar el estado
        if natillera.creator_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el creador puede cambiar el estado")
        
        natillera.estado = estado
        db.commit()
        db.refresh(natillera)
        return natillera
    
    @staticmethod
    def add_member_to_natillera(db: Session, natillera_id: int, user_id: int, current_user: User) -> dict:
        """Envía una invitación para unirse a una natillera"""
        natillera = NatilleraService.get_natillera_by_id(db, natillera_id)
        if not natillera:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Natillera no encontrada")
        
        # Solo el creador puede invitar miembros
        if natillera.creator_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el creador puede invitar miembros")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        
        # Verificar si ya es miembro
        if user in natillera.members:
            return {"message": "El usuario ya es miembro de la natillera"}
        
        # Verificar si ya existe una invitación pendiente
        existing_invitation = db.query(Invitacion).filter(
            Invitacion.natillera_id == natillera_id,
            Invitacion.invited_user_id == user_id,
            Invitacion.estado == InvitacionEstado.PENDIENTE
        ).first()
        
        if existing_invitation:
            return {"message": "Ya existe una invitación pendiente para este usuario"}
        
        # Crear nueva invitación
        invitacion = Invitacion(
            natillera_id=natillera_id,
            invited_user_id=user_id,
            inviter_user_id=current_user.id,
            estado=InvitacionEstado.PENDIENTE
        )
        
        db.add(invitacion)
        db.commit()
        db.refresh(invitacion)
        
        return {"message": f"Invitación enviada a {user.full_name}", "invitacion_id": invitacion.id}
        db.commit()
        db.refresh(natillera)
        return natillera
    
    @staticmethod
    def is_creator(natillera: Natillera, user: User) -> bool:
        """Verifica si el usuario es el creador de la natillera"""
        return natillera.creator_id == user.id
    
    @staticmethod
    def is_member(natillera: Natillera, user: User) -> bool:
        """Verifica si el usuario es miembro o creador de la natillera"""
        return user.id == natillera.creator_id or any(m.id == user.id for m in natillera.members)
