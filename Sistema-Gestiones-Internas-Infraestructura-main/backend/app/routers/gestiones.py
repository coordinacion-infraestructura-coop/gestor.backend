from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import uuid4
from datetime import date, datetime
from decimal import Decimal
import json

from google.cloud import bigquery

from bq import bq_client, fqtn
from deps import qparams, require_roles
from models import GestionCreate, CambioEstado, LocalidadInfoUpsert
import sql_gestiones as Q

router = APIRouter(prefix="/gestiones", tags=["gestiones"])
public_router = APIRouter(tags=["localidades-info"])


def _run(query: str, cfg: bigquery.QueryJobConfig):
    return bq_client().query(query, job_config=cfg).result()


def _one(query: str, cfg: bigquery.QueryJobConfig):
    rows = list(_run(query, cfg))
    return dict(rows[0]) if rows else None


def _fmt_tables(sql_text: str) -> str:
    return sql_text.format(
        gestiones=fqtn("infra_gestion.gestiones"),
        eventos=fqtn("infra_gestion.gestiones_eventos"),
        geo_localidades=fqtn("geo_localidades"),
        localidades_info=fqtn("infra_gestion.localidades_info"),
        departamentos_info=fqtn("infra_gestion.departamentos_info"),
    )


def _json_safe(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


def json_dumps_safe(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, default=_json_safe)


def _localidad_info_or_default(departamento: str, localidad: str):
    cfg = qparams([
        ("departamento", "STRING", departamento),
        ("localidad", "STRING", localidad),
    ])
    row = _one(_fmt_tables(Q.GET_LOCALIDAD_INFO), cfg) or {}
    return {
        "departamento": row.get("departamento") or departamento,
        "localidad": row.get("localidad") or localidad,
        "habitantes": row.get("habitantes"),
        "electores": row.get("electores"),
        "intendente_jefe_comunal": row.get("intendente_jefe_comunal"),
        "partido_politico": row.get("partido_politico"),
        "tipo_localidad": row.get("tipo_localidad"),
        "color_semaforo": row.get("color_semaforo"),
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
        "updated_by": row.get("updated_by"),
    }


def _departamento_info_or_default(departamento: str):
    cfg = qparams([
        ("departamento", "STRING", departamento),
    ])
    row = _one(_fmt_tables(Q.GET_DEPARTAMENTO_INFO), cfg) or {}
    return {
        "departamento": row.get("departamento") or departamento,
        "habitantes": row.get("habitantes"),
        "electores": row.get("electores"),
        "legislador_departamental": row.get("legislador_departamental"),
        "partido_politico": row.get("partido_politico"),
        "legislador_sabana1": row.get("legislador_sabana1"),
        "partido_politico_sabana1": row.get("partido_politico_sabana1"),
        "legislador_sabana2": row.get("legislador_sabana2"),
        "partido_politico_sabana2": row.get("partido_politico_sabana2"),
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
        "updated_by": row.get("updated_by"),
    }


def _estado_normalizado(value):
    return str(value or "").strip().upper()


def _urgencia_normalizada(value):
    return str(value or "").strip().lower()


def _gestion_sort_key(item):
    gestion = item.get("gestion") or {}
    urgencia = _urgencia_normalizada(gestion.get("urgencia"))
    estado = _estado_normalizado(gestion.get("estado"))
    prioridad = 3
    if urgencia == "alta":
        prioridad = 0
    elif estado not in {"FINALIZADA", "ARCHIVADO"}:
        prioridad = 1
    elif estado == "FINALIZADA":
        prioridad = 2

    fecha_ref = gestion.get("fecha_ingreso") or gestion.get("fecha_estado")
    if isinstance(fecha_ref, datetime):
        ts = fecha_ref.timestamp()
    elif isinstance(fecha_ref, date):
        ts = datetime.combine(fecha_ref, datetime.min.time()).timestamp()
    else:
        try:
            ts = datetime.fromisoformat(str(fecha_ref)).timestamp()
        except Exception:
            ts = 0
    return (prioridad, -ts)


@router.get("")
@router.get("/")
def list_gestiones(
    estado: str | None = None,
    ministerio: str | None = None,
    categoria: str | None = None,
    departamento: str | None = None,
    localidad: str | None = None,

    # búsqueda server-side
    q: str | None = None,

    # (opcionales por si después querés filtrar)
    tipo_gestion: str | None = None,
    canal_origen: str | None = None,

    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(require_roles("Admin", "Supervisor", "Operador", "Consulta")),
):
    cfg_count = qparams([
        ("estado", "STRING", estado),
        ("ministerio", "STRING", ministerio),
        ("categoria", "STRING", categoria),
        ("departamento", "STRING", departamento),
        ("localidad", "STRING", localidad),
        ("q", "STRING", q),

        ("tipo_gestion", "STRING", tipo_gestion),
        ("canal_origen", "STRING", canal_origen),
    ])
    total_row = _one(_fmt_tables(Q.COUNT_GESTIONES), cfg_count)
    total = int(total_row["total"]) if total_row and "total" in total_row else 0

    cfg_list = qparams([
        ("estado", "STRING", estado),
        ("ministerio", "STRING", ministerio),
        ("categoria", "STRING", categoria),
        ("departamento", "STRING", departamento),
        ("localidad", "STRING", localidad),
        ("q", "STRING", q),

        ("tipo_gestion", "STRING", tipo_gestion),
        ("canal_origen", "STRING", canal_origen),

        ("limit", "INT64", limit),
        ("offset", "INT64", offset),
    ])
    items = [dict(r) for r in _run(_fmt_tables(Q.LIST_GESTIONES), cfg_list)]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/resumen-territorial")
def get_resumen_territorial(
    departamento: str = Query(..., min_length=1),
    localidad: str | None = Query(None),
    user=Depends(require_roles("Admin", "Supervisor", "Operador", "Consulta")),
):
    localidad = (localidad or "").strip()
    solo_departamento = not localidad

    cfg_params = [("departamento", "STRING", departamento)]
    if not solo_departamento:
        cfg_params.append(("localidad", "STRING", localidad))
    cfg = qparams(cfg_params)

    if solo_departamento:
        territorio_info = _departamento_info_or_default(departamento)
        gestiones = [dict(r) for r in _run(_fmt_tables(Q.LIST_GESTIONES_RESUMEN_DEPARTAMENTO), cfg)]
        eventos = [dict(r) for r in _run(_fmt_tables(Q.LIST_EVENTOS_RESUMEN_DEPARTAMENTO), cfg)]
    else:
        territorio_info = _localidad_info_or_default(departamento, localidad)
        gestiones = [dict(r) for r in _run(_fmt_tables(Q.LIST_GESTIONES_RESUMEN_TERRITORIAL), cfg)]
        eventos = [dict(r) for r in _run(_fmt_tables(Q.LIST_EVENTOS_RESUMEN_TERRITORIAL), cfg)]

    eventos_por_gestion = {}
    for evento in eventos:
        if evento.get("metadata_json") is not None and not isinstance(evento.get("metadata_json"), str):
            evento["metadata_json"] = json_dumps_safe(evento.get("metadata_json"))
        eventos_por_gestion.setdefault(evento.get("id_gestion"), []).append(evento)

    items = []
    abiertas = 0
    finalizadas = 0
    urgentes = 0

    for gestion in gestiones:
        estado = _estado_normalizado(gestion.get("estado"))
        urgencia = _urgencia_normalizada(gestion.get("urgencia"))
        if estado not in {"FINALIZADA", "ARCHIVADO"}:
            abiertas += 1
        if estado == "FINALIZADA":
            finalizadas += 1
        if urgencia == "alta":
            urgentes += 1

        items.append({
            "gestion": gestion,
            "eventos": eventos_por_gestion.get(gestion.get("id_gestion"), []),
        })

    if solo_departamento:
        items.sort(key=lambda item: (
            str((item.get("gestion") or {}).get("localidad") or "").strip().upper(),
            *_gestion_sort_key(item),
        ))
    else:
        items.sort(key=_gestion_sort_key)

    return {
        "scope": "departamento" if solo_departamento else "localidad",
        "territorio_info": territorio_info,
        "localidad_info": territorio_info if not solo_departamento else None,
        "departamento_info": territorio_info if solo_departamento else None,
        "metricas": {
            "total_gestiones": len(gestiones),
            "abiertas": abiertas,
            "finalizadas": finalizadas,
            "urgentes": urgentes,
        },
        "gestiones": items,
    }


@router.get("/{id_gestion}")
def get_gestion(
    id_gestion: str,
    user=Depends(require_roles("Admin", "Supervisor", "Operador", "Consulta")),
):
    cfg = qparams([("id_gestion", "STRING", id_gestion)])
    g = _one(_fmt_tables(Q.GET_GESTION), cfg)
    if not g:
        raise HTTPException(status_code=404, detail="Gestión no encontrada")
    return g


@router.get("/{id_gestion}/eventos")
def list_eventos(
    id_gestion: str,
    user=Depends(require_roles("Admin", "Supervisor", "Operador", "Consulta")),
):
    cfg = qparams([("id_gestion", "STRING", id_gestion)])
    return [dict(r) for r in _run(_fmt_tables(Q.LIST_EVENTOS), cfg)]


@public_router.get("/localidades-info")
def get_localidad_info(
    departamento: str = Query(..., min_length=1),
    localidad: str = Query(..., min_length=1),
    user=Depends(require_roles("Admin", "Supervisor", "Operador", "Consulta")),
):
    return _localidad_info_or_default(departamento, localidad)


@public_router.put("/localidades-info")
def put_localidad_info(
    payload: LocalidadInfoUpsert,
    user=Depends(require_roles("Admin", "Supervisor", "Operador")),
):
    cfg_geo = qparams([
        ("departamento", "STRING", payload.departamento),
        ("localidad", "STRING", payload.localidad),
    ])
    geo = _one(_fmt_tables(Q.GET_GEO), cfg_geo)
    if not geo:
        raise HTTPException(
            status_code=400,
            detail="Departamento/Localidad inválidos (no existen en geo_localidades)"
        )

    actor = user.get("email") or user.get("usuario") or ""
    now_dt = datetime.utcnow()
    cfg = qparams([
        ("departamento", "STRING", payload.departamento),
        ("localidad", "STRING", payload.localidad),
        ("habitantes", "INT64", payload.habitantes),
        ("electores", "INT64", payload.electores),
        ("intendente_jefe_comunal", "STRING", payload.intendente_jefe_comunal),
        ("partido_politico", "STRING", payload.partido_politico),
        ("updated_at", "TIMESTAMP", now_dt),
        ("updated_by", "STRING", actor),
    ])
    _run(_fmt_tables(Q.UPSERT_LOCALIDAD_INFO), cfg)
    return _localidad_info_or_default(payload.departamento, payload.localidad)


@router.post("", status_code=201)
@router.post("/", status_code=201)
def create_gestion(
    payload: GestionCreate,
    user=Depends(require_roles("Admin", "Supervisor", "Operador")),
):
    # geo lookup
    cfg_geo = qparams([
        ("departamento", "STRING", payload.departamento),
        ("localidad", "STRING", payload.localidad),
    ])
    geo = _one(_fmt_tables(Q.GET_GEO), cfg_geo)
    if not geo:
        raise HTTPException(
            status_code=400,
            detail="Departamento/Localidad inválidos (no existen en geo_localidades)"
        )

    now_dt = datetime.utcnow()
    today = date.today()

    new_id = str(uuid4())
    actor = user.get("email") or user.get("usuario") or ""
    rol = user.get("rol")

    # BigQuery NUMERIC: pasamos string
    lat_val = geo.get("lat")
    lon_val = geo.get("lon")
    lat_num = None if lat_val is None else str(lat_val)
    lon_num = None if lon_val is None else str(lon_val)

    cfg_ins = qparams([
        ("id_gestion", "STRING", new_id),
        ("nro_expediente", "STRING", getattr(payload, "nro_expediente", None)),
        ("origen", "STRING", "APP"),

        ("estado", "STRING", "INGRESADO"),
        ("fecha_ingreso", "DATE", today),
        ("fecha_estado", "TIMESTAMP", now_dt),
        ("fecha_finalizacion", "DATE", None),

        ("urgencia", "STRING", payload.urgencia or "Media"),

        ("ministerio_agencia_id", "STRING", payload.ministerio_agencia_id),
        ("organismo_id", "STRING", getattr(payload, "organismo_id", None)),
        ("derivado_a_id", "STRING", None),

        ("categoria_general_id", "STRING", payload.categoria_general_id),
        ("subcategoria_id", "STRING", None),
        ("tipo_demanda_principal_id", "STRING", None),
        ("subtipo_detalle", "STRING", getattr(payload, "subtipo_detalle", None)),

        ("detalle", "STRING", payload.detalle),
        ("observaciones", "STRING", payload.observaciones),

        ("geo_id", "STRING", geo.get("id_geo")),
        ("departamento", "STRING", payload.departamento),
        ("localidad", "STRING", payload.localidad),
        ("direccion", "STRING", payload.direccion),

        ("lat", "NUMERIC", lat_num),
        ("lon", "NUMERIC", lon_num),

        ("costo_estimado", "NUMERIC", getattr(payload, "costo_estimado", None)),
        ("costo_moneda", "STRING", getattr(payload, "costo_moneda", None)),

        ("created_at", "TIMESTAMP", now_dt),
        ("created_by", "STRING", actor),
        ("updated_at", "TIMESTAMP", now_dt),
        ("updated_by", "STRING", actor),

        # ✅ NUEVOS
        ("tipo_gestion", "STRING", getattr(payload, "tipo_gestion", None)),
        ("canal_origen", "STRING", getattr(payload, "canal_origen", None)),
    ])
    _run(_fmt_tables(Q.INSERT_GESTION), cfg_ins)

    meta = {
        "ministerio_agencia_id": payload.ministerio_agencia_id,
        "categoria_general_id": payload.categoria_general_id,
        "organismo_id": getattr(payload, "organismo_id", None),
        "subtipo_detalle": getattr(payload, "subtipo_detalle", None),
        "costo_estimado": getattr(payload, "costo_estimado", None),
        "costo_moneda": getattr(payload, "costo_moneda", None),
        "nro_expediente": getattr(payload, "nro_expediente", None),
        "departamento": payload.departamento,
        "localidad": payload.localidad,
        "geo_id": geo.get("id_geo"),

        # ✅ NUEVOS
        "tipo_gestion": getattr(payload, "tipo_gestion", None),
        "canal_origen": getattr(payload, "canal_origen", None),
    }

    cfg_ev = qparams([
        ("id_evento", "STRING", str(uuid4())),
        ("id_gestion", "STRING", new_id),
        ("fecha_evento", "TIMESTAMP", now_dt),
        ("usuario", "STRING", actor),
        ("rol_usuario", "STRING", rol),
        ("tipo_evento", "STRING", "CREACION"),
        ("estado_anterior", "STRING", None),
        ("estado_nuevo", "STRING", "INGRESADO"),
        ("campo_modificado", "STRING", None),
        ("valor_anterior", "STRING", None),
        ("valor_nuevo", "STRING", None),
        ("comentario", "STRING", None),
        ("metadata_json", "STRING", json_dumps_safe(meta)),
    ])
    _run(_fmt_tables(Q.INSERT_EVENTO), cfg_ev)

    return {"id_gestion": new_id}


@router.post("/{id_gestion}/cambiar-estado")
def cambiar_estado(
    id_gestion: str,
    payload: CambioEstado,
    user=Depends(require_roles("Admin", "Supervisor", "Operador")),
):
    cfg_get = qparams([("id_gestion", "STRING", id_gestion)])
    g = _one(_fmt_tables(Q.GET_GESTION), cfg_get)
    if not g:
        raise HTTPException(status_code=404, detail="Gestión no encontrada")

    estado_anterior = g.get("estado")
    old_fecha_ingreso = g.get("fecha_ingreso")
    now_dt = datetime.utcnow()
    actor = user.get("email") or user.get("usuario") or ""
    rol = user.get("rol")

    # Si el usuario no edita ciertos campos, NO se tocan (se conserva valor actual)
    # - nro_expediente:
    #     * None  => no editó => conservar
    #     * ""    => lo vació => guardar NULL
    #     * "..." => editó => guardar
    # - fecha_ingreso:
    #     * None  => no editó => conservar
    nuevo_nro_expediente_raw = payload.nro_expediente

    if nuevo_nro_expediente_raw is None:
        # No editó el sticker: conservar
        nuevo_nro_expediente = g.get("nro_expediente")
    else:
        # Editó: si dejó vacío => NULL; si no => valor limpio
        nuevo_nro_expediente_clean = str(nuevo_nro_expediente_raw).strip()
        nuevo_nro_expediente = nuevo_nro_expediente_clean if nuevo_nro_expediente_clean != "" else None

    nueva_fecha_ingreso = payload.fecha_ingreso
    if nueva_fecha_ingreso is None:
        nueva_fecha_ingreso = g.get("fecha_ingreso")
        # BigQuery suele devolver DATE como date, pero si llega string ("YYYY-MM-DD") lo parseamos
        if isinstance(nueva_fecha_ingreso, str):
            try:
                nueva_fecha_ingreso = date.fromisoformat(nueva_fecha_ingreso)
            except ValueError:
                pass

    # Departamento / Localidad:
    # - Si no se editan (None), se conserva el valor actual
    # - No permitimos vaciarlos
    nuevo_departamento = payload.departamento
    if nuevo_departamento is None:
        nuevo_departamento = g.get("departamento")
    else:
        nuevo_departamento = str(nuevo_departamento).strip()
        if nuevo_departamento == "":
            raise HTTPException(status_code=400, detail="Departamento no puede quedar vacío")

    nueva_localidad = payload.localidad
    if nueva_localidad is None:
        nueva_localidad = g.get("localidad")
    else:
        nueva_localidad = str(nueva_localidad).strip()
        if nueva_localidad == "":
            raise HTTPException(status_code=400, detail="Localidad no puede quedar vacía")

    # Validar que la combinación exista en geo_localidades
    cfg_geo = qparams([
        ("departamento", "STRING", nuevo_departamento),
        ("localidad", "STRING", nueva_localidad),
    ])
    geo = _one(_fmt_tables(Q.GET_GEO), cfg_geo)
    if not geo:
        raise HTTPException(
            status_code=400,
            detail="Departamento/Localidad inválidos (no existen en geo_localidades)"
        )

    cfg_upd = qparams([
        ("id_gestion", "STRING", id_gestion),
        ("old_fecha_ingreso", "DATE", old_fecha_ingreso),
        ("nuevo_estado", "STRING", payload.nuevo_estado),
        ("fecha_estado", "TIMESTAMP", now_dt),
        ("derivado_a_id", "STRING", payload.derivado_a),
        ("nro_expediente", "STRING", nuevo_nro_expediente),
        ("fecha_ingreso", "DATE", nueva_fecha_ingreso),
        ("departamento", "STRING", nuevo_departamento),
        ("localidad", "STRING", nueva_localidad),
        ("updated_at", "TIMESTAMP", now_dt),
        ("updated_by", "STRING", actor),
    ])
    job = bq_client().query(_fmt_tables(Q.UPDATE_ESTADO_GESTION), job_config=cfg_upd)
    job.result()

    if job.num_dml_affected_rows == 0:
        raise HTTPException(status_code=500, detail="No se pudo actualizar la gestión (0 filas afectadas). Verifique el ID y la fecha original.")

    meta = {
        "derivado_a": payload.derivado_a,
        "acciones_implementadas": payload.acciones_implementadas,
        "nro_expediente": nuevo_nro_expediente,
        "fecha_ingreso": str(nueva_fecha_ingreso) if nueva_fecha_ingreso else None,
        "departamento": nuevo_departamento,
        "localidad": nueva_localidad,
        "geo_id": geo.get("id_geo") if geo else None,
    }

    # Evento principal de cambio de estado
    cfg_ev = qparams([
        ("id_evento", "STRING", str(uuid4())),
        ("id_gestion", "STRING", id_gestion),
        ("fecha_evento", "TIMESTAMP", now_dt),
        ("usuario", "STRING", actor),
        ("rol_usuario", "STRING", rol),
        ("tipo_evento", "STRING", "CAMBIO_ESTADO"),
        ("estado_anterior", "STRING", estado_anterior),
        ("estado_nuevo", "STRING", payload.nuevo_estado),
        ("campo_modificado", "STRING", None),
        ("valor_anterior", "STRING", None),
        ("valor_nuevo", "STRING", None),
        ("comentario", "STRING", payload.comentario),
        ("metadata_json", "STRING", json_dumps_safe(meta)),
    ])
    _run(_fmt_tables(Q.INSERT_EVENTO), cfg_ev)

    # Auditoría explícita de cambios de datos relevantes
    cambios = []

    old_nro_expediente = g.get("nro_expediente")
    if (old_nro_expediente or None) != (nuevo_nro_expediente or None):
        cambios.append(("nro_expediente", old_nro_expediente, nuevo_nro_expediente))

    old_fecha_ingreso_str = str(old_fecha_ingreso) if old_fecha_ingreso else None
    nueva_fecha_ingreso_str = str(nueva_fecha_ingreso) if nueva_fecha_ingreso else None
    if old_fecha_ingreso_str != nueva_fecha_ingreso_str:
        cambios.append(("fecha_ingreso", old_fecha_ingreso_str, nueva_fecha_ingreso_str))

    old_departamento = g.get("departamento")
    if (old_departamento or None) != (nuevo_departamento or None):
        cambios.append(("departamento", old_departamento, nuevo_departamento))

    old_localidad = g.get("localidad")
    if (old_localidad or None) != (nueva_localidad or None):
        cambios.append(("localidad", old_localidad, nueva_localidad))

    for campo, anterior, nuevo in cambios:
        meta_cambio = {
            "campo": campo,
            "valor_anterior": anterior,
            "valor_nuevo": nuevo,
            "estado_contexto": payload.nuevo_estado,
        }
        cfg_ev_cambio = qparams([
            ("id_evento", "STRING", str(uuid4())),
            ("id_gestion", "STRING", id_gestion),
            ("fecha_evento", "TIMESTAMP", now_dt),
            ("usuario", "STRING", actor),
            ("rol_usuario", "STRING", rol),
            ("tipo_evento", "STRING", "ACTUALIZA_DATO"),
            ("estado_anterior", "STRING", estado_anterior),
            ("estado_nuevo", "STRING", payload.nuevo_estado),
            ("campo_modificado", "STRING", campo),
            ("valor_anterior", "STRING", None if anterior is None else str(anterior)),
            ("valor_nuevo", "STRING", None if nuevo is None else str(nuevo)),
            ("comentario", "STRING", payload.comentario),
            ("metadata_json", "STRING", json_dumps_safe(meta_cambio)),
        ])
        _run(_fmt_tables(Q.INSERT_EVENTO), cfg_ev_cambio)

    return {"ok": True, "id_gestion": id_gestion, "estado": payload.nuevo_estado}


@router.delete("/{id_gestion}")
def delete_gestion(
    id_gestion: str,
    user=Depends(require_roles("Admin", "Supervisor")),
):
    now_dt = datetime.utcnow()
    actor = user.get("email") or user.get("usuario") or ""
    rol = user.get("rol")

    cfg_del = qparams([
        ("id_gestion", "STRING", id_gestion),
        ("updated_at", "TIMESTAMP", now_dt),
        ("updated_by", "STRING", actor),
    ])
    _run(_fmt_tables(Q.DELETE_GESTION), cfg_del)

    cfg_ev = qparams([
        ("id_evento", "STRING", str(uuid4())),
        ("id_gestion", "STRING", id_gestion),
        ("fecha_evento", "TIMESTAMP", now_dt),
        ("usuario", "STRING", actor),
        ("rol_usuario", "STRING", rol),
        ("tipo_evento", "STRING", "ARCHIVO"),
        ("estado_anterior", "STRING", None),
        ("estado_nuevo", "STRING", None),
        ("campo_modificado", "STRING", "is_deleted"),
        ("valor_anterior", "STRING", "FALSE"),
        ("valor_nuevo", "STRING", "TRUE"),
        ("comentario", "STRING", "Borrado lógico desde UI"),
        ("metadata_json", "STRING", json_dumps_safe({})),
    ])
    _run(_fmt_tables(Q.INSERT_EVENTO), cfg_ev)

    return {"ok": True}
