# Refactor XP — PhysioScan

Metodología XP exige refactorizar continuamente: código limpio, sin duplicación, responsabilidades claras.

---

## 1. Violaciones de arquitectura detectadas

### 1.1 Controladores que importan repositorios directamente

La regla es: **Presentación → Negocio → Datos**. Los controladores solo pueden llamar a servicios; los repositorios son exclusivos de la capa de datos.

| Controlador | Repos importados | Impacto |
|---|---|---|
| `auth_controlador.py` | `seguridad_repositorio`, `usuario_repositorio` | Lógica de sesión servidor mezclada con HTTP |
| `admin_controlador.py` | `deportista_repositorio`, `dispositivo_repositorio`, `seguridad_repositorio`, `usuario_repositorio` | CRUD de entidades sin pasar por servicios |
| `deportista_controlador.py` | `alerta_repositorio`, `deportista_repositorio`, `sesion_repositorio` | Consultas de datos sin lógica de negocio encapsulada |
| `entrenador_controlador.py` | `alerta_repositorio`, `deportista_repositorio`, `sesion_repositorio` | Ídem |
| `usuario_controlador.py` | `deportista_repositorio` | Acceso directo a perfil deportivo |
| `api_ingesta_controlador.py` | `deportista_repositorio`, `alerta_repositorio`, `lectura_repositorio`, `sesion_repositorio` (lazy) | Consultas de tiempo real sin servicio intermediario |

### 1.2 Plan de corrección (próxima iteración XP)

Para cada controlador afectado:

1. Crear o extender el servicio correspondiente con el método que encapsula la consulta.
   - `deportista_servicio.obtener_dashboard(id_deportista)` → encapsula joins de sesiones + alertas
   - `entrenador_servicio.listar_deportistas_con_semaforo(id_entrenador)` → encapsula las 3 queries
   - `admin_servicio.obtener_panel(...)` → delega a repos internamente
   - `ingesta_servicio.obtener_tiempo_real(id_sesion, id_usuario)` → encapsula auth + lecturas + alertas
2. El controlador solo recibe `request` → llama al servicio → renderiza template o devuelve JSON.
3. Eliminar los imports `from app.datos` de `app/presentacion`.

### 1.3 Severidad actual

- **No es un bug funcional**: la app opera correctamente.
- **Sí es deuda técnica**: dificulta tests unitarios de controladores y viola el principio de separación de capas.
- **Prioridad**: media. Resolver en sprint 2 antes de agregar más endpoints.

---

## 2. Verificación de invariantes por capa

### Capa de negocio: sin imports de Flask ni mysql.connector

```
grep -r "from flask\|import flask\|mysql.connector" app/negocio/
```

Resultado esperado: **0 coincidencias**. Verificado: ningún servicio importa Flask ni mysql.connector.

### Capa de datos: sin lógica de negocio

Los repositorios solo contienen:
- `ejecutar()`, `uno()`, `muchos()`, `tx()` del `base_repositorio`
- SQL parametrizado con `%s` (nunca concatenación de strings)
- Mapeo fila → dict

No contienen: validaciones de negocio, reglas de contraseña, decisiones de flujo.

### Capa de presentación: sin SQL

```
grep -r "SELECT\|INSERT\|UPDATE\|DELETE" app/presentacion/
```

Resultado esperado: **0 coincidencias**. Verificado: ningún controlador tiene SQL inline.

---

## 3. Funciones duplicadas / candidatas a extracción

| Patrón | Ubicación | Acción |
|---|---|---|
| `datetime.utcnow().strftime(...)` | `ingesta_servicio`, `recuperacion_archivo_servicio`, `heuristica_servicio` | Extraer helper `_ts_utc()` en `comun/utils.py` en próxima iteración |
| `"".join(secrets.choice(_ALFABETO) for _ in range(4))` repetido | `auth_servicio._generar_codigos`, `recuperacion_archivo_servicio._generar_codigo` | Consolidar en `comun/seguridad_utils.py` |
| Bloque `try: from app.datos import X` | `heuristica_servicio`, `ingesta_servicio` | Mover al nivel de módulo (ahora son lazy para evitar import circular) — documentar el motivo |

---

## 4. Checklist de nombres y funciones cortas

- [x] Funciones de servicio ≤ 30 líneas (salvo `autenticar` que gestiona múltiples estados de cuenta)
- [x] Nombres en español consistentes: `registrar`, `verificar`, `autenticar`, `revocar`
- [x] Sin abreviaturas crípticas en nombres públicos
- [x] `_private` con underscore para helpers internos
- [x] Repositorios con verbo_sustantivo: `buscar_por_email`, `crear_completo`, `marcar_token_usado`
