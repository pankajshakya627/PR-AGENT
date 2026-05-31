import asyncio
import os
import pytest
from src.tenant import (
    TenantContext,
    get_current_tenant_id,
    log_tenant_action,
    get_tenant_audit_logs,
    get_tenant_cached_value,
    set_tenant_cached_value,
    tenant_scoped
)

def test_tenant_context_propagation():
    """
    Verifies that TenantContext correctly sets and clears active tenant IDs
    in a thread-safe / async-safe manner.
    """
    assert get_current_tenant_id() is None
    
    with TenantContext("tenant_alpha"):
        assert get_current_tenant_id() == "tenant_alpha"
        
        with TenantContext("tenant_beta"):
            assert get_current_tenant_id() == "tenant_beta"
            
        assert get_current_tenant_id() == "tenant_alpha"
        
    assert get_current_tenant_id() is None


@pytest.mark.asyncio
async def test_async_tenant_isolation():
    """
    Verifies that async tasks running concurrently maintain isolated tenant contexts.
    """
    async def run_task(tenant_name, delay):
        with TenantContext(tenant_name):
            assert get_current_tenant_id() == tenant_name
            await asyncio.sleep(delay)
            assert get_current_tenant_id() == tenant_name
            log_tenant_action("async_verify", f"Verified context safety for {tenant_name}")
            return True

    # Run tasks concurrently
    results = await asyncio.gather(
        run_task("tenant_1", 0.1),
        run_task("tenant_2", 0.05),
        run_task("tenant_3", 0.15)
    )
    assert all(results)


def test_scoped_caching():
    """
    Verifies that cached values are strictly isolated per tenant
    and no cross-tenant leakage is possible.
    """
    # Active caching is enabled by default
    os.environ["ENABLE_CACHING"] = "True"
    
    # Try reading cache key without tenant context -> should refuse
    assert get_tenant_cached_value("common_key") is None
    
    with TenantContext("tenant_red"):
        set_tenant_cached_value("common_key", "data_red")
        assert get_tenant_cached_value("common_key") == "data_red"
        
    with TenantContext("tenant_blue"):
        # Key should be empty/isolated for a different tenant
        assert get_tenant_cached_value("common_key") is None
        set_tenant_cached_value("common_key", "data_blue")
        assert get_tenant_cached_value("common_key") == "data_blue"
        
    # Re-verify tenant red retains its own isolated key
    with TenantContext("tenant_red"):
        assert get_tenant_cached_value("common_key") == "data_red"


def test_structured_audit_logging():
    """
    Verifies that tenant actions are correctly audited with proper scoping.
    """
    test_action = "test_run_isolation"
    test_details = "Asserting log formatting works perfectly"
    
    with TenantContext("tenant_audited"):
        log_tenant_action(test_action, test_details)
        
    logs = get_tenant_audit_logs(limit=5)
    assert len(logs) > 0
    
    # Verify that the logs contain our action
    assert any(test_action in log for log in logs)
    assert any(test_details in log for log in logs)



def test_nvidia_llm_instantiation():
    """
    Verifies that nvidia provider can be created.
    """
    from src.config import get_llm_config
    # Set mock key for test
    os.environ["NVIDIA_API_KEY"] = "mock-key-for-test"
    os.environ["LLM_PROVIDER"] = "nvidia"
    
    config = get_llm_config()
    assert config["provider"] == "nvidia"
    assert config["nvidia_model"] == "meta/llama2-70b"
    assert config["nvidia_base_url"] == "https://integrate.api.nvidia.com/v1"
    
    # Clean up env
    del os.environ["NVIDIA_API_KEY"]
    os.environ["LLM_PROVIDER"] = "groq"


def test_three_tiered_memory_architecture():
    """
    Verifies that Tier 1, Tier 2, and Tier 3 Cognitive Memory structures
    operate correctly, enforce boundaries, and isolate information per tenant.
    """
    from src.memory import L1WorkingMemory, L2EpisodicMemory, L3SemanticMemory
    
    # ------------------ L1 Working Memory ------------------
    short_diff = "diff --git a/test.py b/test.py\n+print('hello')"
    long_diff = "diff --git a/test.py b/test.py\n" + ("+print('hi')\n" * 1500)
    
    assert L1WorkingMemory.optimize_diff_context(short_diff, 100) == short_diff
    optimized = L1WorkingMemory.optimize_diff_context(long_diff, 100)
    assert len(optimized) < len(long_diff)
    assert "truncated" in optimized
    
    # ------------------ L2 Episodic Memory ------------------
    with TenantContext("tenant_yellow"):
        L2EpisodicMemory.record_episode("pr_1", "security_run", {"vulns": 0})
        episodes_yellow = L2EpisodicMemory.retrieve_episodes("pr_1")
        assert "security_run" in episodes_yellow
        assert episodes_yellow["security_run"]["data"] == {"vulns": 0}
        
    with TenantContext("tenant_purple"):
        # Purple should have an isolated empty L2 episode list
        episodes_purple = L2EpisodicMemory.retrieve_episodes("pr_1")
        assert "security_run" not in episodes_purple
        
    # ------------------ L3 Semantic Memory ------------------
    with TenantContext("tenant_yellow"):
        L3SemanticMemory.register_rule("Style: Python functions should not exceed 30 lines.")
        rules_yellow = L3SemanticMemory.get_rules()
        assert any("Python functions should not exceed 30 lines" in r for r in rules_yellow)
        
    with TenantContext("tenant_purple"):
        # Purple should not see Yellow's custom semantic rules
        rules_purple = L3SemanticMemory.get_rules()
        assert not any("Python functions should not exceed 30 lines" in r for r in rules_purple)

