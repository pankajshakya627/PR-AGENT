import os
import logging
from typing import Dict, Any, List, Optional
from src.tenant import get_current_tenant_id, log_tenant_action

logger = logging.getLogger(__name__)

# ============================================================================
# Tier 1: Working Memory (L1) - Active Focus & Context window optimization
# ============================================================================

class L1WorkingMemory:
    """
    Manages active, high-density focus inside the LLM context window.
    Handles sliding window context limits and prefix caching optimizations.
    """
    @staticmethod
    def optimize_diff_context(diff_text: str, max_chars: int = 12000) -> str:
        """
        Slices diffs to fit within the L1 working focus to optimize KV Cache prefix matching.
        """
        if len(diff_text) <= max_chars:
            return diff_text
            
        logger.info(f"L1 Working Memory: Slicing diff of size {len(diff_text)} to fit max context {max_chars}")
        # Keep heading context and slice the rest safely
        return diff_text[:max_chars] + "\n\n[... Diff truncated in L1 Working Memory to optimize context window & KV Cache ...]"


# ============================================================================
# Tier 2: Episodic Memory (L2) - Trajectory Replay & Event Logging
# ============================================================================

class L2EpisodicMemory:
    """
    Stores session experiences, execution trajectories, and results per tenant.
    Allows experience replay and memory retrieval for answering questions about past turns.
    """
    # Episodic storage: { tenant_id: { pr_url/commit_url: { episode_name: data } } }
    _episodes: Dict[str, Dict[str, Dict[str, Any]]] = {}

    @classmethod
    def record_episode(cls, resource_key: str, episode_name: str, data: Any):
        """
        Saves an execution trajectory or result inside the episodic memory of the tenant.
        """
        tenant_id = get_current_tenant_id() or "default_tenant"
        if tenant_id not in cls._episodes:
            cls._episodes[tenant_id] = {}
        if resource_key not in cls._episodes[tenant_id]:
            cls._episodes[tenant_id][resource_key] = {}
            
        cls._episodes[tenant_id][resource_key][episode_name] = {
            "data": data,
            "timestamp": os.getenv("CURRENT_TIME", "unknown")
        }
        log_tenant_action("record_episode", f"L2 Episodic Memory: Recorded episode '{episode_name}' for resource '{resource_key}'.")

    @classmethod
    def retrieve_episodes(cls, resource_key: str) -> Dict[str, Any]:
        """
        Retrieves all past execution episodes/trajectories for experience replay.
        """
        tenant_id = get_current_tenant_id() or "default_tenant"
        return cls._episodes.get(tenant_id, {}).get(resource_key, {})


# ============================================================================
# Tier 3: Semantic Memory (L3) - Immutable Facts & Team Guidelines
# ============================================================================

class L3SemanticMemory:
    """
    Stores long-term rules, coding facts, and style guides per tenant.
    Injects immutable facts into agent runs to guide structural decisions.
    """
    # Semantic rules store: { tenant_id: [ Rules/Facts ] }
    _semantic_facts: Dict[str, List[str]] = {}

    @classmethod
    def register_rule(cls, rule: str):
        """Registers a persistent style/coding rule for the current tenant."""
        tenant_id = get_current_tenant_id() or "default_tenant"
        if tenant_id not in cls._semantic_facts:
            cls._semantic_facts[tenant_id] = []
        cls._semantic_facts[tenant_id].append(rule)
        log_tenant_action("register_semantic_rule", f"L3 Semantic Memory: Registered rule: {rule[:50]}...")

    @classmethod
    def get_rules(cls) -> List[str]:
        """Returns the list of persistent style guidelines/rules for the current tenant."""
        tenant_id = get_current_tenant_id() or "default_tenant"
        # Always return some sensible default coding practices if none are registered
        default_rules = [
            "Maintain high test coverage for all newly added functions.",
            "Enforce strict input validations for public-facing interface functions.",
            "Use clear typing annotations across all Python modules."
        ]
        return cls._semantic_facts.get(tenant_id, []) + default_rules
