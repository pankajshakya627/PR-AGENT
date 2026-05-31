import os
import sys
import types

from src.tracing import build_langfuse_config, configure_langfuse_environment, langfuse_enabled


def test_langfuse_tracing_disabled_without_credentials(monkeypatch):
    monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    assert langfuse_enabled() is False
    assert build_langfuse_config({"tenant_id": "tenant_a"}, run_name="code_review") is None


def test_langfuse_tracing_builds_callback_config(monkeypatch):
    class FakeCallbackHandler:
        pass

    fake_langfuse = types.ModuleType("langfuse")
    fake_langchain = types.ModuleType("langfuse.langchain")
    fake_langchain.CallbackHandler = FakeCallbackHandler

    monkeypatch.setitem(sys.modules, "langfuse", fake_langfuse)
    monkeypatch.setitem(sys.modules, "langfuse.langchain", fake_langchain)
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")

    config = build_langfuse_config(
        {
            "tenant_id": "tenant_a",
            "pr_url": "https://github.com/example/repo/pull/42",
        },
        run_name="code_review",
        provider="nvidia",
    )

    assert config is not None
    assert isinstance(config["callbacks"][0], FakeCallbackHandler)
    assert config["run_name"] == "code_review"
    assert config["metadata"]["langfuse_user_id"] == "tenant_a"
    assert config["metadata"]["langfuse_session_id"] == "https://github.com/example/repo/pull/42"
    assert config["metadata"]["provider"] == "nvidia"
    assert "pr-agent" in config["tags"]


def test_langfuse_base_url_maps_to_sdk_host(monkeypatch):
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

    configure_langfuse_environment()

    assert os.getenv("LANGFUSE_HOST") == "https://cloud.langfuse.com"
