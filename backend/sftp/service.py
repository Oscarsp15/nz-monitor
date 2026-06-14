"""Lógica SFTP: disco, archivos viejos, listado. Credenciales desde el store (config web).

Saneo estricto de rutas/patrones antes de armar comandos remotos (anti-inyección de shell):
solo se permiten caracteres seguros; lo demás se rechaza/normaliza.
"""
import re

from store import get_sftp

from .connection import get_sftp_connection

_PATH_RE = re.compile(r"^[A-Za-z0-9_./\-]{1,256}$")
_PATTERN_RE = re.compile(r"^[A-Za-z0-9_.*?\-]{1,64}$")


def _safe_path(p: str | None) -> str:
    p = (p or "/").strip()
    if not _PATH_RE.match(p) or ".." in p:  # sin '..' para no escapar
        raise ValueError("ruta no válida")
    return p


def _safe_pattern(p: str | None) -> str:
    p = (p or "*").strip()
    if not _PATTERN_RE.match(p):
        raise ValueError("patrón no válido")
    return p


def _conn():
    c = get_sftp()
    if not c["host"]:
        raise ValueError("SFTP no configurado (ver Ajustes)")
    return get_sftp_connection(c["host"], c["port"], c["user"], c["password"], c["private_key"])


def health() -> dict:
    with _conn() as conn:
        return conn.test()


def disk_usage(path: str = "/") -> dict:
    path = _safe_path(path)
    with _conn() as conn:
        r = conn.run(f"df -h {path}")
    lines = [ln for ln in r["stdout"].strip().split("\n") if ln]
    if r["exit_code"] != 0 or len(lines) < 2:
        return {"path": path, "error": r["stderr"] or "sin salida de df"}
    d = lines[1].split()
    return {"path": path, "filesystem": d[0], "size": d[1], "used": d[2],
            "available": d[3], "use_percent": d[4], "mounted_on": d[5] if len(d) > 5 else ""}


def du_top(path: str, top: int = 20) -> list[dict]:
    path = _safe_path(path)
    top = max(1, min(int(top or 20), 100))
    with _conn() as conn:
        r = conn.run(f"du -sh {path}/* 2>/dev/null | sort -rh | head -n {top}")
    out = []
    for line in r["stdout"].strip().split("\n"):
        parts = line.split(None, 1)
        if len(parts) == 2:
            out.append({"size": parts[0], "path": parts[1]})
    return out


def old_files(path: str, days: int = 90, pattern: str = "*", max_results: int = 100) -> list[dict]:
    path = _safe_path(path)
    pattern = _safe_pattern(pattern)
    days = max(0, min(int(days or 90), 100000))
    max_results = max(1, min(int(max_results or 100), 1000))
    with _conn() as conn:
        r = conn.run(
            f'find {path} -name "{pattern}" -type f -mtime +{days} '
            f'-exec ls -lh {{}} \\; 2>/dev/null | head -n {max_results}'
        )
    files = []
    for line in r["stdout"].strip().split("\n"):
        parts = line.split()
        if len(parts) >= 9:
            files.append({"permissions": parts[0], "size": parts[4],
                          "modified": f"{parts[5]} {parts[6]} {parts[7]}",
                          "path": " ".join(parts[8:])})
    return files


def list_dir(path: str) -> list[dict]:
    path = _safe_path(path)
    with _conn() as conn:
        r = conn.run(f"ls -la {path}")
    out = []
    for line in r["stdout"].strip().split("\n"):
        if not line or line.startswith("total"):
            continue
        parts = line.split()
        if len(parts) >= 9:
            out.append({"permissions": parts[0], "size": parts[4],
                        "modified": f"{parts[5]} {parts[6]} {parts[7]}",
                        "name": " ".join(parts[8:]), "is_dir": parts[0].startswith("d")})
    return out
