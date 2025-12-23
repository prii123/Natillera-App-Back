from sqlalchemy.orm import Session
from app.models import Politica
from app.schemas import PoliticaCreate, PoliticaUpdate
from typing import List, Optional


class PoliticaService:
    @staticmethod
    def get_politicas_by_natillera(db: Session, natillera_id: int) -> List[Politica]:
        """Obtiene todas las políticas de una natillera ordenadas por orden"""
        return db.query(Politica).filter(Politica.natillera_id == natillera_id).order_by(Politica.orden).all()

    @staticmethod
    def get_politica_by_id(db: Session, politica_id: int) -> Optional[Politica]:
        """Obtiene una política por su ID"""
        return db.query(Politica).filter(Politica.id == politica_id).first()

    @staticmethod
    def create_politica(db: Session, politica: PoliticaCreate) -> Politica:
        """Crea una nueva política"""
        db_politica = Politica(
            natillera_id=politica.natillera_id,
            titulo=politica.titulo,
            descripcion=politica.descripcion,
            orden=politica.orden
        )
        db.add(db_politica)
        db.commit()
        db.refresh(db_politica)
        return db_politica

    @staticmethod
    def update_politica(db: Session, politica_id: int, politica_update: PoliticaUpdate) -> Optional[Politica]:
        """Actualiza una política existente"""
        db_politica = db.query(Politica).filter(Politica.id == politica_id).first()
        if db_politica:
            for field, value in politica_update.dict(exclude_unset=True).items():
                setattr(db_politica, field, value)
            db.commit()
            db.refresh(db_politica)
        return db_politica

    @staticmethod
    def delete_politica(db: Session, politica_id: int) -> bool:
        """Elimina una política"""
        db_politica = db.query(Politica).filter(Politica.id == politica_id).first()
        if db_politica:
            db.delete(db_politica)
            db.commit()
            return True
        return False

    @staticmethod
    def reorder_politicas(db: Session, natillera_id: int, politica_orders: List[dict]) -> bool:
        """Reordena las políticas de una natillera"""
        try:
            for order_data in politica_orders:
                db.query(Politica).filter(Politica.id == order_data['id']).update({
                    'orden': order_data['orden']
                })
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            return False