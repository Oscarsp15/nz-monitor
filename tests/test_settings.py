"""Ajustes en SQLite: cifrado de secretos + notificación Telegram (solo nuevos críticos)."""
import sqlite3


def test_secret_cifrado_y_roundtrip(tmp_db):
    from store import get_setting, set_setting

    set_setting("plano", "valor")
    set_setting("token", "secreto123", secret=True)
    assert get_setting("plano") == "valor"
    assert get_setting("token") == "secreto123"

    # el secreto NO se guarda en claro en la BD
    conn = sqlite3.connect(tmp_db)
    raw = conn.execute("SELECT value FROM app_setting WHERE key='token'").fetchone()[0]
    conn.close()
    assert "secreto123" not in raw


def test_telegram_set_get_conserva_token(tmp_db):
    from store import get_telegram, set_telegram

    set_telegram("TOK", "-1001234567890")
    assert get_telegram() == ("TOK", "-1001234567890")
    # guardar solo el chat no debe borrar el token
    set_telegram(None, "-1009999")
    assert get_telegram() == ("TOK", "-1009999")


def test_notify_avisa_activos_y_no_repite(tmp_db, monkeypatch):
    import notify
    from store import set_telegram

    set_telegram("TOK", "-100")  # configurado
    sent: list[str] = []
    monkeypatch.setattr("notify.telegram.send", lambda text: bool(sent.append(text)) or True)

    p1 = {"alerts": [{"ds": 1, "level": "crit", "message": "Dataslice 1 al 97%"}],
          "max_dataslice_pct": 97}
    notify.notify_alerts(p1)  # crítico activo al configurar → avisa (estado vacío en BD)
    assert len(sent) == 1 and "Dataslice 1" in sent[0]

    notify.notify_alerts(p1)  # mismo crítico → no repite (anti-spam)
    assert len(sent) == 1

    p2 = {"alerts": [{"ds": 1, "level": "crit", "message": "d1"},
                     {"ds": 2, "level": "crit", "message": "Dataslice 2 al 96%"}],
          "max_dataslice_pct": 98}
    notify.notify_alerts(p2)  # entra un nuevo crítico (ds2) → avisa
    assert len(sent) == 2 and "Dataslice 2" in sent[1]

    notify.notify_alerts({"alerts": [], "max_dataslice_pct": 80})  # resuelto → avisa una vez
    assert len(sent) == 3 and "sin dataslices" in sent[2].lower()
