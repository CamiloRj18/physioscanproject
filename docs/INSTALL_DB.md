# Instalación de la Base de Datos — PhysioScan

## Prerrequisitos

- MySQL 8.x instalado y corriendo
- Cliente `mysql` disponible en PATH

## 1. Crear la base de datos y el usuario de la aplicación

Conéctate con un usuario que tenga privilegios de administración:

```bash
mysql -u root -p
```

```sql
-- Base de datos
CREATE DATABASE IF NOT EXISTS physioscan
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- Usuario de la app: solo DML (sin DROP / ALTER / GRANT)
CREATE USER 'physioscan_app'@'localhost' IDENTIFIED BY 'CAMBIA_ESTA_CONTRASENA';

GRANT SELECT, INSERT, UPDATE, DELETE
  ON physioscan.*
  TO 'physioscan_app'@'localhost';

FLUSH PRIVILEGES;
EXIT;
```

## 2. Aplicar el esquema (con usuario admin)

```bash
mysql -u root -p physioscan < database/01_schema.sql
mysql -u root -p physioscan < database/02_triggers.sql
mysql -u root -p physioscan < database/03_seed.sql
mysql -u root -p physioscan < database/04_vistas.sql
```

## 3. Verificar el trigger `trg_usuario_codigo`

```sql
USE physioscan;

-- Insertar usuario de prueba (id_rol=1 = administrador, del seed)
INSERT INTO usuario (primer_nombre, primer_apellido, email, id_rol)
VALUES ('Camilo', 'Ramirez', 'test@ejemplo.com', 1);

-- Debe devolver: codigo_usuario = '10001CR'
SELECT id_usuario, codigo_usuario FROM usuario WHERE email = 'test@ejemplo.com';

-- Limpiar fila de prueba
DELETE FROM usuario WHERE email = 'test@ejemplo.com';
```

## 4. Variables de entorno

Copia `.env.example` → `.env` y actualiza `DB_PASSWORD` con la contraseña
del usuario `physioscan_app`. El usuario `root` **no** va en `.env`.

## Notas de seguridad

- `physioscan_app` solo tiene DML: el esquema y los triggers se aplican con admin.
- La contraseña de la app va exclusivamente en `.env` (excluido de git).
- El usuario administrador inicial se crea con `flask crear-admin`, nunca con SQL en claro.
