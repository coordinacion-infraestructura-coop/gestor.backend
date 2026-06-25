-- ============================================================
-- FASE 1 — Infraestructura de Módulos
-- Ejecutar en BigQuery Console (proyecto: essential-haiku-482815-u4)
-- ============================================================

-- Catálogo de módulos disponibles en el sistema
CREATE TABLE IF NOT EXISTS `infra_gestion.cat_modulos` (
  id          STRING NOT NULL,
  nombre      STRING NOT NULL,
  descripcion STRING,
  activo      BOOL DEFAULT TRUE,
  orden       INT64
);

-- Permisos de usuario por módulo
CREATE TABLE IF NOT EXISTS `infra_gestion.usuario_modulos` (
  email       STRING NOT NULL,
  modulo      STRING NOT NULL,
  rol_modulo  STRING NOT NULL,
  activo      BOOL DEFAULT TRUE,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by  STRING
);

-- Datos iniciales: módulo Cordón Cuneta
INSERT INTO `infra_gestion.cat_modulos` (id, nombre, descripcion, activo, orden)
VALUES
  ('cordon_cuneta', 'Cordón Cuneta', 'Programa de financiamiento para obras de cordón cuneta y adoquinado', TRUE, 1);

-- Para habilitar un módulo a un usuario (reemplazar email):
-- INSERT INTO `infra_gestion.usuario_modulos` (email, modulo, rol_modulo, activo, created_at, created_by)
-- VALUES ('usuario@dominio.com', 'cordon_cuneta', 'Operador', TRUE, CURRENT_TIMESTAMP(), 'admin@dominio.com');
