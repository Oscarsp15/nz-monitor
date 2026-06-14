"""Conexión SSH/SFTP con Paramiko (portado de v1). Comandos remotos para disco/archivos.

⚠️ Las rutas/patrones se sanean en service.py ANTES de construir comandos (evita inyección).
"""
import contextlib
import io
from contextlib import contextmanager
from typing import Any

import paramiko

from config import get_settings

S = get_settings()


class SFTPConnection:
    def __init__(self, host: str, port: int, username: str,
                 password: str | None = None, private_key: str | None = None):
        self.host, self.port, self.username = host, port, username
        self.password, self.private_key = password, private_key
        self._client: paramiko.SSHClient | None = None

    def connect(self) -> paramiko.SSHClient:
        if self._client is None:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # noqa: S507 (red interna)
            kw: dict[str, Any] = {"hostname": self.host, "port": self.port,
                                  "username": self.username, "timeout": S.sftp_connection_timeout}
            if self.private_key:
                key_file = io.StringIO(self.private_key)
                for kind in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
                    try:
                        key_file.seek(0)
                        kw["pkey"] = kind.from_private_key(key_file)
                        break
                    except paramiko.SSHException:
                        continue
            elif self.password:
                kw["password"] = self.password
            c.connect(**kw)
            self._client = c
        return self._client

    def close(self) -> None:
        if self._client:
            with contextlib.suppress(Exception):
                self._client.close()
            self._client = None

    def test(self) -> dict:
        try:
            self.connect()
            return {"status": "connected", "host": self.host, "port": self.port}
        except Exception as e:  # noqa: BLE001
            return {"status": "error", "host": self.host, "port": self.port, "error": str(e)}

    def run(self, command: str, timeout: int | None = None) -> dict:
        client = self.connect()
        _, out, err = client.exec_command(command, timeout=timeout or S.sftp_command_timeout)
        code = out.channel.recv_exit_status()
        return {"stdout": out.read().decode(errors="replace"),
                "stderr": err.read().decode(errors="replace"), "exit_code": code}


@contextmanager
def get_sftp_connection(host: str, port: int, username: str,
                        password: str | None = None, private_key: str | None = None):
    conn = SFTPConnection(host, port, username, password, private_key)
    try:
        yield conn
    finally:
        conn.close()
