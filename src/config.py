import os
from typing import Dict, Any, Literal

# LLM Configuration
LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "openai"), # Default to openai
    "openai_model": "gpt-4o-mini",
    "anthropic_model": "claude-3-5-sonnet-20240620",
    "local_base_url": os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:12434/engines/llama.cpp/v1"),
    "local_model": os.getenv("LOCAL_LLM_MODEL", "ai/llama3.2:latest"),
    "temperature": 0.7,
    "max_tokens": 4000,
}

# Agent Coordination Rules
AGENT_CONFIG = {
    "parallel_threshold": 3,
    "timeout_per_agent": 300,
    "max_retries": 2,
    "enable_caching": True,
}

def get_llm_config() -> Dict[str, Any]:
    """Returns the LLM configuration."""
    config = LLM_CONFIG.copy()
    
    # Auto-detect provider if not explicitly set and keys are missing
    if config["provider"] == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        if os.getenv("OPENAI_API_KEY"):
            config["provider"] = "openai"
            
    return config

def get_agent_config() -> Dict[str, Any]:
    """Returns the agent configuration."""
    return AGENT_CONFIG
