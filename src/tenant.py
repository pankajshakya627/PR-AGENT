import contextvars
import logging
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Context variable to hold the tenant ID
_tenant_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("tenant_id", default=None)
_tenant_id_pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")

# ----------------------------------------------------------------------------
# Tenant Propagation
# ----------------------------------------------------------------------------

class TenantContext:
    """
    Context manager to set and propagate tenant context across threads/async tasks.
    """
    def __init__(self, tenant_id: str):
        self.tenant_id = validate_tenant_id(tenant_id)
        self.token = None

    def __enter__(self):
        self.token = _tenant_id_var.set(self.tenant_id)
        log_tenant_action("context_enter", f"Entered tenant context: {self.tenant_id}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log_tenant_action("context_exit", f"Exited tenant context: {self.tenant_id}")
        if self.token:
            _tenant_id_var.reset(self.token)


def get_current_tenant_id() -> Optional[str]:
    """Retrieves the tenant_id from the active contextvars context."""
    return _tenant_id_var.get()


def validate_tenant_id(tenant_id: Any) -> str:
    """Return a normalized tenant ID or raise if it cannot safely scope data."""
    if not isinstance(tenant_id, str):
        raise ValueError("Valid tenant_id required")

    normalized = tenant_id.strip()
    if not normalized or not _tenant_id_pattern.fullmatch(normalized):
        raise ValueError("Valid tenant_id required")

    return normalized


def resolve_tenant_id(tenant_id: Optional[str] = None) -> str:
    """Resolve an explicit tenant ID or DEFAULT_TENANT_ID, then validate it."""
    candidate = tenant_id if tenant_id is not None else os.getenv("DEFAULT_TENANT_ID")
    return validate_tenant_id(candidate)


def require_current_tenant_id() -> str:
    """Return the active tenant ID, failing closed when no tenant is scoped."""
    return validate_tenant_id(get_current_tenant_id())


# ----------------------------------------------------------------------------
# Audit Logging
# ----------------------------------------------------------------------------

AUDIT_LOG_FILE = "config/tenant_audit.log"

def log_tenant_action(action: str, details: str, status: str = "SUCCESS"):
    """
    Writes structured, timestamped audit logs for every tenant action.
    Ensures operational safety, monitoring, and compliance.
    """
    tenant_id = get_current_tenant_id() or "ANONYMOUS"
    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp} | TENANT: {tenant_id} | ACTION: {action} | STATUS: {status} | DETAILS: {details}\n"
    
    os.makedirs("config", exist_ok=True)
    try:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


def get_tenant_audit_logs(limit: int = 50) -> list[str]:
    """Retrieves the last N audit logs from the log file."""
    if not os.path.exists(AUDIT_LOG_FILE):
        return []
    
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return [line.strip() for line in lines[-limit:]]
    except Exception as e:
        logger.error(f"Failed to read audit logs: {e}")
        return []


# ----------------------------------------------------------------------------
# Scoped Caching
# ----------------------------------------------------------------------------

# In-memory tenant-isolated cache. Keys are strictly namespaced by tenant ID.
# Prevents unauthorized access or cross-tenant cache pollution.
_tenant_cache: Dict[str, Any] = {}


def _tenant_cache_key(tenant_id: str, cache_key: str) -> str:
    return f"tenant:{tenant_id}:{cache_key}"

def get_tenant_cached_value(cache_key: str) -> Optional[Any]:
    """
    Retrieves a cached value for the current tenant.
    Guarantees strict isolation by refusing access if no tenant is set.
    """
    tenant_id = require_current_tenant_id()
    
    value = _tenant_cache.get(_tenant_cache_key(tenant_id, cache_key))
    if value is not None:
        log_tenant_action("cache_hit", f"Cache key '{cache_key}' found.")
    return value


def set_tenant_cached_value(cache_key: str, value: Any):
    """
    Caches a value strictly scoped under the current tenant ID.
    """
    tenant_id = require_current_tenant_id()
    _tenant_cache[_tenant_cache_key(tenant_id, cache_key)] = value
    log_tenant_action("cache_store", f"Cached value for key '{cache_key}'.")


def tenant_scoped(func):
    """
    Decorator to wrap agent execute calls with TenantContext and Scoped Caching.
    Ensures that execution context is isolated and data is secured per tenant.
    """
    import functools
    @functools.wraps(func)
    async def wrapper(self, context: dict, *args, **kwargs):
        tenant_id = resolve_tenant_id(context.get("tenant_id"))
        
        # Scope active context
        with TenantContext(tenant_id):
            enable_caching = os.getenv("ENABLE_CACHING", "True").lower() == "true"
            if enable_caching:
                # Construct safe cache key scoped to resource & tenant
                url = context.get("pr_url") or context.get("commit_url") or f"{context.get('repo_name') or 'repo'}/{context.get('head_branch') or 'branch'}"
                cache_key = f"{self.__class__.__name__}:{url}"
                
                cached = get_tenant_cached_value(cache_key)
                if cached is not None:
                    log_tenant_action("cache_retrieve", f"Retrieved cached response for {self.__class__.__name__}")
                    return cached
            
            # Execute actual task
            log_tenant_action("agent_execute", f"Executing agent {self.__class__.__name__}")
            result = await func(self, context, *args, **kwargs)
            
            # Construct resource URL for L2 Episodic Memory scoping
            url = context.get("pr_url") or context.get("commit_url") or f"{context.get('repo_name') or 'repo'}/{context.get('head_branch') or 'branch'}"
            
            if result and "error" not in str(result):
                if enable_caching:
                    set_tenant_cached_value(cache_key, result)
                
                # Record to L2 Episodic Memory
                from src.memory import L2EpisodicMemory
                for key, val in result.items():
                    L2EpisodicMemory.record_episode(url, key, val)
                
            return result
            
    return wrapper

