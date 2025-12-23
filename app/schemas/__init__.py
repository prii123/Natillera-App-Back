from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum

# Enums
class AporteStatusEnum(str, Enum):
    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"

class NatilleraEstadoEnum(str, Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"

class InvitacionEstadoEnum(str, Enum):
    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"

class TipoTransaccionEnum(str, Enum):
    EFECTIVO = "efectivo"
    PRESTAMO = "prestamo"
    INGRESO = "ingreso"
    GASTO = "gasto"

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Natillera Schemas
class NatilleraBase(BaseModel):
    name: str
    monthly_amount: Decimal

class NatilleraCreate(NatilleraBase):
    pass

class NatilleraUpdate(BaseModel):
    estado: Optional[NatilleraEstadoEnum] = None
    name: Optional[str] = None
    monthly_amount: Optional[Decimal] = None

class NatilleraResponse(NatilleraBase):
    id: int
    creator_id: int
    created_at: datetime
    estado: NatilleraEstadoEnum
    creator: UserResponse
    
    class Config:
        from_attributes = True

class NatilleraWithMembers(NatilleraResponse):
    members: List[UserResponse]
    
    class Config:
        from_attributes = True

# Aporte Schemas
class AporteBase(BaseModel):
    amount: Decimal
    month: int
    year: int

class AporteCreate(AporteBase):
    natillera_id: int

class AporteUpdate(BaseModel):
    status: AporteStatusEnum
    rejection_reason: Optional[str] = None

class AporteResponse(AporteBase):
    id: int
    user_id: int
    natillera_id: int
    status: AporteStatusEnum
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user: UserResponse
    
    class Config:
        from_attributes = True

class AporteWithNatillera(AporteResponse):
    natillera: NatilleraResponse
    
    class Config:
        from_attributes = True

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

# Invitacion Schemas
class InvitacionBase(BaseModel):
    natillera_id: int
    invited_email: EmailStr

class InvitacionCreate(InvitacionBase):
    pass

class InvitacionResponse(BaseModel):
    id: int
    natillera_id: int
    invited_user_id: int
    inviter_user_id: int
    estado: InvitacionEstadoEnum
    created_at: datetime
    updated_at: datetime
    natillera: NatilleraResponse
    inviter_user: UserResponse
    
    class Config:
        from_attributes = True


# Transaccion Schemas
class TransaccionBase(BaseModel):
    tipo: TipoTransaccionEnum
    categoria: str
    monto: Decimal
    descripcion: Optional[str] = None
    fecha: Optional[datetime] = None

class TransaccionCreate(TransaccionBase):
    natillera_id: int

class TransaccionUpdate(BaseModel):
    categoria: Optional[str] = None
    monto: Optional[Decimal] = None
    descripcion: Optional[str] = None
    fecha: Optional[datetime] = None

class TransaccionResponse(TransaccionBase):
    id: int
    natillera_id: int
    creado_por: int
    aporte_id: Optional[int] = None
    prestamo_id: Optional[int] = None
    created_at: datetime
    creador: UserResponse
    miembro: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True

class BalanceResponse(BaseModel):
    efectivo: Decimal
    prestamos: Decimal
    ingresos: Decimal
    gastos: Decimal
    capital_disponible: Decimal


# Prestamo Schemas
class EstadoPrestamoEnum(str, Enum):
    ACTIVO = "activo"
    PAGADO = "pagado"
    VENCIDO = "vencido"
    CANCELADO = "cancelado"


class PrestamoBase(BaseModel):
    monto: Decimal
    tasa_interes: Decimal
    plazo_meses: int
    nombre_prestatario: str
    telefono_prestatario: Optional[str] = None
    email_prestatario: Optional[str] = None
    direccion_prestatario: Optional[str] = None
    referente_id: int
    notas: Optional[str] = None


class PrestamoCreate(PrestamoBase):
    natillera_id: int
    fecha_inicio: Optional[datetime] = None


class PrestamoUpdate(BaseModel):
    estado: Optional[EstadoPrestamoEnum] = None
    monto_pagado: Optional[Decimal] = None
    notas: Optional[str] = None
    monto: Optional[Decimal] = None
    tasa_interes: Optional[Decimal] = None


class PrestamoResponse(PrestamoBase):
    id: int
    natillera_id: int
    fecha_inicio: datetime
    fecha_vencimiento: datetime
    estado: EstadoPrestamoEnum
    monto_pagado: Decimal
    creado_por: int
    created_at: datetime
    updated_at: datetime
    referente: UserResponse
    creador: UserResponse
    
    class Config:
        from_attributes = True


class PrestamoDetalle(PrestamoResponse):
    monto_pendiente: Decimal
    interes_total: Decimal
    monto_total: Decimal
    dias_restantes: int
    
    class Config:
        from_attributes = True


class PagoRequest(BaseModel):
    monto_pago: Decimal


class PagoPendienteResponse(BaseModel):
    id: int
    prestamo_id: int
    monto: Decimal
    fecha_pago: datetime
    prestatario: str
    prestamo_monto: Decimal
    
    class Config:
        from_attributes = True


class PagoPrestamoBase(BaseModel):
    prestamo_id: int
    monto: Decimal
    fecha_pago: Optional[datetime] = None
    notas: Optional[str] = None


class PagoPrestamoCreate(PagoPrestamoBase):
    pass


class PagoPrestamoResponse(PagoPrestamoBase):
    id: int
    estado: str
    registrado_por: int
    aprobado_por: Optional[int] = None
    fecha_aprobacion: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PagosPrestamoResponse(BaseModel):
    prestamo: PrestamoResponse
    pagos: List[PagoPrestamoResponse]
    
    class Config:
        from_attributes = True


# Politica Schemas
class PoliticaBase(BaseModel):
    titulo: str
    descripcion: str
    orden: Optional[int] = 0


class PoliticaCreate(PoliticaBase):
    natillera_id: int


class PoliticaUpdate(PoliticaBase):
    pass


class PoliticaResponse(PoliticaBase):
    id: int
    natillera_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
