import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _env_flag_enabled(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_flag_disabled(name: str) -> bool:
    raw = os.getenv(name)
    return raw is not None and raw.strip().lower() in {"0", "false", "no", "off"}


def langfuse_credentials_present() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def configure_langfuse_environment() -> None:
    """Normalize supported Langfuse env vars before the SDK initializes."""
    base_url = os.getenv("LANGFUSE_BASE_URL")
    if base_url and not os.getenv("LANGFUSE_HOST"):
        os.environ["LANGFUSE_HOST"] = base_url.strip()


def langfuse_enabled() -> bool:
    """Return whether Langfuse tracing should be attached to LangChain calls."""
    if _env_flag_disabled("LANGFUSE_ENABLED"):
        return False
    return _env_flag_enabled("LANGFUSE_ENABLED") or langfuse_credentials_present()


def _session_id_from_context(context: Dict[str, Any]) -> str:
    if context.get("pr_url"):
        return str(context["pr_url"])
    if context.get("commit_url"):
        return str(context["commit_url"])
    repo_name = context.get("repo_name")
    head_branch = context.get("head_branch")
    if repo_name or head_branch:
        return f"{repo_name or 'repo'}:{head_branch or 'branch'}"
    return str(context.get("tenant_id") or "unknown-session")


def build_langfuse_config(
    context: Dict[str, Any],
    *,
    run_name: str,
    provider: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Build LangChain RunnableConfig for Langfuse tracing.

    Langfuse is optional: missing credentials or missing SDK keep local/dev runs
    working without emitting traces.
    """
    if not langfuse_enabled():
        return None

    if not langfuse_credentials_present():
        logger.warning("LANGFUSE_ENABLED is set but LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY is missing; tracing disabled.")
        return None

    configure_langfuse_environment()

    try:
        from langfuse.langchain import CallbackHandler
    except ImportError:
        logger.warning("Langfuse tracing requested but the 'langfuse' package is not installed; tracing disabled.")
        return None

    tenant_id = str(context.get("tenant_id") or "unknown-tenant")
    session_id = _session_id_from_context(context)
    tags = ["pr-agent", run_name]

    metadata: Dict[str, Any] = {
        "langfuse_user_id": tenant_id,
        "langfuse_session_id": session_id,
        "langfuse_tags": tags,
        "tenant_id": tenant_id,
        "agent": run_name,
    }
    if provider:
        metadata["provider"] = provider

    return {
        "callbacks": [CallbackHandler()],
        "run_name": run_name,
        "tags": tags,
        "metadata": metadata,
    }
