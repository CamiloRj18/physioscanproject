# Instalación de la Base de Datos — PhysioScan

## Prerrequisitos

- **XAMPP** instalado y corriendo con el módulo **MySQL activo** en el puerto 3306.
- Python 3.9+ con las dependencias del proyecto instaladas:
  ```bash
  pip install -r requirements.txt
  ```
- Archivo `.env` en la raíz del proyecto (copia `.env.example → .env`):
  ```
  DB_HOST=localhost
  DB_PORT=3306
  DB_ROOT_PASSWORD=          # vacío por defecto en XAMPP; pon tu contraseña si la cambiaste
  ```

## 1. Crear la base de datos (script automático)

```bash
python scripts/crear_bd.py
```

El script se conecta como `root`, ejecuta en orden los 4 scripts SQL y
muestra `OK: database/0N_*.sql` al terminar cada uno. Salida esperada:

```
OK: database/01_schema.sql
OK: database/02_triggers.sql
OK: database/03_seed.sql
OK: database/04_vistas.sql

✓ Base de datos physioscan creada correctamente.
  Siguiente paso: crear el usuario app (ver docs/INSTALL_DB.md).
```

> **Si la BD ya existe:** abre phpMyAdmin → selecciona `physioscan` → Operaciones → Eliminar BD, y vuelve a ejecutar el script.

## 2. Crear el usuario de la aplicación (solo DML)

El usuario `physioscan_app` solo recibe SELECT, INSERT, UPDATE, DELETE —
sin DROP, ALTER ni GRANT. Ejecuta en la terminal (o en phpMyAdmin → SQL):

```bash
mysql -u root -p -e "
  CREATE USER 'physioscan_app'@'localhost' IDENTIFIED BY 'TU_PASSWORD_APP';
  GRANT SELECT, INSERT, UPDATE, DELETE
    ON physioscan.*
    TO 'physioscan_app'@'localhost';
  FLUSH PRIVILEGES;
"
```

Luego actualiza `DB_USER=physioscan_app` y `DB_PASSWORD=TU_PASSWORD_APP` en `.env`.

## 3. Verificar el trigger `trg_usuario_codigo`

En phpMyAdmin → SQL (seleccionando la BD `physioscan`):

```sql
-- Insertar usuario de prueba (id_rol=1 = administrador, del seed)
INSERT INTO usuario (primer_nombre, primer_apellido, email, id_rol)
VALUES ('Camilo', 'Ramirez', 'test@ejemplo.com', 1);

-- Debe devolver: codigo_usuario = '10001CR'
SELECT id_usuario, codigo_usuario FROM usuario WHERE email = 'test@ejemplo.com';

-- Limpiar fila de prueba
DELETE FROM usuario WHERE email = 'test@ejemplo.com';
```

## Notas

- El cotejamiento usado es `utf8mb4_general_ci` (compatible con MySQL 5.7+/XAMPP).
- Los `CHECK` constraints se analizan pero no se aplican en MySQL 5.7 (comportamiento esperado).
- `physioscan_app` solo tiene DML; los triggers y el esquema se aplican con el script de root.
- El usuario administrador inicial se crea con `flask crear-admin` (nunca contraseñas en SQL).
