"""Comandos CLI de Flask para tareas de administración.

Registro:  create_app() llama a registrar_comandos(app).
Uso:       flask --app app crear-admin
"""
from __future__ import annotations

import secrets
import string
from datetime import datetime

import click
from flask.cli import with_appcontext


def registrar_comandos(app) -> None:
    app.cli.add_command(cmd_crear_admin)


# ── Comando crear-admin ──────────────────────────────────────────────────────

@click.command("crear-admin")
@click.option("--nombre",   prompt="Primer nombre",   help="Primer nombre del administrador.")
@click.option("--apellido", prompt="Primer apellido", help="Primer apellido del administrador.")
@click.option("--email",    prompt="Email",           help="Email de acceso.")
@click.option(
    "--password",
    prompt="Contraseña (mín. 12 caracteres, 1 mayúsc., 1 minúsc., 1 dígito)",
    hide_input=True,
    confirmation_prompt="Confirmar contraseña",
    help="Contraseña del administrador.",
)
@with_appcontext
def cmd_crear_admin(nombre: str, apellido: str, email: str, password: str) -> None:
    """Crea el usuario administrador inicial y su lote de 12 códigos de recuperación."""
    from app.comun.validadores import validar_email, validar_contrasena
    from app.comun.seguridad_utils import hash_password, hash_codigo
    from app.datos.base_repositorio import uno, transaccion

    email = email.strip().lower()
    nombre = nombre.strip()
    apellido = apellido.strip()

    # ── Validaciones ────────────────────────────────────────────────────────
    if not validar_email(email):
        raise click.ClickException("El email no tiene un formato válido.")

    error_pwd = validar_contrasena(password)
    if error_pwd:
        raise click.ClickException(error_pwd)

    # ── Verificar seed y duplicados ──────────────────────────────────────────
    try:
        rol = uno("SELECT id_rol FROM rol WHERE nombre = %s", ("administrador",))
    except Exception as exc:
        raise click.ClickException(
            f"No se pudo conectar a la BD: {exc}\n"
            "Ejecuta primero: python scripts/crear_bd.py"
        )

    if not rol:
        raise click.ClickException(
            "No existe el rol 'administrador'. Ejecuta: python scripts/crear_bd.py"
        )

    if uno("SELECT id_usuario FROM usuario WHERE email = %s", (email,)):
        raise click.ClickException(f"Ya existe un usuario con el email '{email}'.")

    id_rol = rol["id_rol"]

    # ── Hashes ──────────────────────────────────────────────────────────────
    click.echo("Generando hash de contraseña…")
    hash_pwd = hash_password(password)

    click.echo("Generando y hasheando 12 códigos de recuperación…")
    codigos_claro = [_codigo_recuperacion() for _ in range(12)]
    hashes = [hash_codigo(c) for c in codigos_claro]

    # ── Transacción ──────────────────────────────────────────────────────────
    id_usuario: int
    with transaccion() as (conn, cur):
        cur.execute(
            """
            INSERT INTO usuario
                (primer_nombre, primer_apellido, email, id_rol, estado, email_verificado)
            VALUES (%s, %s, %s, %s, 'activo', TRUE)
            """,
            (nombre, apellido, email, id_rol),
        )
        id_usuario = cur.lastrowid

        cur.execute(
            "INSERT INTO credencial (id_usuario, hash_contrasena) VALUES (%s, %s)",
            (id_usuario, hash_pwd),
        )

        cur.execute(
            """
            INSERT INTO lote_recuperacion (id_usuario, numero_lote, total_codigos, activo)
            VALUES (%s, 1, 12, TRUE)
            """,
            (id_usuario,),
        )
        id_lote = cur.lastrowid

        for orden, h in enumerate(hashes, 1):
            cur.execute(
                """
                INSERT INTO codigo_recuperacion_archivo (id_lote, orden, codigo_hash)
                VALUES (%s, %s, %s)
                """,
                (id_lote, orden, h),
            )

    # ── Obtener codigo_usuario generado por el trigger ───────────────────────
    fila = uno("SELECT codigo_usuario FROM usuario WHERE id_usuario = %s", (id_usuario,))
    codigo_usuario = fila["codigo_usuario"] if fila else "???????"

    # ── Imprimir el archivo UNA SOLA VEZ ─────────────────────────────────────
    _imprimir_archivo(email, codigo_usuario, codigos_claro)


def _codigo_recuperacion() -> str:
    """Genera un código en formato XXXX-XXXX-XXXX (letras mayúsculas + dígitos)."""
    alfabet = string.ascii_uppercase + string.digits
    grupos = ["".join(secrets.choice(alfabet) for _ in range(4)) for _ in range(3)]
    return "-".join(grupos)


def _imprimir_archivo(email: str, codigo_usuario: str, codigos: list[str]) -> None:
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep = "=" * 62

    click.echo()
    click.echo(sep)
    click.echo("  ARCHIVO DE RECUPERACIÓN — PhysioScan")
    click.echo(f"  Usuario       : {email}")
    click.echo(f"  Código usuario: {codigo_usuario}")
    click.echo(f"  Generado el   : {fecha}")
    click.echo(sep)
    click.echo()
    click.echo("  IMPORTANTE: guarda estos 12 códigos en un lugar seguro.")
    click.echo("  Son de un solo uso. El sistema NO puede mostrarlos de nuevo.")
    click.echo()
    for i, c in enumerate(codigos, 1):
        click.echo(f"  {i:>2}.  {c}")
    click.echo()
    click.echo(sep)
    click.echo("  Si los pierdes, pide al administrador que los regenere.")
    click.echo(sep)
    click.echo()
    click.secho("✓ Administrador creado correctamente.", fg="green", bold=True)
