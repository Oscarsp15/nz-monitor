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


def test_notify_solo_avisa_criticos_nuevos(tmp_db, monkeypatch):
    import notify
    from store import set_telegram

    set_telegram("TOK", "-100")  # configurado
    sent: list[str] = []
    monkeypatch.setattr("notify.telegram.send", lambda text: bool(sent.append(text)) or True)

    prev = {"data": {"alerts": [{"ds": 1, "level": "crit"}]}}
    payload = {
        "alerts": [
            {"ds": 1, "level": "crit", "message": "Dataslice 1 al 97%"},
            {"ds": 2, "level": "crit", "message": "Dataslice 2 al 96%"},
        ],
        "count": 2,
        "max_dataslice_pct": 97,
    }
    notify.notify_alerts(prev, payload)

    assert len(sent) == 1
    assert "Dataslice 2" in sent[0]  # solo el nuevo
    assert "Dataslice 1 al 97%" not in sent[0]  # ds1 ya estaba en crítico
