from sqlalchemy.orm import Session, joinedload
from app.models import Sorteo, User, Natillera, EstadoSorteo, TipoSorteo, BilleteLoteria, EstadoBillete
from app.schemas import SorteoCreate
from typing import List, Optional
from fastapi import HTTPException, status
from datetime import datetime

class SorteoService:
    @staticmethod
    def create_sorteo(db: Session, sorteo: SorteoCreate, creator: User) -> Sorteo:
        """Crea un nuevo sorteo"""
        # Verificar que el usuario sea creador de la natillera
        natillera = db.query(Natillera).filter(Natillera.id == sorteo.natillera_id).first()
        if not natillera:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Natillera no encontrada")
        
        if natillera.creator_id != creator.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el creador puede crear sorteos")
        
        db_sorteo = Sorteo(
            natillera_id=sorteo.natillera_id,
            tipo=sorteo.tipo,
            titulo=sorteo.titulo,
            descripcion=sorteo.descripcion,
            fecha_sorteo=sorteo.fecha_sorteo,
            estado=EstadoSorteo.ACTIVO,
            creador_id=creator.id
        )
        
        db.add(db_sorteo)
        db.flush()  # Para obtener el ID del sorteo
        
        # Si es una lotería, crear 101 billetes (000-100)
        if sorteo.tipo == TipoSorteo.LOTERIA:
            for numero in range(0, 101):  # 0-100
                billete = BilleteLoteria(
                    sorteo_id=db_sorteo.id,
                    numero=f"{numero:03d}",  # Formato con 3 dígitos: 000, 001, 002, ..., 100
                    estado=EstadoBillete.DISPONIBLE
                )
                db.add(billete)
        
        db.commit()
        db.refresh(db_sorteo)
        return db.query(Sorteo).filter(Sorteo.id == db_sorteo.id).first()
    
    @staticmethod
    def get_sorteo_by_id(db: Session, sorteo_id: int) -> Optional[Sorteo]:
        """Obtiene un sorteo por ID"""
        return db.query(Sorteo).filter(Sorteo.id == sorteo_id).first()
    
    @staticmethod
    def get_active_sorteos_for_user(db: Session, user: User) -> List[Sorteo]:
        """Obtiene todos los sorteos activos de las natilleras del usuario"""
        natillera_ids = [n.id for n in user.natilleras]
        print(f"Buscando sorteos para natilleras: {natillera_ids}")
        sorteos = db.query(Sorteo).filter(
            Sorteo.natillera_id.in_(natillera_ids),
            Sorteo.estado == EstadoSorteo.ACTIVO
        ).all()
        return sorteos
    
    @staticmethod
    def get_billetes_loteria(db: Session, sorteo_id: int) -> List[BilleteLoteria]:
        """Obtiene todos los billetes de una lotería"""
        return db.query(BilleteLoteria).filter(BilleteLoteria.sorteo_id == sorteo_id).order_by(BilleteLoteria.numero).all()
    
    @staticmethod
    def tomar_billete_loteria(db: Session, sorteo_id: int, numero: str, user: User) -> BilleteLoteria:
        """Permite a un usuario tomar un billete disponible"""
        print(f"Intentando tomar billete: sorteo_id={sorteo_id}, numero={numero}, user_id={user.id}")
        
        # Formatear el número con ceros a la izquierda
        numero_formateado = f"{int(numero):03d}"
        
        # Verificar que el usuario pertenece a la natillera del sorteo
        sorteo = db.query(Sorteo).filter(Sorteo.id == sorteo_id).first()
        if not sorteo:
            print(f"Sorteo no encontrado: {sorteo_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sorteo no encontrado")
        
        print(f"Sorteo encontrado: {sorteo.id}, natillera: {sorteo.natillera_id}")
        print(f"Natilleras del usuario: {[n.id for n in user.natilleras]}")
        
        if sorteo.natillera_id not in [n.id for n in user.natilleras]:
            print(f"Usuario no tiene acceso al sorteo")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a este sorteo")
        
        # Buscar el billete
        billete = db.query(BilleteLoteria).filter(
            BilleteLoteria.sorteo_id == sorteo_id,
            BilleteLoteria.numero == numero_formateado
        ).first()
        
        if not billete:
            print(f"Billete no encontrado: sorteo_id={sorteo_id}, numero={numero_formateado}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billete no encontrado")
        
        print(f"Billete encontrado: id={billete.id}, estado={billete.estado}")
        
        if billete.estado != EstadoBillete.DISPONIBLE:
            print(f"Billete no disponible: estado={billete.estado}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Billete no disponible")
        
        # Tomar el billete
        print("Tomando billete...")
        billete.estado = EstadoBillete.TOMADO
        billete.tomado_por = user.id
        billete.fecha_tomado = datetime.now()
        
        try:
            db.commit()
            print("Commit exitoso")
            # En lugar de refresh, hacer una nueva query para evitar problemas de relaciones
            billete_actualizado = db.query(BilleteLoteria).filter(BilleteLoteria.id == billete.id).first()
            print("Query exitosa")
            return billete_actualizado
        except Exception as e:
            print(f"Error en commit/refresh: {e}")
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al tomar billete: {str(e)}")
    
    @staticmethod
    def finalizar_sorteo(db: Session, sorteo_id: int, user: User, numero_ganador: Optional[str] = None) -> Sorteo:
        """Finaliza un sorteo seleccionando un número ganador (aleatoriamente o especificado)"""
        sorteo = db.query(Sorteo).filter(Sorteo.id == sorteo_id).first()
        if not sorteo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sorteo no encontrado")
        
        # Verificar que el usuario sea el creador
        if sorteo.creador_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el creador puede finalizar el sorteo")
        
        if sorteo.estado != EstadoSorteo.ACTIVO:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El sorteo ya está finalizado")
        
        # Obtener todos los billetes tomados
        billetes_tomados = db.query(BilleteLoteria).filter(
            BilleteLoteria.sorteo_id == sorteo_id,
            BilleteLoteria.estado == EstadoBillete.TOMADO
        ).all()
        
        if not billetes_tomados:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay billetes tomados para sortear")
        
        if numero_ganador is not None:
            # Formatear el número con ceros a la izquierda si es necesario
            numero_formateado = f"{int(numero_ganador):03d}"
            
            # Buscar el billete con ese número (puede estar tomado o no)
            billete_ganador = db.query(BilleteLoteria).filter(
                BilleteLoteria.sorteo_id == sorteo_id,
                BilleteLoteria.numero == numero_formateado
            ).first()
            
            if not billete_ganador:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                  detail=f"El número {numero_formateado} no existe")
            
            # Si el billete no está tomado, no hay ganador
            if billete_ganador.estado != EstadoBillete.TOMADO:
                # Actualizar el sorteo indicando que no hay ganador
                sorteo.estado = EstadoSorteo.FINALIZADO
                sorteo.numero_ganador = numero_formateado  # Ya está formateado
                sorteo.fecha_sorteo = datetime.now()
                db.commit()
                db.refresh(sorteo)
                return sorteo
            
            ganador = billete_ganador
        else:
            # Seleccionar un ganador aleatoriamente
            import random
            ganador = random.choice(billetes_tomados)
        
        # Actualizar el sorteo
        sorteo.estado = EstadoSorteo.FINALIZADO
        sorteo.numero_ganador = ganador.numero.zfill(3)  # Asegurar formato con 3 dígitos
        sorteo.fecha_sorteo = datetime.now()
        
        db.commit()
        db.refresh(sorteo)
        return sorteo
    
    @staticmethod
    def marcar_billete_pagado(db: Session, sorteo_id: int, numero: str, user: User) -> BilleteLoteria:
        """Marca un billete como pagado (solo para el creador del sorteo)"""
        sorteo = db.query(Sorteo).filter(Sorteo.id == sorteo_id).first()
        if not sorteo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sorteo no encontrado")
        
        # Verificar que el usuario sea el creador
        if sorteo.creador_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el creador puede marcar pagos")
        
        # Formatear el número con ceros a la izquierda
        numero_formateado = f"{int(numero):03d}"
        
        billete = db.query(BilleteLoteria).filter(
            BilleteLoteria.sorteo_id == sorteo_id,
            BilleteLoteria.numero == numero_formateado
        ).first()
        
        if not billete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billete no encontrado")
        
        if billete.estado != EstadoBillete.TOMADO:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se pueden marcar como pagados los billetes tomados")
        
        billete.pagado = True
        db.commit()
        db.refresh(billete)
        return billete
    
    @staticmethod
    def get_billetes_admin(db: Session, sorteo_id: int, user: User) -> List[BilleteLoteria]:
        """Obtiene todos los billetes con información completa para el admin/creador"""
        print(f"Obteniendo billetes admin para sorteo {sorteo_id}, usuario {user.id}")
        
        sorteo = db.query(Sorteo).filter(Sorteo.id == sorteo_id).first()
        if not sorteo:
            print(f"Sorteo {sorteo_id} no encontrado")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sorteo no encontrado")
        
        # Verificar que el usuario sea el creador
        if sorteo.creador_id != user.id:
            print(f"Usuario {user.id} no es creador del sorteo {sorteo_id} (creador: {sorteo.creador_id})")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a esta información")
        
        print("Usuario autorizado, obteniendo billetes...")
        # Obtener billetes sin joinedload por ahora para evitar problemas de serialización
        try:
            billetes = db.query(BilleteLoteria).filter(BilleteLoteria.sorteo_id == sorteo_id).order_by(BilleteLoteria.numero).all()
            print(f"Se encontraron {len(billetes)} billetes")
            return billetes
        except Exception as e:
            print(f"Error obteniendo billetes: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error obteniendo billetes: {str(e)}")
    
    @staticmethod
    def get_finalized_sorteos_for_user(db: Session, user: User) -> List[dict]:
        """Obtiene todos los sorteos finalizados de las natilleras del usuario con información del ganador"""
        # Obtener IDs de natilleras del usuario
        natillera_ids = [n.id for n in user.natilleras]
        
        # Obtener sorteos finalizados con relaciones
        sorteos = db.query(Sorteo).options(
            joinedload(Sorteo.creador),
            joinedload(Sorteo.natillera),
            joinedload(Sorteo.billetes)
        ).filter(
            Sorteo.natillera_id.in_(natillera_ids),
            Sorteo.estado == EstadoSorteo.FINALIZADO
        ).order_by(Sorteo.fecha_sorteo.desc()).all()
        
        # Convertir a formato de respuesta que coincida con SorteoFinalizadoResponse
        result = []
        for sorteo in sorteos:
            # Buscar el billete ganador
            ganador_data = None
            if sorteo.numero_ganador:
                # Hacer una consulta explícita para obtener el billete con el usuario
                billete_ganador = db.query(BilleteLoteria).options(
                    joinedload(BilleteLoteria.usuario)
                ).filter(
                    BilleteLoteria.sorteo_id == sorteo.id,
                    BilleteLoteria.numero == sorteo.numero_ganador,
                    BilleteLoteria.estado == EstadoBillete.TOMADO
                ).first()
                
                if billete_ganador and billete_ganador.usuario:
                    ganador_data = {
                        'id': billete_ganador.usuario.id,
                        'email': billete_ganador.usuario.email or '',
                        'username': billete_ganador.usuario.username or '',
                        'full_name': billete_ganador.usuario.full_name or '',
                        'created_at': billete_ganador.usuario.created_at.isoformat() if billete_ganador.usuario.created_at else None
                    }
                    print(f"  ¡Ganador encontrado! {ganador_data['full_name']}")
                else:
                    print(f"  Billete encontrado: {billete_ganador}, Usuario: {billete_ganador.usuario if billete_ganador else None}")
            
            sorteo_dict = {
                'id': sorteo.id,
                'natillera_id': sorteo.natillera_id,
                'tipo': sorteo.tipo.value if hasattr(sorteo.tipo, 'value') else str(sorteo.tipo),
                'titulo': sorteo.titulo or '',
                'descripcion': sorteo.descripcion or '',
                'fecha_creacion': sorteo.fecha_creacion.isoformat() if sorteo.fecha_creacion else None,
                'fecha_sorteo': sorteo.fecha_sorteo.isoformat() if sorteo.fecha_sorteo else None,
                'estado': sorteo.estado.value if hasattr(sorteo.estado, 'value') else str(sorteo.estado),
                'creador_id': sorteo.creador_id,
                'numero_ganador': sorteo.numero_ganador,
                'creador': {
                    'id': sorteo.creador.id,
                    'email': sorteo.creador.email or '',
                    'username': sorteo.creador.username or '',
                    'full_name': sorteo.creador.full_name or '',
                    'created_at': sorteo.creador.created_at.isoformat() if sorteo.creador.created_at else None
                },
                'natillera': {
                    'id': sorteo.natillera.id,
                    'name': sorteo.natillera.name or '',
                    'monthly_amount': float(sorteo.natillera.monthly_amount or 0),
                    'creator_id': sorteo.natillera.creator_id,
                    'created_at': sorteo.natillera.created_at.isoformat() if sorteo.natillera.created_at else None,
                    'estado': sorteo.natillera.estado.value if hasattr(sorteo.natillera.estado, 'value') else str(sorteo.natillera.estado)
                },
                'ganador': ganador_data
            }
            result.append(sorteo_dict)
        
        print(f"Se encontraron {len(result)} sorteos finalizados para el usuario {user.id}")
        print(f"Se encontraron {len(result)} sorteos finalizados para el usuario {user.id}")
        return result
    
    @staticmethod
    def update_sorteo_estado(db: Session, sorteo_id: int, estado: EstadoSorteo, current_user: User) -> Sorteo:
        """Actualiza el estado de un sorteo"""
        sorteo = SorteoService.get_sorteo_by_id(db, sorteo_id)
        if not sorteo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sorteo no encontrado")
        
        if sorteo.creador_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el creador puede modificar el sorteo")
        
        sorteo.estado = estado
        db.commit()
        db.refresh(sorteo)
        return sorteo