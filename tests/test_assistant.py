"""Asistente Telegram: seguridad (solo el chat configurado) y respuesta."""


def test_asistente_solo_responde_su_chat(tmp_db, monkeypatch):
    from notify import assistant

    sent: list = []
    monkeypatch.setattr(assistant, "_send", lambda *a, **k: sent.append(a))
    monkeypatch.setattr("notify.ai.ask", lambda *a, **k: "respuesta")

    # mensaje de OTRO chat → se ignora
    assistant.handle_update(
        {"message": {"chat": {"id": -999}, "text": "hola", "message_id": 1}}, my_chat="-100"
    )
    assert sent == []

    # mensaje del chat correcto → responde
    assistant.handle_update(
        {"message": {"chat": {"id": -100}, "text": "hola", "message_id": 2}}, my_chat="-100"
    )
    assert len(sent) == 1


def test_asistente_ignora_sin_texto(tmp_db, monkeypatch):
    from notify import assistant

    sent: list = []
    monkeypatch.setattr(assistant, "_send", lambda *a, **k: sent.append(a))
    assistant.handle_update({"message": {"chat": {"id": -100}, "message_id": 3}}, my_chat="-100")
    assert sent == []
