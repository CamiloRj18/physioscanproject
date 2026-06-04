-- PhysioScan — Datos iniciales
-- Ejecutar DESPUÉS de 02_triggers.sql
-- SIN contraseñas en texto claro: el admin inicial se crea con `flask crear-admin`

USE physioscan;

-- ─── Roles ───────────────────────────────────────────────────────────────────
INSERT INTO rol (nombre, descripcion) VALUES
  ('administrador', 'Gestión total del sistema y reemisión de archivos de recuperación'),
  ('entrenador',    'Consulta de deportistas asignados y sus métricas'),
  ('deportista',    'Acceso a sus propias sesiones y métricas'),
  ('usuario',       'Cuenta básica. Puede completar perfil deportivo desde su panel.');

-- ─── Tipos de sensor ─────────────────────────────────────────────────────────
INSERT INTO tipo_sensor (codigo, nombre, unidad, descripcion) VALUES
  ('ECG', 'Electrocardiograma / frecuencia cardíaca', 'mV/bpm',     'AD8232 - señal analógica de pulso'),
  ('GPS', 'Posicionamiento global',                   'grados/km-h','NEO-7M - latitud, longitud, velocidad'),
  ('IMU', 'Unidad de medición inercial',              'g/°/s',      'MPU-6050 - acelerómetro y giroscopio');

-- ─── Umbrales heurísticos globales (ajustables por deportista en runtime) ────
INSERT INTO umbral_heuristico (id_deportista, parametro, operador, valor, severidad, mensaje) VALUES
  (NULL, 'fc_porcentaje_max',    '>=', 90, 'rojo',     'Frecuencia cardíaca por encima del 90% de FCmáx: sobreesfuerzo'),
  (NULL, 'fc_porcentaje_max',    '>=', 80, 'amarillo', 'Frecuencia cardíaca alta (80-90% de FCmáx)'),
  (NULL, 'fc_recuperacion_bpm',  '<',  12, 'amarillo', 'Recuperación cardíaca lenta: posible fatiga'),
  (NULL, 'inclinacion_grados',   '>=', 45, 'rojo',     'Inclinación corporal extrema: posible caída');

-- ─── NOTA sobre el usuario administrador ─────────────────────────────────────
-- El admin inicial se siembra con el comando:  flask crear-admin
-- Ese comando pide email + contraseña, genera hash Argon2id, inserta en
-- usuario/credencial y genera el lote de recuperacion de 12 códigos.
-- NUNCA se guarda una contraseña en texto plano en este repositorio.
