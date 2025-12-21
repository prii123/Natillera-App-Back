from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from app.models import Prestamo, Transaccion, Natillera, User, EstadoPrestamo, TipoTransaccion, PagoPrestamo, EstadoPago
from app.schemas import PrestamoCreate, PrestamoUpdate, PrestamoDetalle
from app.services.user_service import UserService


class PrestamoService:

    @staticmethod
    def get_pagos_prestamo_autorizado(db: Session, prestamo_id: int, user: 'User') -> dict:
        """
        Devuelve los pagos de un préstamo solo si el usuario es el creador de la natillera o el referente del préstamo.
        Retorna datos del préstamo y los pagos ordenados por fecha ascendente.
        """
        prestamo = db.query(Prestamo).options(
            joinedload(Prestamo.referente),
            joinedload(Prestamo.creador),
            joinedload(Prestamo.natillera)
        ).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")
        natillera = PrestamoService.get_natillera_by_id(db, prestamo.natillera_id)
        if not natillera:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Natillera no encontrada")
        is_creator = PrestamoService.user_is_natillera_creator(natillera, user)
        is_referente = PrestamoService.user_is_prestamo_referente(prestamo, user)
        if not (is_creator or is_referente):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="No tienes permiso para ver los pagos de este préstamo")
        # Obtener pagos ordenados por fecha ascendente desde la nueva tabla PagoPrestamo
        pagos = db.query(PagoPrestamo).options(
            joinedload(PagoPrestamo.registrador),
            joinedload(PagoPrestamo.aprobador)
        ).filter(
            PagoPrestamo.prestamo_id == prestamo_id
        ).order_by(PagoPrestamo.fecha_pago.asc()).all()
        return {
            "prestamo": prestamo,
            "pagos": pagos
        }

    @staticmethod
    def get_natillera_by_id(db: Session, natillera_id: int) -> Optional[Natillera]:
        """Obtiene una natillera por su ID"""
        return db.query(Natillera).filter(Natillera.id == natillera_id).first()

    @staticmethod
    def get_prestamo_by_id_simple(db: Session, prestamo_id: int) -> Optional[Prestamo]:
        """Obtiene un préstamo por su ID (objeto ORM simple)"""
        return db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()

    @staticmethod
    def user_is_natillera_creator(natillera: Natillera, user: User) -> bool:
        return natillera.creator_id == user.id

    @staticmethod
    def user_is_natillera_member(natillera: Natillera, user: User) -> bool:
        return user.id == natillera.creator_id or any(m.id == user.id for m in natillera.members)

    @staticmethod
    def user_is_prestamo_referente(prestamo: Prestamo, user: User) -> bool:
        return prestamo.referente_id == user.id

    @staticmethod
    def get_pagos_prestamo(db: Session, prestamo_id: int) -> list:
        """Devuelve el historial de pagos (transacciones de tipo ingreso asociadas a este préstamo)"""
        from app.models import Transaccion, TipoTransaccion
        pagos = db.query(Transaccion).filter(
            Transaccion.prestamo_id == prestamo_id,
            Transaccion.tipo.in_([TipoTransaccion.INGRESO, TipoTransaccion.PRESTAMO, TipoTransaccion.PAGO_PRESTAMOS, TipoTransaccion.PAGO_PRESTAMO_PENDIENTE])
        ).order_by(Transaccion.fecha.asc()).all()
        return [
            {
                "id": pago.id,
                "prestamo_id": pago.prestamo_id,
                "monto": float(pago.monto),
                "fecha_pago": pago.fecha.isoformat() if pago.fecha else None
            }
            for pago in pagos
        ]
    
    @staticmethod
    def calcular_monto_total(monto: Decimal, tasa_interes: Decimal, plazo_meses: int) -> dict:
        """Calcula el interés total y el monto total a pagar"""
        # Convertir todo a Decimal para evitar errores de tipo
        interes_total = (monto * tasa_interes / Decimal(100)) * (Decimal(plazo_meses) / Decimal(12))
        monto_total = monto + interes_total
        return {
            "interes_total": interes_total,
            "monto_total": monto_total
        }
    
    @staticmethod
    def create_prestamo(db: Session, prestamo_data: PrestamoCreate, user_id: int) -> Prestamo:
        """Crea un préstamo y genera una transacción de tipo PRESTAMO"""
        # Verificar que el referente exista y pertenezca a la natillera
        referente = db.query(User).filter(User.id == prestamo_data.referente_id).first()
        if not referente:
            raise ValueError("El referente no existe")
        # Verificar que la natillera existe
        natillera = db.query(Natillera).filter(Natillera.id == prestamo_data.natillera_id).first()
        if not natillera:
            raise ValueError("La natillera no existe")
        # Calcular fecha de vencimiento si no se proporciona fecha_inicio
        fecha_inicio = prestamo_data.fecha_inicio or datetime.now()
        fecha_vencimiento = fecha_inicio + timedelta(days=30 * prestamo_data.plazo_meses)
        # Calcular el monto total con intereses
        calculos = PrestamoService.calcular_monto_total(
            prestamo_data.monto,
            prestamo_data.tasa_interes,
            prestamo_data.plazo_meses
        )
        # Determinar si el usuario es creador o miembro
        aprobado = None  # None = pendiente, True = aprobado, False = rechazado
        if user_id == natillera.creator_id:
            aprobado = True
        # Si no es el creador, queda como None (pendiente)
        # Crear el préstamo
        prestamo = Prestamo(
            natillera_id=prestamo_data.natillera_id,
            monto=prestamo_data.monto,
            tasa_interes=prestamo_data.tasa_interes,
            plazo_meses=prestamo_data.plazo_meses,
            fecha_inicio=fecha_inicio,
            fecha_vencimiento=fecha_vencimiento,
            nombre_prestatario=prestamo_data.nombre_prestatario,
            telefono_prestatario=prestamo_data.telefono_prestatario,
            email_prestatario=prestamo_data.email_prestatario,
            direccion_prestatario=prestamo_data.direccion_prestatario,
            referente_id=prestamo_data.referente_id,
            creado_por=user_id,
            notas=prestamo_data.notas,
            estado=EstadoPrestamo.ACTIVO,
            monto_pagado=Decimal('0.00'),
            aprobado=aprobado
        )
        db.add(prestamo)
        db.flush()  # Para obtener el ID del préstamo
        # Crear transacción de egreso (préstamo del monto total)
        transaccion_egreso = Transaccion(
            natillera_id=prestamo_data.natillera_id,
            tipo=TipoTransaccion.PRESTAMO,
            categoria="Préstamo",
            monto=calculos["monto_total"],  # Registrar monto total con intereses
            descripcion=f"Préstamo a {prestamo_data.nombre_prestatario} (Ref: {referente.full_name}) - Monto: ${prestamo_data.monto}, Interés: ${calculos['interes_total']}, Total: ${calculos['monto_total']}",
            creado_por=user_id,
            prestamo_id=prestamo.id
        )
        db.add(transaccion_egreso)
        
        # Si el préstamo se aprueba automáticamente (creador), crear transacción de ingreso por intereses
        if aprobado is True:
            transaccion_ingreso = Transaccion(
                natillera_id=prestamo_data.natillera_id,
                tipo=TipoTransaccion.INGRESO,
                categoria="Intereses por Préstamo",
                monto=calculos["interes_total"],
                descripcion=f"Intereses por préstamo a {prestamo_data.nombre_prestatario} - {prestamo_data.tasa_interes}% anual por {prestamo_data.plazo_meses} meses",
                creado_por=user_id,
                prestamo_id=prestamo.id
            )
            db.add(transaccion_ingreso)
        
        db.commit()
        db.refresh(prestamo)
        return prestamo
    
    @staticmethod
    def get_prestamos_by_natillera(
        db: Session,
        natillera_id: int,
        estado: Optional[str] = None,
        referente_id: Optional[int] = None
    ) -> List[Prestamo]:
        """Obtiene todos los préstamos de una natillera con filtros opcionales"""
        
        query = db.query(Prestamo).options(
            joinedload(Prestamo.referente),
            joinedload(Prestamo.creador)
        ).filter(Prestamo.natillera_id == natillera_id)
        
        if estado:
            try:
                estado_enum = EstadoPrestamo(estado)
                query = query.filter(Prestamo.estado == estado_enum)
            except ValueError:
                pass  # Si el estado no es válido, ignorar el filtro
        
        if referente_id:
            query = query.filter(Prestamo.referente_id == referente_id)
        
        return query.order_by(Prestamo.created_at.desc()).all()
    
    @staticmethod
    def get_resumen_prestamos(db: Session, natillera_id: int) -> dict:
        """Obtiene resumen agregado de préstamos para mejor rendimiento"""
        from sqlalchemy import func
        
        # Obtener todos los préstamos de la natillera
        prestamos = db.query(Prestamo).filter(
            Prestamo.natillera_id == natillera_id
        ).all()
        
        # Calcular estadísticas
        activos = [p for p in prestamos if p.estado == EstadoPrestamo.ACTIVO]
        total_activos = len(activos)
        
        monto_prestado = sum(p.monto for p in prestamos)
        monto_recuperado = sum(p.monto_pagado for p in prestamos)
        
        # Calcular monto por recuperar (solo de préstamos activos)
        monto_por_recuperar = Decimal('0.00')
        for prestamo in activos:
            calculos = PrestamoService.calcular_monto_total(
                prestamo.monto,
                prestamo.tasa_interes,
                prestamo.plazo_meses
            )
            monto_pendiente = calculos["monto_total"] - prestamo.monto_pagado
            monto_por_recuperar += monto_pendiente
        
        return {
            "total_activos": total_activos,
            "monto_prestado": monto_prestado,
            "monto_por_recuperar": monto_por_recuperar,
            "monto_recuperado": monto_recuperado
        }
    
    @staticmethod
    def get_prestamo_by_id(db: Session, prestamo_id: int) -> Optional[PrestamoDetalle]:
        """Obtiene un préstamo por su ID con detalles calculados"""
        
        prestamo = db.query(Prestamo).options(
            joinedload(Prestamo.referente),
            joinedload(Prestamo.creador)
        ).filter(Prestamo.id == prestamo_id).first()
        
        if not prestamo:
            return None
        
        # Calcular detalles
        calculos = PrestamoService.calcular_monto_total(
            prestamo.monto,
            prestamo.tasa_interes,
            prestamo.plazo_meses
        )
        
        dias_restantes = (prestamo.fecha_vencimiento - datetime.now()).days
        monto_pendiente = calculos["monto_total"] - prestamo.monto_pagado
        
        # Crear objeto PrestamoDetalle
        prestamo_dict = {
            "id": prestamo.id,
            "natillera_id": prestamo.natillera_id,
            "monto": prestamo.monto,
            "tasa_interes": prestamo.tasa_interes,
            "plazo_meses": prestamo.plazo_meses,
            "nombre_prestatario": prestamo.nombre_prestatario,
            "telefono_prestatario": prestamo.telefono_prestatario,
            "email_prestatario": prestamo.email_prestatario,
            "direccion_prestatario": prestamo.direccion_prestatario,
            "referente_id": prestamo.referente_id,
            "notas": prestamo.notas,
            "fecha_inicio": prestamo.fecha_inicio,
            "fecha_vencimiento": prestamo.fecha_vencimiento,
            "estado": prestamo.estado.value,
            "monto_pagado": prestamo.monto_pagado,
            "creado_por": prestamo.creado_por,
            "created_at": prestamo.created_at,
            "updated_at": prestamo.updated_at,
            "referente": prestamo.referente,
            "creador": prestamo.creador,
            "monto_pendiente": monto_pendiente,
            "interes_total": calculos["interes_total"],
            "monto_total": calculos["monto_total"],
            "dias_restantes": max(0, dias_restantes)
        }
        
        return PrestamoDetalle(**prestamo_dict)
    
    @staticmethod
    def update_prestamo(
        db: Session,
        prestamo_id: int,
        prestamo_update: PrestamoUpdate,
        user_id: int
    ) -> Optional[Prestamo]:
        """Actualiza un préstamo (pagos, estado, notas)"""
        
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            return None
        
        # Actualizar campos si se proporcionan
        if prestamo_update.estado:
            prestamo.estado = EstadoPrestamo(prestamo_update.estado.value)
        
        if prestamo_update.monto_pagado is not None:
            # Validar que no supere el monto total
            calculos = PrestamoService.calcular_monto_total(
                prestamo.monto,
                prestamo.tasa_interes,
                prestamo.plazo_meses
            )
            
            if prestamo_update.monto_pagado > calculos["monto_total"]:
                raise ValueError("El monto pagado no puede superar el monto total del préstamo")
            
            prestamo.monto_pagado = prestamo_update.monto_pagado
            
            # Si el monto pagado es igual al total, marcar como PAGADO
            if prestamo.monto_pagado >= calculos["monto_total"]:
                prestamo.estado = EstadoPrestamo.PAGADO
        
        if prestamo_update.monto is not None:
            prestamo.monto = prestamo_update.monto
        
        if prestamo_update.tasa_interes is not None:
            prestamo.tasa_interes = prestamo_update.tasa_interes
        
        if prestamo_update.notas is not None:
            prestamo.notas = prestamo_update.notas
        
        # Actualizar timestamp
        prestamo.updated_at = datetime.now()
        
        db.commit()
        db.refresh(prestamo)
        
        return prestamo
    
    @staticmethod
    def aprobar_prestamo(db: Session, prestamo_id: int, user_id: int) -> Prestamo:
        """Aprueba un préstamo y crea la transacción de ingreso por intereses si no existe"""
        
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            raise ValueError("Préstamo no encontrado")
        
        if prestamo.aprobado is True:
            raise ValueError("El préstamo ya está aprobado")
        
        # Verificar que el usuario sea el creador de la natillera
        natillera = PrestamoService.get_natillera_by_id(db, prestamo.natillera_id)
        if not natillera or natillera.creator_id != user_id:
            raise ValueError("Solo el creador de la natillera puede aprobar préstamos")
        
        prestamo.aprobado = True
        prestamo.updated_at = datetime.now()
        
        # Verificar si ya existe una transacción de ingreso por intereses para este préstamo
        existing_ingreso = db.query(Transaccion).filter(
            Transaccion.prestamo_id == prestamo_id,
            Transaccion.tipo == TipoTransaccion.INGRESO,
            Transaccion.categoria == "Intereses por Préstamo"
        ).first()
        
        if not existing_ingreso:
            # Calcular intereses
            calculos = PrestamoService.calcular_monto_total(
                prestamo.monto,
                prestamo.tasa_interes,
                prestamo.plazo_meses
            )
            
            # Crear transacción de ingreso por intereses
            transaccion_ingreso = Transaccion(
                natillera_id=prestamo.natillera_id,
                tipo=TipoTransaccion.INGRESO,
                categoria="Intereses por Préstamo",
                monto=calculos["interes_total"],
                descripcion=f"Intereses por préstamo aprobado a {prestamo.nombre_prestatario} - {prestamo.tasa_interes}% anual por {prestamo.plazo_meses} meses",
                creado_por=user_id,
                prestamo_id=prestamo.id
            )
            db.add(transaccion_ingreso)
        
        db.commit()
        db.refresh(prestamo)
        return prestamo
    
    @staticmethod
    def rechazar_prestamo(db: Session, prestamo_id: int, user_id: int) -> Prestamo:
        """Rechaza un préstamo pendiente"""
        
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            raise ValueError("Préstamo no encontrado")
        
        if prestamo.aprobado is not None:
            raise ValueError("El préstamo ya ha sido aprobado o rechazado")
        
        # Verificar que el usuario sea el creador de la natillera
        natillera = PrestamoService.get_natillera_by_id(db, prestamo.natillera_id)
        if not natillera or natillera.creator_id != user_id:
            raise ValueError("Solo el creador de la natillera puede rechazar préstamos")
        
        prestamo.aprobado = False
        prestamo.updated_at = datetime.now()
        
        db.commit()
        db.refresh(prestamo)
        return prestamo
    
    @staticmethod
    def registrar_pago(
        db: Session,
        prestamo_id: int,
        monto_pago: Decimal,
        user_id: int
    ) -> Prestamo:
        """Registra un pago parcial o total de un préstamo"""
        
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            raise ValueError("Préstamo no encontrado")
        
        # Obtener el usuario
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        
        # Verificar si el usuario es el creador de la natillera
        natillera = PrestamoService.get_natillera_by_id(db, prestamo.natillera_id)
        is_creator = PrestamoService.user_is_natillera_creator(natillera, user)
        
        # Crear el pago
        pago = PagoPrestamo(
            prestamo_id=prestamo_id,
            monto=monto_pago,
            registrado_por=user_id,
            estado=EstadoPago.APROBADO if is_creator else EstadoPago.PENDIENTE
        )
        
        db.add(pago)
        
        if is_creator:
            # Creador: Registrar pago directamente aprobado
            prestamo.monto_pagado += monto_pago
            
            # Calcular el monto total con intereses para verificar si está completamente pagado
            calculos = PrestamoService.calcular_monto_total(
                prestamo.monto, prestamo.tasa_interes, prestamo.plazo_meses
            )
            monto_total_con_intereses = calculos["monto_total"]
            
            # Verificar si el préstamo está completamente pagado (monto + intereses)
            if prestamo.monto_pagado >= monto_total_con_intereses:
                prestamo.estado = EstadoPrestamo.PAGADO
            
            pago.aprobado_por = user_id
            pago.fecha_aprobacion = datetime.utcnow()
            
            # Crear transacción de pago aprobado
            nueva_transaccion = Transaccion(
                natillera_id=prestamo.natillera_id,
                creado_por=user_id,
                tipo=TipoTransaccion.EFECTIVO,
                categoria="pago de prestamo",
                monto=monto_pago,
                fecha=datetime.utcnow(),
                descripcion=f"Pago registrado de préstamo #{prestamo.id} por {monto_pago}",
                prestamo_id=prestamo.id
            )
            db.add(nueva_transaccion)
        # Si no es creador, el pago queda pendiente
        
        db.commit()
        db.refresh(prestamo)
        
        return prestamo
    
    @staticmethod
    def aprobar_pago_pendiente(
        db: Session,
        pago_id: int,
        user_id: int
    ) -> Prestamo:
        """Aprueba un pago pendiente de un préstamo (solo el creador puede hacerlo)"""
        
        # Obtener el pago
        pago = db.query(PagoPrestamo).filter(PagoPrestamo.id == pago_id).first()
        if not pago:
            raise ValueError("Pago no encontrado")
        
        # Verificar que sea un pago pendiente
        if pago.estado != EstadoPago.PENDIENTE:
            raise ValueError("Este pago no está pendiente de aprobación")
        
        # Obtener el préstamo
        prestamo = db.query(Prestamo).filter(Prestamo.id == pago.prestamo_id).first()
        if not prestamo:
            raise ValueError("Préstamo no encontrado")
        
        # Obtener el usuario
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        
        # Verificar que el usuario sea el creador de la natillera
        natillera = PrestamoService.get_natillera_by_id(db, prestamo.natillera_id)
        if not PrestamoService.user_is_natillera_creator(natillera, user):
            raise ValueError("Solo el creador de la natillera puede aprobar pagos pendientes")
        
        # Aprobar el pago
        pago.estado = EstadoPago.APROBADO
        pago.aprobado_por = user_id
        pago.fecha_aprobacion = datetime.utcnow()
        
        # Actualizar el monto pagado del préstamo
        prestamo.monto_pagado += pago.monto
        
        # Calcular el monto total con intereses para verificar si está completamente pagado
        calculos = PrestamoService.calcular_monto_total(
            prestamo.monto, prestamo.tasa_interes, prestamo.plazo_meses
        )
        monto_total_con_intereses = calculos["monto_total"]
        
        # Verificar si el préstamo está completamente pagado (monto + intereses)
        if prestamo.monto_pagado >= monto_total_con_intereses:
            prestamo.estado = EstadoPrestamo.PAGADO
        
        # Crear transacción de pago aprobado
        nueva_transaccion = Transaccion(
            natillera_id=prestamo.natillera_id,
            creado_por=pago.registrado_por,
            tipo=TipoTransaccion.EFECTIVO,
            categoria="pago de prestamo",
            monto=pago.monto,
            fecha=datetime.utcnow(),
            descripcion=f"Pago aprobado de préstamo #{prestamo.id} por {pago.monto}",
            prestamo_id=prestamo.id
        )
        db.add(nueva_transaccion)
        
        db.commit()
        db.refresh(prestamo)
        
        return prestamo
    
    @staticmethod
    def get_pagos_pendientes_por_creador(
        db: Session,
        user_id: int
    ) -> List[dict]:
        """Obtiene todos los pagos pendientes de aprobación para las natilleras donde el usuario es creador"""
        
        # Obtener todas las natilleras donde el usuario es creador
        natilleras_creadas = db.query(Natillera).filter(Natillera.creator_id == user_id).all()
        natillera_ids = [n.id for n in natilleras_creadas]
        
        if not natillera_ids:
            return []
        
        # Obtener pagos pendientes de estas natilleras
        pagos_pendientes = db.query(PagoPrestamo).filter(
            PagoPrestamo.estado == EstadoPago.PENDIENTE,
            PagoPrestamo.prestamo_id.in_(
                db.query(Prestamo.id).filter(Prestamo.natillera_id.in_(natillera_ids))
            )
        ).all()
        
        # Formatear la respuesta
        resultado = []
        for pago in pagos_pendientes:
            prestamo = db.query(Prestamo).filter(Prestamo.id == pago.prestamo_id).first()
            if prestamo:
                resultado.append({
                    "id": pago.id,
                    "prestamo_id": pago.prestamo_id,
                    "monto": pago.monto,
                    "fecha_pago": pago.fecha_pago,
                    "prestatario": prestamo.nombre_prestatario,
                    "prestamo_monto": prestamo.monto
                })
        
        return resultado
