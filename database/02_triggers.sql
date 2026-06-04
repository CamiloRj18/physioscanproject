-- PhysioScan — Triggers: codigos de negocio + auditoría de estado
-- Ejecutar DESPUÉS de 01_schema.sql con usuario admin

USE physioscan;

-- ─── Semillas de secuencia ───────────────────────────────────────────────────
-- usuario: arranca en 10000 → primer código = 10001XX
INSERT INTO secuencia_codigo (nombre_secuencia, valor_actual)
VALUES ('usuario', 10000)
ON DUPLICATE KEY UPDATE valor_actual = valor_actual;

-- dispositivo: arranca en 0 → primer código = CHAL0001
INSERT INTO secuencia_codigo (nombre_secuencia, valor_actual)
VALUES ('dispositivo', 0)
ON DUPLICATE KEY UPDATE valor_actual = valor_actual;

DELIMITER //

-- ─── Trigger: codigo_usuario ─────────────────────────────────────────────────
-- Produce CHAR(7): 5 dígitos + inicial primer_nombre + inicial primer_apellido
-- Ejemplo: Camilo Ramírez → 10001CR
CREATE TRIGGER trg_usuario_codigo
BEFORE INSERT ON usuario
FOR EACH ROW
BEGIN
  DECLARE v_seq        INT UNSIGNED;
  DECLARE v_ini_nombre   CHAR(1);
  DECLARE v_ini_apellido CHAR(1);

  -- Incremento atómico seguro ante concurrencia con LAST_INSERT_ID
  UPDATE secuencia_codigo
     SET valor_actual = LAST_INSERT_ID(valor_actual + 1)
   WHERE nombre_secuencia = 'usuario';
  SET v_seq = LAST_INSERT_ID();

  SET v_ini_nombre   = UPPER(LEFT(TRIM(NEW.primer_nombre),   1));
  SET v_ini_apellido = UPPER(LEFT(TRIM(NEW.primer_apellido), 1));

  -- LPAD garantiza exactamente 5 dígitos; resultado total: 7 caracteres
  SET NEW.codigo_usuario = CONCAT(LPAD(v_seq, 5, '0'), v_ini_nombre, v_ini_apellido);
END//

-- ─── Trigger: auditoria de cambios de estado de cuenta ───────────────────────
CREATE TRIGGER trg_usuario_auditoria_estado
AFTER UPDATE ON usuario
FOR EACH ROW
BEGIN
  IF NEW.estado <> OLD.estado THEN
    INSERT INTO auditoria (id_usuario, accion, entidad, id_entidad, detalle)
    VALUES (
      NEW.id_usuario,
      'CAMBIO_ESTADO',
      'usuario',
      NEW.id_usuario,
      JSON_OBJECT('anterior', OLD.estado, 'nuevo', NEW.estado)
    );
  END IF;
END//

-- ─── Trigger: codigo_dispositivo ─────────────────────────────────────────────
-- Mismo patrón que trg_usuario_codigo
-- Produce CHAR(8): 'CHAL' + 4 dígitos  → p.ej. CHAL0001
CREATE TRIGGER trg_dispositivo_codigo
BEFORE INSERT ON dispositivo
FOR EACH ROW
BEGIN
  DECLARE v_seq INT UNSIGNED;

  UPDATE secuencia_codigo
     SET valor_actual = LAST_INSERT_ID(valor_actual + 1)
   WHERE nombre_secuencia = 'dispositivo';
  SET v_seq = LAST_INSERT_ID();

  SET NEW.codigo_dispositivo = CONCAT('CHAL', LPAD(v_seq, 4, '0'));
END//

DELIMITER ;
