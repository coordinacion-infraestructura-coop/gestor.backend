# Queries para el informe del Ministerio de Cooperativas y Mutuales.
# Todas usan la vista v_informe_cooperativas del dataset infra_gestion.
# Parámetros: @fecha_desde (DATE), @fecha_hasta (DATE), opcionalmente @tema (STRING).

from bq import fqtn
VIEW = fqtn("v_informe_cooperativas")

# ── Resumen general (KPIs) ────────────────────────────────────────────────────
# Retorna: total gestiones, totales por tema con desagregado de estados.
RESUMEN = f"""
SELECT
  tema_informe                                        AS tema,
  COUNT(*)                                            AS total,
  COUNTIF(estado = 'FINALIZADA')                      AS finalizadas,
  COUNTIF(estado NOT IN ('FINALIZADA', 'ARCHIVADO'))  AS en_curso,
  COUNTIF(estado = 'ARCHIVADO')                       AS archivadas,
  COUNTIF(urgencia = 'Alta')                          AS urgentes
FROM `{VIEW}`
WHERE
  fecha_ingreso BETWEEN @fecha_desde AND @fecha_hasta
GROUP BY tema
ORDER BY total DESC
"""

# ── Evolución mensual ─────────────────────────────────────────────────────────
# Retorna: mes (YYYY-MM), tema, cantidad de gestiones ingresadas ese mes.
# El parámetro @tema es opcional: si viene vacío ('') no filtra por tema.
TEMPORAL = f"""
SELECT
  FORMAT_DATE('%Y-%m', fecha_ingreso) AS mes,
  tema_informe                        AS tema,
  COUNT(*)                            AS total
FROM `{VIEW}`
WHERE
  fecha_ingreso BETWEEN @fecha_desde AND @fecha_hasta
  AND (@tema = '' OR tema_informe = @tema)
GROUP BY mes, tema
ORDER BY mes, tema
"""

# ── Gestiones por tema y departamento ────────────────────────────────────────
# Retorna: tema, departamento, total, finalizadas.
POR_DEPARTAMENTO = f"""
SELECT
  tema_informe                    AS tema,
  departamento,
  COUNT(*)                        AS total,
  COUNTIF(estado = 'FINALIZADA')  AS finalizadas
FROM `{VIEW}`
WHERE
  fecha_ingreso BETWEEN @fecha_desde AND @fecha_hasta
  AND (@tema = '' OR tema_informe = @tema)
GROUP BY tema, departamento
ORDER BY tema, total DESC
"""

# ── Puntos para el mapa ───────────────────────────────────────────────────────
# Retorna todos los puntos con lat/lon para renderizar en Leaflet.
# Cuando la gestión no tiene geo_id, lat/lon vienen NULL → el frontend los omite.
PUNTOS = f"""
SELECT
  id_gestion,
  tema_informe                                  AS tema,
  es_ministerio_cooperativas,
  estado,
  urgencia,
  departamento,
  localidad,
  fecha_ingreso,
  SUBSTR(detalle, 1, 160)                       AS detalle_corto,
  nro_expediente,
  lat,
  lon
FROM `{VIEW}`
WHERE
  fecha_ingreso BETWEEN @fecha_desde AND @fecha_hasta
  AND (@tema = '' OR tema_informe = @tema)
  AND lat IS NOT NULL
  AND lon IS NOT NULL
ORDER BY fecha_ingreso DESC
"""
