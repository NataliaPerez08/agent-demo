import json


def _fake_response(payload: dict):
    class _Resp:
        def __init__(self, data: bytes):
            self._data = data

        def read(self) -> bytes:
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return _Resp(json.dumps(payload).encode("utf-8"))


def test_local_model_ready_present(monkeypatch):
    from tests import conftest

    monkeypatch.setenv("ANALYST_MODEL", "analyst-local-fast")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda url, timeout=2: _fake_response(
            {"models": [{"name": "qwen2.5:1.5b:latest"}, {"name": "qwen2.5:7b:latest"}]}
        ),
    )

    assert conftest._local_model_ready() is True


def test_local_model_ready_absent(monkeypatch):
    from tests import conftest

    monkeypatch.setenv("ANALYST_MODEL", "analyst-local-fast")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda url, timeout=2: _fake_response({"models": [{"name": "qwen2.5:7b:latest"}]}),
    )

    assert conftest._local_model_ready() is False


def test_local_model_ready_connection_error(monkeypatch):
    from tests import conftest

    monkeypatch.setenv("ANALYST_MODEL", "analyst-local-fast")

    def _raise(*a, **k):
        raise ConnectionError("no server")

    monkeypatch.setattr("urllib.request.urlopen", _raise)

    assert conftest._local_model_ready() is False


def test_local_model_ready_non_local_alias(monkeypatch):
    from tests import conftest

    monkeypatch.setenv("ANALYST_MODEL", "analyst-smart")

    assert conftest._local_model_ready() is False


def test_llm_ready_local_path_uses_probe(monkeypatch):
    from tests import conftest

    monkeypatch.setenv("ANALYST_MODEL", "analyst-local-fast")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda url, timeout=2: _fake_response(
            {"models": [{"name": "qwen2.5:1.5b:latest"}]}
        ),
    )

    assert conftest._is_local_model() is True
    assert conftest._llm_ready() is True


def test_llm_ready_openai_path_uses_api_key(monkeypatch):
    from tests import conftest

    monkeypatch.setenv("ANALYST_MODEL", "analyst-smart")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real")

    assert conftest._is_local_model() is False
    assert conftest._llm_ready() is True


def test_llm_ready_openai_path_dummy_key(monkeypatch):
    from tests import conftest

    monkeypatch.setenv("ANALYST_MODEL", "analyst-smart")
    monkeypatch.setenv("OPENAI_API_KEY", "TU_API_KEY")

    assert conftest._llm_ready() is False