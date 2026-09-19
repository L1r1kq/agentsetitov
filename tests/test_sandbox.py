from agentse.tools.sandbox import SandboxDenied, _static_guard, run_sandbox


def test_forbids_import():
    try:
        _static_guard("import os\nprint(os.getcwd())")
        assert False, "must deny"
    except SandboxDenied:
        pass


def test_local_exec(monkeypatch, tmp_path):
    from agentse.config import Settings

    settings = Settings()
    object.__setattr__(settings, "sandbox_enabled", False)
    object.__setattr__(settings, "sandbox_timeout_s", 4)
    out = run_sandbox("result = 7 * 4", settings)
    assert out["ok"] is True
    assert "28" in out["stdout"]
