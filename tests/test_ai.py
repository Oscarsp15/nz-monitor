"""IA Groq (opcional): desactivada por defecto y tolerante a fallos."""


def test_ai_desactivada_sin_key(tmp_db):
    import notify

    # sin key/enabled en la BD → IA apagada, sin tocar Netezza
    assert notify.ai.enabled() is False
    assert notify.ai.ask("hola") is None
    assert notify.ai.alert_analysis([{"ds": 1, "level": "crit", "value": 97}]) is None


def test_ai_enabled_requiere_key_y_toggle(tmp_db):
    import notify
    from store import set_groq

    set_groq("gsk_dummy", "llama-3.3-70b-versatile", False)  # key pero sin activar
    assert notify.ai.enabled() is False
    set_groq(None, None, True)  # activar
    assert notify.ai.enabled() is True
