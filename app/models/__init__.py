from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, DateTime, Enum, Table, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

# Tabla de asociación para usuarios y natilleras
user_natillera = Table(
    'user_natillera',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('natillera_id', Integer, ForeignKey('natilleras.id'), primary_key=True),
    Column('joined_at', DateTime, default=datetime.utcnow)
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    created_natilleras = relationship("Natillera", back_populates="creator")
    natilleras = relationship("Natillera", secondary=user_natillera, back_populates="members")
    aportes = relationship("Aporte", back_populates="user")
    billetes_loteria = relationship("BilleteLoteria", back_populates="usuario", foreign_keys="BilleteLoteria.tomado_por")


class NatilleraEstado(str, enum.Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"


class Natillera(Base):
    __tablename__ = "natilleras"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    monthly_amount = Column(Numeric(10, 2), nullable=False)
    estado = Column(Enum(NatilleraEstado, name='natilleraestado', values_callable=lambda x: [e.value for e in x]), default=NatilleraEstado.ACTIVO, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    creator = relationship("User", back_populates="created_natilleras")
    members = relationship("User", secondary=user_natillera, back_populates="natilleras")
    aportes = relationship("Aporte", back_populates="natillera")


class AporteStatus(str, enum.Enum):
    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"


class InvitacionEstado(str, enum.Enum):
    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"


class Invitacion(Base):
    __tablename__ = "invitaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    natillera_id = Column(Integer, ForeignKey("natilleras.id"), nullable=False)
    invited_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    inviter_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    estado = Column(Enum(InvitacionEstado, name='invitacionestado', values_callable=lambda x: [e.value for e in x]), default=InvitacionEstado.PENDIENTE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    natillera = relationship("Natillera", foreign_keys=[natillera_id])
    invited_user = relationship("User", foreign_keys=[invited_user_id])
    inviter_user = relationship("User", foreign_keys=[inviter_user_id])


class Aporte(Base):
    __tablename__ = "aportes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    natillera_id = Column(Integer, ForeignKey("natilleras.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)
    status = Column(Enum(AporteStatus), default=AporteStatus.PENDIENTE, nullable=False)
    rejection_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    user = relationship("User", back_populates="aportes")
    natillera = relationship("Natillera", back_populates="aportes")


class TipoTransaccion(str, enum.Enum):
    EFECTIVO = "efectivo"  # Aportes de socios
    PRESTAMO = "prestamo"  # Préstamos realizados por la natillera
    PAGO_PRESTAMOS = "pago_prestamos"  # Pagos de préstamos realizados por la natillera
    PAGO_PRESTAMO_PENDIENTE = "pago_prestamo_pendiente"  # Pagos pendientes de aprobación
    INGRESO = "ingreso"    # Intereses y otros ingresos
    GASTO = "gasto"        # Costos y gastos


class Transaccion(Base):
    __tablename__ = "transacciones"
    
    id = Column(Integer, primary_key=True, index=True)
    natillera_id = Column(Integer, ForeignKey("natilleras.id"), nullable=False)
    tipo = Column(Enum(TipoTransaccion, name='tipotransaccion', values_callable=lambda x: [e.value for e in x]), nullable=False)
    categoria = Column(String, nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    descripcion = Column(String, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)
    creado_por = Column(Integer, ForeignKey("users.id"), nullable=False)
    aporte_id = Column(Integer, ForeignKey("aportes.id"), nullable=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    natillera = relationship("Natillera", foreign_keys=[natillera_id])
    creador = relationship("User", foreign_keys=[creado_por])
    aporte = relationship("Aporte", foreign_keys=[aporte_id])
    prestamo = relationship("Prestamo", foreign_keys=[prestamo_id], back_populates="transaccion")


class EstadoPago(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"


class PagoPrestamo(Base):
    __tablename__ = "pagos_prestamo"
    
    id = Column(Integer, primary_key=True, index=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    fecha_pago = Column(DateTime, default=datetime.utcnow, nullable=False)
    estado = Column(Enum(EstadoPago, name='estadopago', values_callable=lambda x: [e.value for e in x]), default=EstadoPago.PENDIENTE, nullable=False)
    registrado_por = Column(Integer, ForeignKey("users.id"), nullable=False)
    aprobado_por = Column(Integer, ForeignKey("users.id"), nullable=True)
    fecha_aprobacion = Column(DateTime, nullable=True)
    notas = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    prestamo = relationship("Prestamo", back_populates="pagos")
    registrador = relationship("User", foreign_keys=[registrado_por])
    aprobador = relationship("User", foreign_keys=[aprobado_por])


class EstadoPrestamo(str, enum.Enum):
    ACTIVO = "activo"
    PAGADO = "pagado"
    VENCIDO = "vencido"
    CANCELADO = "cancelado"


class Prestamo(Base):
    __tablename__ = "prestamos"
    
    id = Column(Integer, primary_key=True, index=True)
    natillera_id = Column(Integer, ForeignKey("natilleras.id"), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    tasa_interes = Column(Numeric(5, 2), nullable=False)  # Porcentaje
    plazo_meses = Column(Integer, nullable=False)
    fecha_inicio = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_vencimiento = Column(DateTime, nullable=False)
    
    # Información del prestatario (tercero)
    nombre_prestatario = Column(String, nullable=False)
    telefono_prestatario = Column(String, nullable=True)
    email_prestatario = Column(String, nullable=True)
    direccion_prestatario = Column(String, nullable=True)
    
    # Socio referente (quien avala o refiere al prestatario)
    referente_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Estado y pagos
    estado = Column(Enum(EstadoPrestamo, name='estadoprestamo', values_callable=lambda x: [e.value for e in x]), default=EstadoPrestamo.ACTIVO, nullable=False)
    monto_pagado = Column(Numeric(10, 2), default=0, nullable=False)
    notas = Column(String, nullable=True)
    aprobado = Column(Boolean, nullable=True)  # True=aprobado, False=rechazado, None=pendiente
    
    creado_por = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    natillera = relationship("Natillera", foreign_keys=[natillera_id])
    referente = relationship("User", foreign_keys=[referente_id])
    creador = relationship("User", foreign_keys=[creado_por])
    transaccion = relationship("Transaccion", back_populates="prestamo", uselist=False)
    pagos = relationship("PagoPrestamo", back_populates="prestamo")


class Politica(Base):
    __tablename__ = "politicas"
    
    id = Column(Integer, primary_key=True, index=True)
    natillera_id = Column(Integer, ForeignKey("natilleras.id"), nullable=False)
    titulo = Column(String, nullable=False)
    descripcion = Column(String, nullable=False)
    orden = Column(Integer, default=0, nullable=False)  # Para ordenar las políticas
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    natillera = relationship("Natillera", back_populates="politicas")


# Agregar relación a Natillera
Natillera.politicas = relationship("Politica", back_populates="natillera", cascade="all, delete-orphan")


class ArchivoAdjunto(Base):
    __tablename__ = "archivos_adjuntos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre_archivo = Column(String, nullable=False)
    ruta_archivo = Column(String, nullable=False)  # Key en MinIO
    tipo_archivo = Column(String, nullable=False)  # MIME type
    tamano = Column(Integer, nullable=False)  # Tamaño en bytes
    fecha_subida = Column(DateTime, default=datetime.utcnow, nullable=False)
    id_aporte = Column(Integer, ForeignKey("aportes.id"), nullable=True)
    id_pago_prestamo = Column(Integer, ForeignKey("pagos_prestamo.id"), nullable=True)
    id_usuario = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relaciones
    aporte = relationship("Aporte", back_populates="archivos_adjuntos")
    pago_prestamo = relationship("PagoPrestamo", back_populates="archivos_adjuntos")
    usuario = relationship("User", back_populates="archivos_adjuntos")


# Agregar relaciones inversas
Aporte.archivos_adjuntos = relationship("ArchivoAdjunto", back_populates="aporte", cascade="all, delete-orphan")
PagoPrestamo.archivos_adjuntos = relationship("ArchivoAdjunto", back_populates="pago_prestamo", cascade="all, delete-orphan")
User.archivos_adjuntos = relationship("ArchivoAdjunto", back_populates="usuario", cascade="all, delete-orphan")


class TipoSorteo(str, enum.Enum):
    LOTERIA = "loteria"
    RIFA = "rifa"


class EstadoSorteo(str, enum.Enum):
    ACTIVO = "activo"
    FINALIZADO = "finalizado"


class Sorteo(Base):
    __tablename__ = "sorteos"
    
    id = Column(Integer, primary_key=True, index=True)
    natillera_id = Column(Integer, ForeignKey("natilleras.id"), nullable=False)
    tipo = Column(Enum(TipoSorteo, name='tiposorteo', values_callable=lambda x: [e.value for e in x]), nullable=False)
    titulo = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_sorteo = Column(DateTime, nullable=True)
    estado = Column(Enum(EstadoSorteo, name='estadosorteo', values_callable=lambda x: [e.value for e in x]), default=EstadoSorteo.ACTIVO, nullable=False)
    creador_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    numero_ganador = Column(String(3), nullable=True)  # Número ganador cuando se finaliza
    
    # Relaciones
    natillera = relationship("Natillera", foreign_keys=[natillera_id])
    creador = relationship("User", foreign_keys=[creador_id])
    billetes = relationship("BilleteLoteria", back_populates="sorteo", cascade="all, delete-orphan")
    
    # Atributo para el ganador (se pobla dinámicamente)
    _ganador = None
    
    @property
    def ganador(self):
        """Propiedad para obtener el usuario ganador"""
        if self._ganador is not None:
            return self._ganador
        if self.numero_ganador and self.billetes:
            for billete in self.billetes:
                if billete.numero == self.numero_ganador:
                    self._ganador = billete.usuario
                    return self._ganador
        return None
    
    @ganador.setter
    def ganador(self, value):
        self._ganador = value


class EstadoBillete(str, enum.Enum):
    DISPONIBLE = "disponible"
    TOMADO = "tomado"


class BilleteLoteria(Base):
    __tablename__ = "billetes_loteria"
    
    id = Column(Integer, primary_key=True, index=True)
    sorteo_id = Column(Integer, ForeignKey("sorteos.id"), nullable=False)
    numero = Column(String(3), nullable=False)  # 000-100
    estado = Column(Enum(EstadoBillete, name='estadobillete', values_callable=lambda x: [e.value for e in x]), default=EstadoBillete.DISPONIBLE, nullable=False)
    tomado_por = Column(Integer, ForeignKey("users.id"), nullable=True)
    fecha_tomado = Column(DateTime, nullable=True)
    pagado = Column(Boolean, default=False, nullable=False)  # Indica si el billete ha sido pagado
    
    # Relaciones
    sorteo = relationship("Sorteo", back_populates="billetes")
    usuario = relationship("User", foreign_keys=[tomado_por])
    
    # Constraint único para sorteo + numero
    __table_args__ = (
        UniqueConstraint('sorteo_id', 'numero', name='unique_sorteo_numero'),
    )
