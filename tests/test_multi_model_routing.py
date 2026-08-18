import main


class DummyClient:
    def __init__(self, name):
        self.name = name

    def chat(self, system_prompt, user_prompt):
        return self.name


def test_create_agent_llm_calls_keeps_role_models_independent(monkeypatch):
    monkeypatch.setattr(
        main,
        "create_llm_client",
        lambda _config, agent_name: DummyClient(agent_name),
    )
    calls = main.create_agent_llm_calls({"agents": {}})
    assert set(calls) == {"qigua_agent", "scene_router", "yao_agent", "reporter"}
    assert calls["qigua_agent"]("", "") == "qigua_agent"
    assert calls["reporter"]("", "") == "reporter"
