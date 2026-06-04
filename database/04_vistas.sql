-- PhysioScan — Vistas de reporte
-- Ejecutar DESPUÉS de 03_seed.sql

USE physioscan;

-- ─── Vista principal: resumen de sesión con métricas y datos del deportista ──
CREATE OR REPLACE VIEW v_resumen_sesion AS
SELECT
    s.id_sesion,
    s.titulo,
    s.inicio,
    s.fin,
    s.estado                                        AS estado_sesion,
    TIMESTAMPDIFF(SECOND, s.inicio, s.fin)          AS duracion_seg_calculada,
    d.id_deportista,
    u.codigo_usuario,
    CONCAT(u.primer_nombre, ' ', u.primer_apellido) AS nombre_deportista,
    d.deporte,
    d.categoria,
    d.fc_max_estimada,
    -- Métricas agregadas (caché en metrica_sesion, fuente de verdad = lectura_*)
    m.fc_promedio,
    m.fc_maxima,
    m.fc_minima,
    m.distancia_total_m,
    m.velocidad_max_kmh,
    m.velocidad_prom_kmh,
    m.duracion_seg,
    m.inclinacion_max,
    m.calorias_estimadas,
    m.recalculado_en
FROM sesion_entrenamiento   s
JOIN deportista              d ON s.id_deportista = d.id_deportista
LEFT JOIN usuario            u ON d.id_usuario    = u.id_usuario
LEFT JOIN metrica_sesion     m ON s.id_sesion      = m.id_sesion;
