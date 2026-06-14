"""Agente IA (tool-calling): ejecuta la herramienta y responde con su resultado."""


def test_agent_llama_tool_y_responde(monkeypatch):
    from notify import agent

    # la tool consulta el "service" → mockeamos la tool directamente
    monkeypatch.setitem(agent.IMPL, "top_skew_tables",
                        lambda **k: [{"db": "DESA_MODELOS", "table": "T1", "skew": 192, "gb": 0.5}])

    # 1ª respuesta del modelo: pide la tool; 2ª: respuesta final usando el resultado
    seq = [
        {"tool_calls": [{"id": "c1", "function": {"name": "top_skew_tables",
                                                  "arguments": '{"limit": 1}'}}]},
        {"content": "La peor distribuida es DESA_MODELOS.T1 (skew 192)."},
    ]
    calls = {"n": 0}

    def fake_chat(messages, tools=None, tool_choice="auto", max_tokens=600):
        m = seq[calls["n"]]
        calls["n"] += 1
        return m

    monkeypatch.setattr(agent.ai, "chat", fake_chat)

    out = agent.run_agent("¿cuál es la tabla peor distribuida?")
    assert "T1" in out
    assert calls["n"] == 2  # una vuelta de tool + respuesta final
