-- PhysioScan — DDL completo
-- MySQL 8.x, utf8mb4, InnoDB, FKs con ON UPDATE CASCADE
-- Ejecutar con usuario admin (no con physioscan_app)

CREATE DATABASE IF NOT EXISTS physioscan
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE physioscan;

-- ───────────────────────── Identidad y seguridad ─────────────────────────

CREATE TABLE rol (
  id_rol        TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nombre        VARCHAR(30)  NOT NULL UNIQUE,
  descripcion   VARCHAR(150) NULL
) ENGINE=InnoDB;

-- Soporte para triggers de codigos de negocio
CREATE TABLE secuencia_codigo (
  nombre_secuencia VARCHAR(50) PRIMARY KEY,
  valor_actual     INT UNSIGNED NOT NULL
) ENGINE=InnoDB;

CREATE TABLE usuario (
  id_usuario          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo_usuario      CHAR(7)      NULL UNIQUE,          -- 5 dígitos + 2 iniciales (trg_usuario_codigo)
  primer_nombre       VARCHAR(40)  NOT NULL,
  segundo_nombre      VARCHAR(40)  NULL,
  primer_apellido     VARCHAR(40)  NOT NULL,
  segundo_apellido    VARCHAR(40)  NULL,
  email               VARCHAR(120) NOT NULL UNIQUE,      -- almacenar en minúscula
  telefono            VARCHAR(20)  NULL,
  id_rol              TINYINT UNSIGNED NOT NULL,
  estado              ENUM('pendiente_verificacion','activo','inactivo','bloqueado')
                        NOT NULL DEFAULT 'pendiente_verificacion',
  email_verificado    BOOLEAN      NOT NULL DEFAULT FALSE,
  intentos_fallidos   TINYINT UNSIGNED NOT NULL DEFAULT 0,
  bloqueado_hasta     DATETIME     NULL,
  ultimo_acceso       DATETIME     NULL,
  fecha_creacion      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_actualizacion DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_usuario_rol FOREIGN KEY (id_rol)
    REFERENCES rol(id_rol) ON UPDATE CASCADE ON DELETE RESTRICT,
  INDEX idx_usuario_email  (email),
  INDEX idx_usuario_estado (estado)
) ENGINE=InnoDB;

CREATE TABLE credencial (                         -- 1:1 con usuario (aísla el secreto)
  id_usuario       INT UNSIGNED  PRIMARY KEY,
  hash_contrasena  VARCHAR(255)  NOT NULL,         -- Argon2id
  algoritmo        VARCHAR(20)   NOT NULL DEFAULT 'argon2id',
  fecha_cambio     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  requiere_cambio  BOOLEAN       NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_credencial_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE historial_contrasena (
  id_historial     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_usuario       INT UNSIGNED   NOT NULL,
  hash_contrasena  VARCHAR(255)   NOT NULL,
  creado_en        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_histpwd_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE CASCADE,
  INDEX idx_histpwd_usuario (id_usuario)
) ENGINE=InnoDB;

CREATE TABLE usuario_2fa (                         -- 1:1, opcional
  id_usuario       INT UNSIGNED  PRIMARY KEY,
  metodo           ENUM('totp','email') NOT NULL DEFAULT 'totp',
  secreto_totp     VARBINARY(255) NULL,             -- cifrado en reposo (Fernet)
  habilitado       BOOLEAN       NOT NULL DEFAULT FALSE,
  confirmado       BOOLEAN       NOT NULL DEFAULT FALSE,
  fecha_activacion DATETIME      NULL,
  CONSTRAINT fk_2fa_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE token_recuperacion (                  -- OTP de un solo uso por correo
  id_token     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_usuario   INT UNSIGNED    NOT NULL,
  token_hash   CHAR(64)        NOT NULL,            -- SHA-256 del token enviado
  tipo         ENUM('reset_password','verificacion_email','2fa_email') NOT NULL,
  expira_en    DATETIME        NOT NULL,
  usado        BOOLEAN         NOT NULL DEFAULT FALSE,
  usado_en     DATETIME        NULL,
  ip_solicitud VARCHAR(45)     NULL,
  creado_en    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_token_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE CASCADE,
  INDEX idx_token_hash            (token_hash),
  INDEX idx_token_usuario_tipo    (id_usuario, tipo, usado)
) ENGINE=InnoDB;

CREATE TABLE lote_recuperacion (                   -- "el archivo" de 12 códigos
  id_lote        BIGINT UNSIGNED  AUTO_INCREMENT PRIMARY KEY,
  id_usuario     INT UNSIGNED     NOT NULL,
  numero_lote    SMALLINT UNSIGNED NOT NULL DEFAULT 1,
  total_codigos  TINYINT UNSIGNED  NOT NULL DEFAULT 12,
  codigos_usados TINYINT UNSIGNED  NOT NULL DEFAULT 0,  -- caché contable
  activo         BOOLEAN           NOT NULL DEFAULT TRUE,
  generado_por   INT UNSIGNED      NULL,                 -- admin reemisor; NULL = registro propio
  generado_en    DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_lote_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_lote_admin FOREIGN KEY (generado_por)
    REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX idx_lote_usuario_activo (id_usuario, activo)
) ENGINE=InnoDB;

CREATE TABLE codigo_recuperacion_archivo (         -- los 12 códigos del lote
  id_codigo    BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_lote      BIGINT UNSIGNED  NOT NULL,
  orden        TINYINT UNSIGNED NOT NULL,           -- 1..12
  codigo_hash  VARCHAR(255)     NOT NULL,            -- Argon2id del código (mostrado una sola vez)
  usado        BOOLEAN          NOT NULL DEFAULT FALSE,
  usado_en     DATETIME         NULL,
  CONSTRAINT fk_codigo_lote FOREIGN KEY (id_lote)
    REFERENCES lote_recuperacion(id_lote) ON UPDATE CASCADE ON DELETE CASCADE,
  UNIQUE KEY uq_lote_orden (id_lote, orden)
) ENGINE=InnoDB;

CREATE TABLE sesion_usuario (                      -- sesiones de login lado servidor (revocables)
  id_sesion_usuario BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_usuario        INT UNSIGNED    NOT NULL,
  token_hash        CHAR(64)        NOT NULL,
  ip                VARCHAR(45)     NULL,
  user_agent        VARCHAR(255)    NULL,
  creado_en         DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expira_en         DATETIME        NOT NULL,
  revocado          BOOLEAN         NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_sesionu_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE CASCADE,
  INDEX idx_sesionu_token (token_hash)
) ENGINE=InnoDB;

CREATE TABLE intento_login (
  id_intento    BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  identificador VARCHAR(120)  NOT NULL,              -- email intentado (puede no existir)
  exito         BOOLEAN       NOT NULL,
  ip            VARCHAR(45)   NULL,
  user_agent    VARCHAR(255)  NULL,
  creado_en     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_intento_id_fecha (identificador, creado_en),
  INDEX idx_intento_ip_fecha (ip, creado_en)
) ENGINE=InnoDB;

CREATE TABLE auditoria (
  id_auditoria BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_usuario   INT UNSIGNED    NULL,
  accion       VARCHAR(60)     NOT NULL,   -- LOGIN_OK, 2FA_FAIL, PWD_RESET, LOTE_REEMITIDO...
  entidad      VARCHAR(40)     NULL,
  id_entidad   VARCHAR(40)     NULL,
  ip           VARCHAR(45)     NULL,
  user_agent   VARCHAR(255)    NULL,
  detalle      JSON            NULL,
  creado_en    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX idx_audit_usuario_fecha (id_usuario, creado_en),
  INDEX idx_audit_accion        (accion)
) ENGINE=InnoDB;

-- ───────────────────────── Dominio deportivo ─────────────────────────

CREATE TABLE deportista (                          -- subtipo 1:1 de usuario
  id_deportista    INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
  id_usuario       INT UNSIGNED    NULL UNIQUE,     -- NULL = atleta sin cuenta de login
  documento        VARCHAR(20)     NULL UNIQUE,
  fecha_nacimiento DATE            NULL,
  sexo             ENUM('M','F','O') NULL,
  altura_cm        SMALLINT UNSIGNED NULL,
  peso_kg          DECIMAL(5,2)    NULL,
  deporte          VARCHAR(50)     NULL,
  categoria        VARCHAR(40)     NULL,
  fc_max_estimada  SMALLINT UNSIGNED NULL,          -- 208 - 0.7*edad (regla)
  fc_reposo        SMALLINT UNSIGNED NULL,
  creado_en        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_deportista_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT chk_altura CHECK (altura_cm IS NULL OR altura_cm BETWEEN 80 AND 260),
  CONSTRAINT chk_peso   CHECK (peso_kg   IS NULL OR peso_kg   BETWEEN 20 AND 300)
) ENGINE=InnoDB;

CREATE TABLE asignacion_entrenador (               -- M:N entrenador(usuario) ↔ deportista
  id_asignacion    BIGINT UNSIGNED  AUTO_INCREMENT PRIMARY KEY,
  id_entrenador    INT UNSIGNED     NOT NULL,       -- usuario con rol entrenador
  id_deportista    INT UNSIGNED     NOT NULL,
  fecha_asignacion DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  activo           BOOLEAN          NOT NULL DEFAULT TRUE,
  CONSTRAINT fk_asig_entrenador FOREIGN KEY (id_entrenador)
    REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_asig_deportista FOREIGN KEY (id_deportista)
    REFERENCES deportista(id_deportista) ON UPDATE CASCADE ON DELETE CASCADE,
  UNIQUE KEY uq_entrenador_deportista (id_entrenador, id_deportista)
) ENGINE=InnoDB;

CREATE TABLE dispositivo (                         -- el chaleco / ESP32
  id_dispositivo     INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
  codigo_dispositivo CHAR(8)         NULL UNIQUE,   -- generado por trg_dispositivo_codigo (p.ej. CHAL0001)
  nombre             VARCHAR(60)     NOT NULL,
  mac                CHAR(17)        NULL UNIQUE,
  api_key_hash       VARCHAR(255)    NOT NULL,       -- Argon2id de la API key (mostrada una vez)
  id_deportista      INT UNSIGNED    NULL,
  firmware_version   VARCHAR(20)     NULL,
  estado             ENUM('activo','inactivo','mantenimiento') NOT NULL DEFAULT 'activo',
  creado_en          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_disp_deportista FOREIGN KEY (id_deportista)
    REFERENCES deportista(id_deportista) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE tipo_sensor (
  id_tipo_sensor TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo         VARCHAR(10)  NOT NULL UNIQUE,       -- ECG, GPS, IMU
  nombre         VARCHAR(50)  NOT NULL,
  unidad         VARCHAR(20)  NULL,
  descripcion    VARCHAR(150) NULL
) ENGINE=InnoDB;

CREATE TABLE sensor (
  id_sensor      INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
  id_dispositivo INT UNSIGNED    NOT NULL,
  id_tipo_sensor TINYINT UNSIGNED NOT NULL,
  modelo         VARCHAR(30)     NOT NULL,           -- NEO-7M / AD8232 / MPU-6050
  config_pines   VARCHAR(100)    NULL,               -- "OUTPUT=34, LO+=35, LO-=32"
  activo         BOOLEAN         NOT NULL DEFAULT TRUE,
  CONSTRAINT fk_sensor_disp FOREIGN KEY (id_dispositivo)
    REFERENCES dispositivo(id_dispositivo) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_sensor_tipo FOREIGN KEY (id_tipo_sensor)
    REFERENCES tipo_sensor(id_tipo_sensor) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE sesion_entrenamiento (
  id_sesion      BIGINT UNSIGNED  AUTO_INCREMENT PRIMARY KEY,
  id_deportista  INT UNSIGNED     NOT NULL,
  id_dispositivo INT UNSIGNED     NULL,
  titulo         VARCHAR(80)      NULL,
  notas          VARCHAR(255)     NULL,
  inicio         DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fin            DATETIME         NULL,
  estado         ENUM('en_curso','finalizada','descartada') NOT NULL DEFAULT 'en_curso',
  CONSTRAINT fk_sesion_deportista FOREIGN KEY (id_deportista)
    REFERENCES deportista(id_deportista) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_sesion_disp FOREIGN KEY (id_dispositivo)
    REFERENCES dispositivo(id_dispositivo) ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX idx_sesion_deportista (id_deportista, inicio)
) ENGINE=InnoDB;

CREATE TABLE lectura_ecg (
  id_lectura       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_sesion        BIGINT UNSIGNED NOT NULL,
  capturado_en     DATETIME(3)     NOT NULL,         -- precisión de milisegundos
  valor_adc        SMALLINT UNSIGNED NOT NULL,       -- 0..4095 del ADC del ESP32
  bpm              SMALLINT UNSIGNED NULL,           -- BPM calculado si aplica
  electrodo_suelto BOOLEAN         NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_ecg_sesion FOREIGN KEY (id_sesion)
    REFERENCES sesion_entrenamiento(id_sesion) ON UPDATE CASCADE ON DELETE CASCADE,
  INDEX idx_ecg_sesion_tiempo (id_sesion, capturado_en)
) ENGINE=InnoDB;

CREATE TABLE lectura_gps (
  id_lectura     BIGINT UNSIGNED  AUTO_INCREMENT PRIMARY KEY,
  id_sesion      BIGINT UNSIGNED  NOT NULL,
  capturado_en   DATETIME(3)      NOT NULL,
  latitud        DECIMAL(9,6)     NOT NULL,
  longitud       DECIMAL(9,6)     NOT NULL,
  velocidad_kmh  DECIMAL(5,2)     NULL,
  altitud_m      DECIMAL(6,2)     NULL,
  satelites      TINYINT UNSIGNED NULL,
  hdop           DECIMAL(4,2)     NULL,
  CONSTRAINT fk_gps_sesion FOREIGN KEY (id_sesion)
    REFERENCES sesion_entrenamiento(id_sesion) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT chk_lat CHECK (latitud  BETWEEN -90  AND  90),
  CONSTRAINT chk_lon CHECK (longitud BETWEEN -180 AND 180),
  INDEX idx_gps_sesion_tiempo (id_sesion, capturado_en)
) ENGINE=InnoDB;

CREATE TABLE lectura_imu (
  id_lectura         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_sesion          BIGINT UNSIGNED NOT NULL,
  capturado_en       DATETIME(3)     NOT NULL,
  accel_x            SMALLINT        NOT NULL,        -- crudo int16 MPU-6050
  accel_y            SMALLINT        NOT NULL,
  accel_z            SMALLINT        NOT NULL,
  gyro_x             SMALLINT        NOT NULL,
  gyro_y             SMALLINT        NOT NULL,
  gyro_z             SMALLINT        NOT NULL,
  inclinacion_grados DECIMAL(5,2)    NULL,             -- pitch calculado
  CONSTRAINT fk_imu_sesion FOREIGN KEY (id_sesion)
    REFERENCES sesion_entrenamiento(id_sesion) ON UPDATE CASCADE ON DELETE CASCADE,
  INDEX idx_imu_sesion_tiempo (id_sesion, capturado_en)
) ENGINE=InnoDB;

-- ───────────────────────── Derivadas / configuración ─────────────────────────

CREATE TABLE metrica_sesion (                      -- 1:1 con sesión (CACHÉ derivada, no fuente de verdad)
  id_sesion           BIGINT UNSIGNED  PRIMARY KEY,
  fc_promedio         SMALLINT UNSIGNED NULL,
  fc_maxima           SMALLINT UNSIGNED NULL,
  fc_minima           SMALLINT UNSIGNED NULL,
  distancia_total_m   DECIMAL(9,2)     NULL,
  velocidad_max_kmh   DECIMAL(5,2)     NULL,
  velocidad_prom_kmh  DECIMAL(5,2)     NULL,
  duracion_seg        INT UNSIGNED     NULL,
  inclinacion_max     DECIMAL(5,2)     NULL,
  calorias_estimadas  DECIMAL(7,2)     NULL,
  recalculado_en      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_metrica_sesion FOREIGN KEY (id_sesion)
    REFERENCES sesion_entrenamiento(id_sesion) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE umbral_heuristico (
  id_umbral     INT UNSIGNED   AUTO_INCREMENT PRIMARY KEY,
  id_deportista INT UNSIGNED   NULL,                 -- NULL = umbral global para todos
  parametro     VARCHAR(40)    NOT NULL,             -- fc_porcentaje_max, inclinacion_caida...
  operador      ENUM('>','>=','<','<=','==') NOT NULL,
  valor         DECIMAL(8,2)   NOT NULL,
  severidad     ENUM('verde','amarillo','rojo') NOT NULL,
  mensaje       VARCHAR(120)   NOT NULL,
  activo        BOOLEAN        NOT NULL DEFAULT TRUE,
  CONSTRAINT fk_umbral_deportista FOREIGN KEY (id_deportista)
    REFERENCES deportista(id_deportista) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE alerta (
  id_alerta        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_sesion        BIGINT UNSIGNED NOT NULL,
  tipo             ENUM('fatiga','sobreesfuerzo_cardiaco','caida_postura','electrodo_suelto') NOT NULL,
  severidad        ENUM('verde','amarillo','rojo') NOT NULL,
  mensaje          VARCHAR(160)    NOT NULL,
  valor_referencia DECIMAL(8,2)    NULL,
  capturado_en     DATETIME(3)     NOT NULL,
  reconocida       BOOLEAN         NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_alerta_sesion FOREIGN KEY (id_sesion)
    REFERENCES sesion_entrenamiento(id_sesion) ON UPDATE CASCADE ON DELETE CASCADE,
  INDEX idx_alerta_sesion (id_sesion, capturado_en)
) ENGINE=InnoDB;
