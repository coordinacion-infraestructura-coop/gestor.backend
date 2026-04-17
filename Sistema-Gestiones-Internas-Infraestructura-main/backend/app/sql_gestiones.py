# app/sql_gestiones.py
# Queries BigQuery (parameterized)

# -------------------------
# GESTIONES
# -------------------------

COUNT_GESTIONES = """
SELECT COUNT(1) AS total
FROM `{gestiones}`
WHERE is_deleted = FALSE
  AND (@estado IS NULL OR @estado = '' OR estado = @estado)
  AND (@ministerio IS NULL OR @ministerio = '' OR ministerio_agencia_id = @ministerio)
  AND (@categoria IS NULL OR @categoria = '' OR categoria_general_id = @categoria)
  AND (@departamento IS NULL OR @departamento = '' OR UPPER(TRIM(departamento)) = UPPER(TRIM(@departamento)))
  AND (@localidad IS NULL OR @localidad = '' OR UPPER(TRIM(localidad)) = UPPER(TRIM(@localidad)))

  -- ✅ NUEVOS (filtros opcionales)
  AND (@tipo_gestion IS NULL OR @tipo_gestion = '' OR tipo_gestion = @tipo_gestion)
  AND (@canal_origen IS NULL OR @canal_origen = '' OR canal_origen = @canal_origen)

  AND (
    @q IS NULL OR @q = '' OR (
      CONTAINS_SUBSTR(LOWER(CAST(id_gestion AS STRING)), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(departamento, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(localidad, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(estado, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(urgencia, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(detalle, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(subtipo_detalle, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(nro_expediente, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(CAST(COALESCE(costo_estimado, 0) AS STRING)), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(costo_moneda, '')), LOWER(@q)) OR

      -- ✅ NUEVOS CAMPOS incluidos en búsqueda
      CONTAINS_SUBSTR(LOWER(COALESCE(tipo_gestion, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(canal_origen, '')), LOWER(@q))
    )
  )
"""

LIST_GESTIONES = """
SELECT
  id_gestion,
  departamento,
  localidad,
  estado,
  urgencia,
  ministerio_agencia_id,
  categoria_general_id,

  -- ✅ NUEVOS
  tipo_gestion,
  canal_origen,

  detalle,
  costo_estimado,
  costo_moneda,
  nro_expediente,
  fecha_ingreso,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), fecha_estado, DAY) AS dias_transcurridos
FROM `{gestiones}`
WHERE is_deleted = FALSE
  AND (@estado IS NULL OR @estado = '' OR estado = @estado)
  AND (@ministerio IS NULL OR @ministerio = '' OR ministerio_agencia_id = @ministerio)
  AND (@categoria IS NULL OR @categoria = '' OR categoria_general_id = @categoria)
  AND (@departamento IS NULL OR @departamento = '' OR UPPER(TRIM(departamento)) = UPPER(TRIM(@departamento)))
  AND (@localidad IS NULL OR @localidad = '' OR UPPER(TRIM(localidad)) = UPPER(TRIM(@localidad)))

  -- ✅ NUEVOS (filtros opcionales)
  AND (@tipo_gestion IS NULL OR @tipo_gestion = '' OR tipo_gestion = @tipo_gestion)
  AND (@canal_origen IS NULL OR @canal_origen = '' OR canal_origen = @canal_origen)

  AND (
    @q IS NULL OR @q = '' OR (
      CONTAINS_SUBSTR(LOWER(CAST(id_gestion AS STRING)), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(departamento, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(localidad, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(estado, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(urgencia, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(detalle, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(subtipo_detalle, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(nro_expediente, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(CAST(COALESCE(costo_estimado, 0) AS STRING)), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(costo_moneda, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(tipo_gestion, '')), LOWER(@q)) OR
      CONTAINS_SUBSTR(LOWER(COALESCE(canal_origen, '')), LOWER(@q))
    )
  )
ORDER BY fecha_ingreso DESC, fecha_estado DESC
LIMIT @limit OFFSET @offset
"""

GET_GESTION = """
SELECT
  id_gestion,
  nro_expediente,
  origen,

  estado,
  fecha_ingreso,
  fecha_estado,
  fecha_finalizacion,

  urgencia,

  ministerio_agencia_id,
  organismo_id,
  derivado_a_id,

  categoria_general_id,
  subcategoria_id,
  tipo_demanda_principal_id,
  subtipo_detalle,

  detalle,
  observaciones,

  geo_id,
  departamento,
  localidad,
  direccion,
  lat,
  lon,

  costo_estimado,
  costo_moneda,

  created_at,
  created_by,
  updated_at,
  updated_by,

  is_deleted,

  -- ✅ NUEVOS
  tipo_gestion,
  canal_origen
FROM `{gestiones}`
WHERE id_gestion = @id_gestion
  AND is_deleted = FALSE
LIMIT 1
"""

LIST_EVENTOS = """
SELECT
  id_evento,
  id_gestion,
  fecha_evento,
  usuario,
  rol_usuario,
  tipo_evento,
  estado_anterior,
  estado_nuevo,
  campo_modificado,
  valor_anterior,
  valor_nuevo,
  comentario,
  metadata_json
FROM `{eventos}`
WHERE id_gestion = @id_gestion
ORDER BY fecha_evento DESC
"""

GET_GEO = """
SELECT
  id_geo,
  departamento,
  localidad,
  lat_centro AS lat,
  lon_centro AS lon
FROM `{geo_localidades}`
WHERE activo = TRUE
  AND UPPER(TRIM(departamento)) = UPPER(TRIM(@departamento))
  AND UPPER(TRIM(localidad)) = UPPER(TRIM(@localidad))
LIMIT 1
"""

INSERT_GESTION = """
INSERT INTO `{gestiones}` (
  id_gestion,
  nro_expediente,
  origen,

  estado,
  fecha_ingreso,
  fecha_estado,
  fecha_finalizacion,

  urgencia,

  ministerio_agencia_id,
  organismo_id,
  derivado_a_id,

  categoria_general_id,
  subcategoria_id,
  tipo_demanda_principal_id,
  subtipo_detalle,

  detalle,
  observaciones,

  geo_id,
  departamento,
  localidad,
  direccion,
  lat,
  lon,

  costo_estimado,
  costo_moneda,

  created_at,
  created_by,
  updated_at,
  updated_by,

  is_deleted,

  -- ✅ NUEVOS
  tipo_gestion,
  canal_origen
)
VALUES (
  @id_gestion,
  @nro_expediente,
  @origen,

  @estado,
  @fecha_ingreso,
  @fecha_estado,
  @fecha_finalizacion,

  @urgencia,

  @ministerio_agencia_id,
  @organismo_id,
  @derivado_a_id,

  @categoria_general_id,
  @subcategoria_id,
  @tipo_demanda_principal_id,
  @subtipo_detalle,

  @detalle,
  @observaciones,

  @geo_id,
  @departamento,
  @localidad,
  @direccion,
  @lat,
  @lon,

  @costo_estimado,
  @costo_moneda,

  @created_at,
  @created_by,
  @updated_at,
  @updated_by,

  FALSE,

  -- ✅ NUEVOS
  @tipo_gestion,
  @canal_origen
)
"""

UPDATE_ESTADO_GESTION = """
UPDATE `{gestiones}`
SET
  estado = @nuevo_estado,
  fecha_estado = @fecha_estado,
  derivado_a_id = @derivado_a_id,
  nro_expediente = @nro_expediente,
  fecha_ingreso = @fecha_ingreso,
  departamento = @departamento,
  localidad = @localidad,
  updated_at = @updated_at,
  updated_by = @updated_by
WHERE id_gestion = @id_gestion
  AND fecha_ingreso = @old_fecha_ingreso
  AND is_deleted = FALSE
"""

DELETE_GESTION = """
UPDATE `{gestiones}`
SET
  is_deleted = TRUE,
  updated_at = @updated_at,
  updated_by = @updated_by
WHERE id_gestion = @id_gestion
  AND is_deleted = FALSE
"""

INSERT_EVENTO = """
INSERT INTO `{eventos}` (
  id_evento,
  id_gestion,
  fecha_evento,

  usuario,
  rol_usuario,

  tipo_evento,

  estado_anterior,
  estado_nuevo,

  campo_modificado,
  valor_anterior,
  valor_nuevo,

  comentario,
  metadata_json
)
VALUES (
  @id_evento,
  @id_gestion,
  @fecha_evento,

  @usuario,
  @rol_usuario,

  @tipo_evento,

  @estado_anterior,
  @estado_nuevo,

  @campo_modificado,
  @valor_anterior,
  @valor_nuevo,

  @comentario,
  PARSE_JSON(@metadata_json)
)
"""


GET_LOCALIDAD_INFO = """
SELECT
  departamento,
  localidad,
  habitantes,
  electores,
  intendente_jefe_comunal,
  partido_politico,
  tipo_localidad,
  color_semaforo,
  updated_at,
  updated_by
FROM `{localidades_info}`
WHERE UPPER(TRIM(departamento)) = UPPER(TRIM(@departamento))
  AND UPPER(TRIM(localidad)) = UPPER(TRIM(@localidad))
LIMIT 1
"""


GET_DEPARTAMENTO_INFO = """
SELECT
  departamento,
  habitantes,
  electores,
  legislador_departamental,
  partido_politico,
  legislador_sabana1,
  partido_politico_sabana1,
  legislador_sabana2,
  partido_politico_sabana2,
  updated_at,
  updated_by
FROM `{departamentos_info}`
WHERE UPPER(TRIM(departamento)) = UPPER(TRIM(@departamento))
LIMIT 1
"""


UPSERT_LOCALIDAD_INFO = """
MERGE `{localidades_info}` AS target
USING (
  SELECT
    @departamento AS departamento,
    @localidad AS localidad,
    @habitantes AS habitantes,
    @electores AS electores,
    @intendente_jefe_comunal AS intendente_jefe_comunal,
    @partido_politico AS partido_politico,
    @updated_at AS updated_at,
    @updated_by AS updated_by
) AS source
ON UPPER(TRIM(target.departamento)) = UPPER(TRIM(source.departamento))
AND UPPER(TRIM(target.localidad)) = UPPER(TRIM(source.localidad))
WHEN MATCHED THEN
  UPDATE SET
    habitantes = source.habitantes,
    electores = source.electores,
    intendente_jefe_comunal = source.intendente_jefe_comunal,
    partido_politico = source.partido_politico,
    updated_at = source.updated_at,
    updated_by = source.updated_by
WHEN NOT MATCHED THEN
  INSERT (
    departamento,
    localidad,
    habitantes,
    electores,
    intendente_jefe_comunal,
    partido_politico,
    updated_at,
    updated_by
  )
  VALUES (
    source.departamento,
    source.localidad,
    source.habitantes,
    source.electores,
    source.intendente_jefe_comunal,
    source.partido_politico,
    source.updated_at,
    source.updated_by
  )
"""


LIST_GESTIONES_RESUMEN_TERRITORIAL = """
SELECT
  id_gestion,
  estado,
  urgencia,
  ministerio_agencia_id,
  categoria_general_id,
  tipo_gestion,
  canal_origen,
  detalle,
  subtipo_detalle,
  observaciones,
  nro_expediente,
  fecha_ingreso,
  fecha_estado,
  costo_estimado,
  costo_moneda,
  direccion,
  departamento,
  localidad
FROM `{gestiones}`
WHERE is_deleted = FALSE
  AND UPPER(TRIM(departamento)) = UPPER(TRIM(@departamento))
  AND UPPER(TRIM(localidad)) = UPPER(TRIM(@localidad))
"""


LIST_GESTIONES_RESUMEN_DEPARTAMENTO = """
SELECT
  id_gestion,
  estado,
  urgencia,
  ministerio_agencia_id,
  categoria_general_id,
  tipo_gestion,
  canal_origen,
  detalle,
  subtipo_detalle,
  observaciones,
  nro_expediente,
  fecha_ingreso,
  fecha_estado,
  costo_estimado,
  costo_moneda,
  direccion,
  departamento,
  localidad
FROM `{gestiones}`
WHERE is_deleted = FALSE
  AND UPPER(TRIM(departamento)) = UPPER(TRIM(@departamento))
"""


LIST_EVENTOS_RESUMEN_TERRITORIAL = """
SELECT
  e.id_evento,
  e.id_gestion,
  e.fecha_evento,
  e.usuario,
  e.rol_usuario,
  e.tipo_evento,
  e.estado_anterior,
  e.estado_nuevo,
  e.campo_modificado,
  e.valor_anterior,
  e.valor_nuevo,
  e.comentario,
  e.metadata_json
FROM `{eventos}` e
JOIN `{gestiones}` g
  ON e.id_gestion = g.id_gestion
WHERE g.is_deleted = FALSE
  AND UPPER(TRIM(g.departamento)) = UPPER(TRIM(@departamento))
  AND UPPER(TRIM(g.localidad)) = UPPER(TRIM(@localidad))
ORDER BY e.fecha_evento DESC
"""


LIST_EVENTOS_RESUMEN_DEPARTAMENTO = """
SELECT
  e.id_evento,
  e.id_gestion,
  e.fecha_evento,
  e.usuario,
  e.rol_usuario,
  e.tipo_evento,
  e.estado_anterior,
  e.estado_nuevo,
  e.campo_modificado,
  e.valor_anterior,
  e.valor_nuevo,
  e.comentario,
  e.metadata_json
FROM `{eventos}` e
JOIN `{gestiones}` g
  ON e.id_gestion = g.id_gestion
WHERE g.is_deleted = FALSE
  AND UPPER(TRIM(g.departamento)) = UPPER(TRIM(@departamento))
ORDER BY e.fecha_evento DESC
"""
