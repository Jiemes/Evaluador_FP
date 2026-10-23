"""
auth_usuarios.py  –  MÓDULO DE AUTENTICACIÓN, PERMISOS Y CONTROL DE OPERADOR ÚNICO.
Usa exclusivamente la librería estándar (hashlib, json, os, datetime, pathlib).
Ver ARQUITECTURA_Y_REGLAS.md §12.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

DIR_SALIDA = Path(__file__).resolve().parent / "salida"
RUTA_USUARIOS = DIR_SALIDA / "usuarios.json"
RUTA_BLOQUEOS = DIR_SALIDA / "bloqueos_distrito.json"


def hashear_password(password: str) -> str:
    """Devuelve el hash SHA-256 en formato hexadecimal."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def inicializar_almacen() -> None:
    """Crea la carpeta de salida y los archivos JSON si no existen,
    asegurando el usuario 'admin' por defecto."""
    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    if not RUTA_USUARIOS.exists():
        admin_data = {
            "version": 1,
            "usuarios": {
                "admin": {
                    "username": "admin",
                    "password_hash": hashear_password("admin2027"),
                    "nombre": "Administrador General",
                    "rol": "admin",
                    "distritos_permitidos": ["TODOS"],
                    "creado": datetime.datetime.now().isoformat(),
                }
            },
        }
        RUTA_USUARIOS.write_text(json.dumps(admin_data, ensure_ascii=False, indent=2), encoding="utf-8")

    if not RUTA_BLOQUEOS.exists():
        RUTA_BLOQUEOS.write_text("{}", encoding="utf-8")


def _cargar_usuarios_raw() -> dict:
    inicializar_almacen()
    try:
        return json.loads(RUTA_USUARIOS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": 1, "usuarios": {}}


def _guardar_usuarios_raw(data: dict) -> None:
    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    RUTA_USUARIOS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def verificar_credenciales(username: str, password: str) -> dict | None:
    """Verifica usuario y contraseña.
    Devuelve un diccionario con los datos del usuario (sin password_hash) si es correcto;
    si las credenciales son inválidas, devuelve None."""
    if not username or not password:
        return None
    u = username.strip().lower()
    data = _cargar_usuarios_raw()
    usr = data.get("usuarios", {}).get(u)
    if not usr:
        return None
    if usr.get("password_hash") != hashear_password(password):
        return None
    return {
        "username": usr["username"],
        "nombre": usr.get("nombre", u),
        "rol": usr.get("rol", "evaluador"),
        "distritos_permitidos": list(usr.get("distritos_permitidos", [])),
    }


def listar_usuarios() -> dict[str, dict]:
    """Devuelve diccionario con todos los usuarios registrados (con campos públicos, sin hash)."""
    data = _cargar_usuarios_raw()
    resultado = {}
    for u, usr in data.get("usuarios", {}).items():
        resultado[u] = {
            "username": usr.get("username", u),
            "nombre": usr.get("nombre", u),
            "rol": usr.get("rol", "evaluador"),
            "distritos_permitidos": list(usr.get("distritos_permitidos", [])),
            "creado": usr.get("creado", ""),
        }
    return resultado


def crear_o_actualizar_usuario(
    username: str,
    password: str | None,
    nombre: str,
    rol: str,
    distritos_permitidos: list[str],
) -> tuple[bool, str]:
    """Crea un nuevo usuario o actualiza uno existente.
    Si password es None o cadena vacía al actualizar, conserva el hash anterior.
    Valida que username no sea vacío y que rol sea 'admin' o 'evaluador'.
    Devuelve (True, 'Mensaje') o (False, 'Motivo del error')."""
    u = (username or "").strip().lower()
    if not u:
        return False, "El nombre de usuario no puede estar vacío."
    if rol not in ("admin", "evaluador"):
        return False, "El rol debe ser 'admin' o 'evaluador'."
    if not nombre.strip():
        nombre = u

    data = _cargar_usuarios_raw()
    usuarios = data.setdefault("usuarios", {})

    if u in usuarios:
        # Actualización
        usr = usuarios[u]
        if password and password.strip():
            usr["password_hash"] = hashear_password(password.strip())
        usr["nombre"] = nombre.strip()
        # No permitir quitar el rol de admin al usuario 'admin' original
        if u == "admin":
            usr["rol"] = "admin"
            usr["distritos_permitidos"] = ["TODOS"]
        else:
            usr["rol"] = rol
            usr["distritos_permitidos"] = list(distritos_permitidos)
        _guardar_usuarios_raw(data)
        return True, f"Usuario '{u}' actualizado con éxito."
    else:
        # Creación
        if not password or not password.strip():
            return False, "Debe especificar una contraseña para el nuevo usuario."
        usuarios[u] = {
            "username": u,
            "password_hash": hashear_password(password.strip()),
            "nombre": nombre.strip(),
            "rol": rol,
            "distritos_permitidos": ["TODOS"] if rol == "admin" else list(distritos_permitidos),
            "creado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        _guardar_usuarios_raw(data)
        return True, f"Usuario '{u}' creado con éxito."


def eliminar_usuario(username: str) -> tuple[bool, str]:
    """Elimina el usuario indicado.
    PROHIBIDO eliminar al usuario 'admin' (devuelve False)."""
    u = (username or "").strip().lower()
    if u == "admin":
        return False, "No está permitido eliminar al usuario 'admin'."
    data = _cargar_usuarios_raw()
    usuarios = data.get("usuarios", {})
    if u not in usuarios:
        return False, f"El usuario '{u}' no existe."
    del usuarios[u]
    _guardar_usuarios_raw(data)
    return True, f"Usuario '{u}' eliminado con éxito."


# --------------------------------------------------------------------------- #
# Control de Operador Único por Distrito (bloqueos_distrito.json)
# --------------------------------------------------------------------------- #
def _cargar_bloqueos() -> dict:
    inicializar_almacen()
    try:
        return json.loads(RUTA_BLOQUEOS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _guardar_bloqueos(b: dict) -> None:
    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    RUTA_BLOQUEOS.write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")


def obtener_operador_distrito(distrito: str) -> dict | None:
    """Devuelve dict con {'username', 'nombre', 'timestamp'} del operador activo del distrito,
    o None si el distrito no tiene operador asignado."""
    if not distrito:
        return None
    b = _cargar_bloqueos()
    return b.get(distrito)


def tomar_control_distrito(distrito: str, username: str, nombre: str) -> dict:
    """Asigna al usuario como Operador Activo del distrito con timestamp actual.
    Persiste en salida/bloqueos_distrito.json y devuelve el registro creado."""
    b = _cargar_bloqueos()
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    registro = {"username": username, "nombre": nombre, "timestamp": ahora}
    b[distrito] = registro
    _guardar_bloqueos(b)
    return registro


def liberar_control_distrito(distrito: str, username: str) -> bool:
    """Si el distrito está operado por username, lo libera y guarda en disco.
    Devuelve True si liberó el bloqueo, False en caso contrario."""
    if not distrito:
        return False
    b = _cargar_bloqueos()
    if distrito in b and b[distrito].get("username") == username:
        del b[distrito]
        _guardar_bloqueos(b)
        return True
    return False


def forzar_liberacion_distrito(distrito: str) -> bool:
    """Fuerza la liberación del bloqueo de un distrito (para administradores)."""
    if not distrito:
        return False
    b = _cargar_bloqueos()
    if distrito in b:
        del b[distrito]
        _guardar_bloqueos(b)
        return True
    return False


def listar_bloqueos() -> dict[str, dict]:
    """Devuelve el mapa completo de distritos y sus operadores activos."""
    return _cargar_bloqueos()
