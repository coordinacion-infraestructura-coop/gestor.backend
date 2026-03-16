from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date

Rol = Literal["Admin", "Operador", "Supervisor", "Consulta"]
Estado = Literal[
    "INGRESADO",
    "DERIVADO A SUAC",
    "LISTA PARA INNAUGURAR",
    "FINALIZADA",
    "NO REMITE SUAC",
    "ARCHIVADO",
]
Urgencia = Literal["Alta", "Media", "Baja"]

class GestionCreate(BaseModel):
    ministerio_agencia_id: str
    categoria_general_id: str
    detalle: str = Field(min_length=1)

    departamento: str = Field(min_length=1)
    localidad: str = Field(min_length=1)

    direccion: Optional[str] = None
    observaciones: Optional[str] = None
    urgencia: Optional[Urgencia] = "Media"

    # ✅ NUEVOS CAMPOS
    tipo_gestion: Optional[str] = None        # ej: TG_CONSULTA, TG_DEMANDA...
    canal_origen: Optional[str] = None        # ej: CO_AGENDA, CO_TELEFONO...

    # Campos extendidos que ya venías usando en UI (si existen en tu payload)
    organismo_id: Optional[str] = None
    subtipo_detalle: Optional[str] = None
    costo_estimado: Optional[float] = None
    costo_moneda: Optional[str] = None
    nro_expediente: Optional[str] = None


class GestionUpdate(BaseModel):
    ministerio_agencia_id: Optional[str] = None
    categoria_general_id: Optional[str] = None
    detalle: Optional[str] = None
    observaciones: Optional[str] = None
    urgencia: Optional[Urgencia] = None
    direccion: Optional[str] = None

    # obligatorios en edición también (si vienen, no pueden ser vacíos)
    departamento: Optional[str] = None
    localidad: Optional[str] = None

    # ✅ NUEVOS CAMPOS
    tipo_gestion: Optional[str] = None
    canal_origen: Optional[str] = None


class CambioEstado(BaseModel):
    nuevo_estado: Estado
    comentario: Optional[str] = None
    
    # ✅ NUEVOS CAMPOS EDITABLES
    nro_expediente: Optional[str] = None
    fecha_ingreso: Optional[date] = None
    departamento: Optional[str] = None
    localidad: Optional[str] = None

    # Campos extra que tu UI venía mandando
    derivado_a: Optional[str] = None
    acciones_implementadas: Optional[str] = None


class LocalidadInfoBase(BaseModel):
    departamento: str = Field(min_length=1)
    localidad: str = Field(min_length=1)
    habitantes: Optional[int] = None
    electores: Optional[int] = None
    intendente_jefe_comunal: Optional[str] = None
    partido_politico: Optional[str] = None


class LocalidadInfoUpsert(LocalidadInfoBase):
    pass


class LocalidadInfoResponse(LocalidadInfoBase):
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
