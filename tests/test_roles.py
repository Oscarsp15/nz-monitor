"""Matriz de permisos: admin/operador/viewer sobre usuarios, ajustes y consultas en vivo."""
import pytest


@pytest.fixture
def no_netezza(monkeypatch):
    """El router de Netezza responde sin tocar el appliance (aquí se prueban permisos)."""
    from netezza import service

    monkeypatch.setattr(service, "overview", lambda db=None, fresh=False: {"databases": []})
    return service


def test_operador_y_viewer_no_entran_a_usuarios_ni_ajustes(client, make_user):
    for rol in ("operador", "viewer"):
        headers = make_user(f"user_{rol}", rol)
        assert client.get("/api/users", headers=headers).status_code == 403
        assert client.post("/api/users", headers=headers,
                           json={"username": "otro", "password": "contrasena123",
                                 "role": "viewer"}).status_code == 403
        assert client.get("/api/settings/sftp", headers=headers).status_code == 403
        assert client.put("/api/settings/sftp", headers=headers,
                          json={"host": "x"}).status_code == 403


def test_viewer_no_puede_forzar_consulta_en_vivo(client, make_user, no_netezza):
    headers = make_user("solo_lectura", "viewer")

    r = client.get("/api/overview?fresh=true", headers=headers)
    assert r.status_code == 403
    assert "rol" in r.json()["detail"]
    assert "operador" in r.json()["detail"]

    # `live=true` (modo en vivo) también está vetado
    assert client.get("/api/dataslices?live=true", headers=headers).status_code == 403

    # pero leer el dato ya recolectado sí puede
    assert client.get("/api/overview", headers=headers).status_code == 200
    assert client.get("/api/monitoring/health", headers=headers).status_code == 200


def test_operador_si_puede_forzar_consulta_en_vivo(client, make_user, no_netezza):
    headers = make_user("operario", "operador")
    assert client.get("/api/overview?fresh=true", headers=headers).status_code == 200


def test_prueba_de_conexion_es_de_operador_para_arriba(client, make_user, monkeypatch):
    from sftp import service as sftp_service

    monkeypatch.setattr(sftp_service, "health", lambda: {"status": "ok"})

    viewer = make_user("solo_lectura", "viewer")
    operador = make_user("operario", "operador")
    assert client.post("/api/settings/sftp/test", headers=viewer).status_code == 403
    assert client.post("/api/settings/sftp/test", headers=operador).status_code == 200
