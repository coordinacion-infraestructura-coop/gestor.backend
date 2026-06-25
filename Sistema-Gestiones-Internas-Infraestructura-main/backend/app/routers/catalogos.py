from fastapi import APIRouter, Depends, HTTPException, Query
from bq import bq_client, fqtn
from deps import qparams, current_user

router = APIRouter(prefix="/catalogos", tags=["catalogos"])


@router.get("/estados")
def estados(user=Depends(current_user)):
    q = f"""
    SELECT id, nombre, orden, activo
    FROM `{fqtn("cat_estado")}`
    WHERE activo = TRUE
    ORDER BY orden, nombre
    """
    return [dict(r) for r in bq_client().query(q).result()]


@router.get("/urgencias")
def urgencias(user=Depends(current_user)):
    q = f"""
    SELECT id, nombre, orden, activo
    FROM `{fqtn("cat_urgencia")}`
    WHERE activo = TRUE
    ORDER BY orden, nombre
    """
    return [dict(r) for r in bq_client().query(q).result()]


@router.get("/ministerios")
def ministerios(user=Depends(current_user)):
    q = f"""
    SELECT id, nombre, activo, orden
    FROM `{fqtn("cat_ministerio_agencia")}`
    WHERE activo = TRUE
    ORDER BY orden, nombre
    """
    return [dict(r) for r in bq_client().query(q).result()]


@router.get("/categorias")
def categorias(user=Depends(current_user)):
    q = f"""
    SELECT id, nombre, activo, orden, descripcion
    FROM `{fqtn("cat_categoria_general")}`
    WHERE activo = TRUE
    ORDER BY orden, nombre
    """
    return [dict(r) for r in bq_client().query(q).result()]


# ✅ NUEVO: Tipos de gestión
@router.get("/tipos-gestion")
def tipos_gestion(user=Depends(current_user)):
    q = f"""
    SELECT id, nombre, activo, orden, descripcion
    FROM `{fqtn("cat_tipo_gestion")}`
    WHERE activo = TRUE
    ORDER BY orden, nombre
    """
    return [dict(r) for r in bq_client().query(q).result()]


# ✅ NUEVO: Canales de origen
@router.get("/canales-origen")
def canales_origen(user=Depends(current_user)):
    q = f"""
    SELECT id, nombre, activo, orden, descripcion
    FROM `{fqtn("cat_canal_origen")}`
    WHERE activo = TRUE
    ORDER BY orden, nombre
    """
    return [dict(r) for r in bq_client().query(q).result()]


@router.get("/departamentos")
def departamentos(user=Depends(current_user)):
    q = f"""
    SELECT DISTINCT departamento
    FROM `{fqtn("geo_localidades")}`
    WHERE departamento IS NOT NULL AND TRIM(departamento) != ''
    ORDER BY departamento
    """
    return [r["departamento"] for r in bq_client().query(q).result()]


@router.get("/localidades")
def localidades(
    departamento: str = Query(..., min_length=1),
    user=Depends(current_user),
):
    q = f"""
    SELECT localidad
    FROM `{fqtn("geo_localidades")}`
    WHERE UPPER(TRIM(departamento)) = UPPER(TRIM(@depto))
      AND localidad IS NOT NULL AND TRIM(localidad) != ''
    ORDER BY localidad
    """
    job = bq_client().query(q, job_config=qparams([("depto", "STRING", departamento)]))
    return [r["localidad"] for r in job.result()]


@router.get("/modulos")
def modulos(user=Depends(current_user)):
    q = f"""
    SELECT id, nombre, descripcion, activo, orden
    FROM `{fqtn("infra_gestion.cat_modulos")}`
    WHERE activo = TRUE
    ORDER BY orden, nombre
    """
    return [dict(r) for r in bq_client().query(q).result()]


@router.get("/geo")
def geo_lookup(
    departamento: str = Query(..., min_length=1),
    localidad: str = Query(..., min_length=1),
    user=Depends(current_user),
):
    q = f"""
    SELECT
      id_geo,
      departamento,
      localidad,
      lat_centro AS lat,
      lon_centro AS lon
    FROM `{fqtn("geo_localidades")}`
    WHERE activo = TRUE
      AND UPPER(TRIM(departamento)) = UPPER(TRIM(@depto))
      AND UPPER(TRIM(localidad)) = UPPER(TRIM(@loc))
    LIMIT 1
    """

    job = bq_client().query(
        q,
        job_config=qparams([
            ("depto", "STRING", departamento),
            ("loc", "STRING", localidad),
        ])
    )

    rows = list(job.result())
    if not rows:
        raise HTTPException(
            status_code=400,
            detail="Departamento/Localidad inválidos (no existen en geo_localidades)"
        )

    r = rows[0]
    out = {
        "id_geo": r.get("id_geo"),
        "departamento": r.get("departamento"),
        "localidad": r.get("localidad"),
        "lat": float(r.get("lat")) if r.get("lat") is not None else None,
        "lon": float(r.get("lon")) if r.get("lon") is not None else None,
    }
    return out
