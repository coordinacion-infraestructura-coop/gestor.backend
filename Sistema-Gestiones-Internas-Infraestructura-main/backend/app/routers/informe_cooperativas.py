# Router FastAPI: /informe/cooperativas
# Endpoints de solo lectura para el informe del Ministerio de Cooperativas y Mutuales.
# Acceso: cualquier usuario autenticado (rol Consulta o superior).

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query

from bq import bq_client
from deps import current_user, qparams
import sql_informe_cooperativas as sql

router = APIRouter(prefix="/informe/cooperativas", tags=["informe-cooperativas"])

_DEFAULT_DESDE = date(2025, 12, 1)


def _run(query: str, params):
    job = bq_client().query(query, job_config=qparams(params))
    return [dict(r) for r in job.result()]


# ── /resumen ─────────────────────────────────────────────────────────────────
@router.get("/resumen")
def resumen(
    fecha_desde: date = Query(default=_DEFAULT_DESDE),
    fecha_hasta: date = Query(default_factory=date.today),
    user=Depends(current_user),
):
    """KPIs: total y desagregado por tema (finalizadas, en curso, urgentes)."""
    rows = _run(sql.RESUMEN, [
        ("fecha_desde", "DATE", fecha_desde.isoformat()),
        ("fecha_hasta", "DATE", fecha_hasta.isoformat()),
    ])
    total = sum(r["total"] for r in rows)
    return {
        "total": total,
        "fecha_desde": fecha_desde.isoformat(),
        "fecha_hasta": fecha_hasta.isoformat(),
        "por_tema": rows,
    }


# ── /temporal ─────────────────────────────────────────────────────────────────
@router.get("/temporal")
def temporal(
    fecha_desde: date = Query(default=_DEFAULT_DESDE),
    fecha_hasta: date = Query(default_factory=date.today),
    tema: Optional[str] = Query(default=None),
    user=Depends(current_user),
):
    """Evolución mensual: filas {mes, tema, total}."""
    rows = _run(sql.TEMPORAL, [
        ("fecha_desde", "DATE", fecha_desde.isoformat()),
        ("fecha_hasta", "DATE", fecha_hasta.isoformat()),
        ("tema", "STRING", tema or ""),
    ])
    return rows


# ── /por-departamento ────────────────────────────────────────────────────────
@router.get("/por-departamento")
def por_departamento(
    fecha_desde: date = Query(default=_DEFAULT_DESDE),
    fecha_hasta: date = Query(default_factory=date.today),
    tema: Optional[str] = Query(default=None),
    user=Depends(current_user),
):
    """Gestiones por tema × departamento."""
    rows = _run(sql.POR_DEPARTAMENTO, [
        ("fecha_desde", "DATE", fecha_desde.isoformat()),
        ("fecha_hasta", "DATE", fecha_hasta.isoformat()),
        ("tema", "STRING", tema or ""),
    ])
    return rows


# ── /puntos ──────────────────────────────────────────────────────────────────
@router.get("/puntos")
def puntos(
    fecha_desde: date = Query(default=_DEFAULT_DESDE),
    fecha_hasta: date = Query(default_factory=date.today),
    tema: Optional[str] = Query(default=None),
    user=Depends(current_user),
):
    """Todos los puntos con lat/lon para el mapa Leaflet."""
    rows = _run(sql.PUNTOS, [
        ("fecha_desde", "DATE", fecha_desde.isoformat()),
        ("fecha_hasta", "DATE", fecha_hasta.isoformat()),
        ("tema", "STRING", tema or ""),
    ])
    # Convertir tipos no serializables (date → str)
    for r in rows:
        if isinstance(r.get("fecha_ingreso"), date):
            r["fecha_ingreso"] = r["fecha_ingreso"].isoformat()
    return rows
