# app/routers/usuarios.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import uuid4
import json

from bq import bq_client
from deps import qparams, require_roles
from models import Rol

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class UsuarioCreate(BaseModel):
    email: EmailStr
    nombre: Optional[str] = None
    rol: Rol
    activo: bool = True


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[Rol] = None
    activo: Optional[bool] = None


def _insert_usuario_evento(actor_email: str, tipo_evento: str, usuario_email: str, payload: dict):
    """
    Inserta evento de auditoría en infra_gestion.usuarios_eventos.
    Requiere que exista esa tabla (vos la creas con DDL).
    """
    q = """
    INSERT INTO `infra_gestion.usuarios_eventos`
    (id_evento, ts_evento, actor_email, tipo_evento, usuario_email, payload_json)
    VALUES
    (@id_evento, CURRENT_TIMESTAMP(), @actor_email, @tipo_evento, @usuario_email, @payload_json)
    """
    bq_client().query(
        q,
        job_config=qparams([
            ("id_evento", "STRING", str(uuid4())),
            ("actor_email", "STRING", actor_email),
            ("tipo_evento", "STRING", tipo_evento),
            ("usuario_email", "STRING", usuario_email.lower()),
            ("payload_json", "STRING", json.dumps(payload, ensure_ascii=False)),
        ])
    ).result()


@router.get("/")
def list_usuarios(user=Depends(require_roles("Admin"))):
    """
    Lista usuarios desde infra_gestion.usuarios_roles.
    """
    q = """
    SELECT
      email, nombre, rol, activo,
      created_at, created_by, updated_at, updated_by
    FROM `infra_gestion.usuarios_roles`
    ORDER BY activo DESC, rol, email
    """
    return [dict(r) for r in bq_client().query(q).result()]


@router.post("/")
def create_usuario(payload: UsuarioCreate, user=Depends(require_roles("Admin"))):
    """
    Crea usuario en usuarios_roles.
    Si ya existe, devuelve 409.
    """
    q_exists = """
    SELECT COUNT(1) AS c
    FROM `infra_gestion.usuarios_roles`
    WHERE LOWER(email) = LOWER(@email)
    """
    c = list(
        bq_client().query(
            q_exists,
            job_config=qparams([("email", "STRING", payload.email.lower())])
        ).result()
    )[0]["c"]

    if c > 0:
        raise HTTPException(status_code=409, detail="El usuario ya existe")

    q = """
    INSERT INTO `infra_gestion.usuarios_roles`
    (email, nombre, rol, activo, created_at, created_by, updated_at, updated_by)
    VALUES
    (@email, @nombre, @rol, @activo, CURRENT_TIMESTAMP(), @actor, CURRENT_TIMESTAMP(), @actor)
    """
    bq_client().query(
        q,
        job_config=qparams([
            ("email", "STRING", payload.email.lower()),
            ("nombre", "STRING", payload.nombre),
            ("rol", "STRING", payload.rol),
            ("activo", "BOOL", payload.activo),
            ("actor", "STRING", user["email"]),
        ])
    ).result()

    _insert_usuario_evento(
        actor_email=user["email"],
        tipo_evento="CREACION",
        usuario_email=payload.email,
        payload=payload.model_dump(),
    )

    return {"ok": True}


@router.put("/{email}")
def update_usuario(email: str, payload: UsuarioUpdate, user=Depends(require_roles("Admin"))):
    """
    Actualiza nombre/rol/activo en usuarios_roles.
    """
    q = """
    UPDATE `infra_gestion.usuarios_roles`
    SET
      nombre = COALESCE(@nombre, nombre),
      rol = COALESCE(@rol, rol),
      activo = COALESCE(@activo, activo),
      updated_at = CURRENT_TIMESTAMP(),
      updated_by = @actor
    WHERE LOWER(email) = LOWER(@email)
    """
    bq_client().query(
        q,
        job_config=qparams([
            ("email", "STRING", email.lower()),
            ("nombre", "STRING", payload.nombre),
            ("rol", "STRING", payload.rol),
            ("activo", "BOOL", payload.activo),
            ("actor", "STRING", user["email"]),
        ])
    ).result()

    _insert_usuario_evento(
        actor_email=user["email"],
        tipo_evento="EDICION",
        usuario_email=email,
        payload=payload.model_dump(),
    )

    return {"ok": True}


@router.delete("/{email}")
def disable_usuario(email: str, user=Depends(require_roles("Admin"))):
    """
    Deshabilita usuario (activo = FALSE) en usuarios_roles.
    """
    q = """
    UPDATE `infra_gestion.usuarios_roles`
    SET
      activo = FALSE,
      updated_at = CURRENT_TIMESTAMP(),
      updated_by = @actor
    WHERE LOWER(email) = LOWER(@email)
    """
    bq_client().query(
        q,
        job_config=qparams([
            ("email", "STRING", email.lower()),
            ("actor", "STRING", user["email"]),
        ])
    ).result()

    _insert_usuario_evento(
        actor_email=user["email"],
        tipo_evento="DESHABILITAR",
        usuario_email=email,
        payload={"activo": False},
    )

    return {"ok": True}
