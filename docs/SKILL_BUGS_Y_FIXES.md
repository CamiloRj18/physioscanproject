# PHYSIOSCAN — Skill de Bugs Conocidos y Fixes

## Bugs críticos ya resueltos

| Bug | Síntoma | Fix aplicado |
|---|---|---|
| BuildError import | ImportError: cannot import name 'BuildError' from 'flask' | `from werkzeug.routing.exceptions import BuildError` |
| Cotejamiento MySQL | ERROR 1273 Unknown collation utf8mb4_0900_ai_ci | Usar `utf8mb4_general_ci` en todo el schema |
| form.hidden_tag() | jinja2.UndefinedError: 'form' is undefined | El proyecto NO usa WTForms. Usar `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` |
| dict object has no attribute | 'dict object' has no attribute 'primer_nombre' | MySQL retorna dicts. Usar `deportista['primer_nombre']` no `deportista.primer_nombre` |
| Rol usuario no configurado | Error al registrar nuevo usuario | `INSERT IGNORE INTO rol (id_rol, nombre, descripcion) VALUES (4, 'usuario', 'Cuenta básica');` |
| Three.js CSP | Applying inline style violates CSP | `style-src 'self' 'unsafe-hashes'` en __init__.py |
| PowerShell && | && no funciona en PowerShell | Usar `;` para separar comandos o comandos separados |
| venv activate falla | No se puede cargar el archivo Scripts\Activate.ps1 | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Login redirige a home | _destino_post_login() falla silenciosamente | Envolver url_for en try/except BuildError |
| CapsuleGeometry | TypeError: THREE.CapsuleGeometry is not a constructor | NUNCA usar CapsuleGeometry en r128. Usar CylinderGeometry + SphereGeometry |

## Bugs pendientes de verificar

| Bug | Síntoma | Fix pendiente |
|---|---|---|
| PDF códigos recuperación | Admin ve los códigos, usuario no los recibe | Prompt enviado a Claude Code: generar PDF tema claro, enviarlo por correo al usuario |
| /deportista/sesiones 500 | 'dict object' has no attribute 'primer_nombre' | Codex aplicó fix parcial, verificar que quedó completo |
| Toggle dark/light | Puede mostrar 2 íconos | Verificar clases th-sun/th-moon en navbar.html |

## Reglas que NUNCA se rompen

```
1. CSP: style-src 'self' 'unsafe-hashes'  →  cero style="" en HTML
2. CSP: script-src 'self'                 →  cero CDN, todo autohospedado
3. Cero emojis como íconos                →  solo SVG inline o <use> del sprite
4. Templates MySQL: usar dict['campo']    →  nunca objeto.campo
5. CSRF: usar csrf_token()                →  nunca form.hidden_tag()
6. Three.js r128: NUNCA CapsuleGeometry   →  usar CylinderGeometry + SphereGeometry
7. SERVER_URL firmware: IP LAN del PC     →  nunca 127.0.0.1
8. Cotejamiento BD: utf8mb4_general_ci    →  nunca utf8mb4_0900_ai_ci
```

## Comandos de diagnóstico rápido

```powershell
# Verificar que la app arranca
.\venv\Scripts\python.exe -c "from app import create_app; app = create_app(); print('OK', len(list(app.url_map.iter_rules())), 'rutas')"

# Diagnóstico de rutas
.\venv\Scripts\python.exe -c "
from app import create_app
app = create_app()
with app.test_client() as c:
    for r in ['/', '/auth/login', '/auth/registro', '/admin/',
              '/admin/usuarios', '/usuario/perfil', '/deportista/sesiones',
              '/entrenador/deportistas', '/recuperacion/solicitar']:
        resp = c.get(r, follow_redirects=False)
        print(r, '->', resp.status_code)
"

# Pruebas (deben ser 48/48 verde)
.\venv\Scripts\python.exe -m pytest tests/ -q

# Auditoría de seguridad
.\venv\Scripts\python.exe -m pip_audit

# Buscar inline styles en templates (deben ser 0)
grep -rn 'style=' app/templates/

# Buscar emojis en el proyecto
grep -rn "emoji" app/templates/ app/static/css/
```

## Verificar rol 4 en BD

```python
# Ejecutar si hay error "Rol 'usuario' no configurado"
from config import ConfigDesarrollo as Config
import mysql.connector
cnx = mysql.connector.connect(
    host=Config.DB_HOST, port=Config.DB_PORT,
    database=Config.DB_NAME, user=Config.DB_USER, password=Config.DB_PASSWORD)
cur = cnx.cursor()
cur.execute("INSERT IGNORE INTO rol (id_rol, nombre, descripcion) VALUES (4, 'usuario', 'Cuenta básica')")
cnx.commit()
cur.execute("SELECT * FROM rol")
for row in cur.fetchall(): print(row)
```
