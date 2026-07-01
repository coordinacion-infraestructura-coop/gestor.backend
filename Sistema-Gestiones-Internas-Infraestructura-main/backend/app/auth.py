# app/auth.py
from fastapi import Header, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests
from typing import Optional, Dict, Any

from config import settings
from bq import bq_client, fqtn
from deps import qparams


def _get_bq_user(email: str) -> Optional[Dict[str, Any]]:
    """
    Busca el usuario en BigQuery (tabla usuarios_roles).
    Debe existir y estar activo para autorizar.
    """
    table = fqtn("infra_gestion.usuarios_roles")

    # Normalizamos 'activo' a BOOL:
    # - si activo ya es BOOL -> SAFE_CAST(activo AS BOOL) funciona
    # - si activo es STRING ("true"/"false") -> SAFE_CAST da NULL, entonces usamos LOWER(...) = "true"
    q = f"""
    SELECT
      email,
      nombre,
      rol,
      CASE
        WHEN SAFE_CAST(activo AS BOOL) IS NOT NULL THEN SAFE_CAST(activo AS BOOL)
        WHEN LOWER(CAST(activo AS STRING)) = "true" THEN TRUE
        ELSE FALSE
      END AS activo
    FROM `{table}`
    WHERE LOWER(email) = LOWER(@email)
    LIMIT 1
    """

    job = bq_client().query(q, job_config=qparams([("email", "STRING", email)]))
    rows = list(job.result())
    return dict(rows[0]) if rows else None


def _get_user_modulos(email: str) -> list:
    """
    Devuelve los módulos activos asignados al usuario.
    Retorna [] silenciosamente si la tabla no existe o hay error (compatibilidad
    con entornos donde el DDL de fase1 aún no fue ejecutado).
    """
    try:
        table = fqtn("infra_gestion.usuario_modulos")
        q = f"""
        SELECT modulo
        FROM `{table}`
        WHERE LOWER(email) = LOWER(@email)
          AND activo = TRUE
        """
        job = bq_client().query(q, job_config=qparams([("email", "STRING", email)]))
        return [row["modulo"] for row in job.result()]
    except Exception:
        return []


def require_user(
    authorization: str = Header(default=""),
    x_forwarded_authorization: str = Header(default="", alias="X-Forwarded-Authorization"),
) -> Dict[str, Any]:
    """
    Dos rutas de autenticación:
    - Llamada vía API Gateway: X-Forwarded-Authorization con Firebase JWT (aud=gestorcooperativo)
    - Llamada directa legacy (Vanilla JS): Authorization con Google OAuth2 token
    """
    # El API Gateway reemplaza Authorization con su propio SA token;
    # el token del usuario queda en X-Forwarded-Authorization.
    gateway_mode = x_forwarded_authorization.startswith("Bearer ")
    raw = x_forwarded_authorization if gateway_mode else authorization

    if not isinstance(raw, str) or not raw.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = raw.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    try:
        if gateway_mode:
            claims = id_token.verify_firebase_token(
                token,
                requests.Request(),
                audience="gestorcooperativo",
            )
        else:
            claims = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.google_client_id,
            )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = (claims.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=401, detail="Token without email")

    user = _get_bq_user(email)
    if not user:
        raise HTTPException(status_code=403, detail="Not authorized (user not found)")

    if not bool(user.get("activo")):
        raise HTTPException(status_code=403, detail="Not authorized (inactive user)")

    modulos = _get_user_modulos(email)
    return {
        "email": user["email"],
        "nombre": user.get("nombre"),
        "rol": user["rol"],
        "modulos": modulos,
    }
