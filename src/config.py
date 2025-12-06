import os
from typing import Dict, Any, Literal

# ============================================================================
# LLM Configuration
# ============================================================================
# Provider options: "openai", "anthropic", "local"
# Set via environment variable LLM_PROVIDER (default: openai)

LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "openai"),
    
    # OpenAI Configuration
    "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    
    # Anthropic Configuration  
    "anthropic_model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620"),
    
    # Local LLM Configuration (for llama.cpp, Ollama, LM Studio, etc.)
    "local_base_url": os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:12434/engines/llama.cpp/v1"),
    "local_model": os.getenv("LOCAL_LLM_MODEL", "ai/llama3.2:latest"),
    
    # Shared Settings
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4000")),
}

# ============================================================================
# Agent Coordination Configuration
# ============================================================================

AGENT_CONFIG = {
    "parallel_threshold": 3,  # Min tasks to consider parallel execution
    "timeout_per_agent": int(os.getenv("AGENT_TIMEOUT", "300")),  # 5 minutes default
    "max_retries": int(os.getenv("AGENT_MAX_RETRIES", "2")),
    "enable_caching": True,
}

def get_llm_config() -> Dict[str, Any]:
    """
    Returns the LLM configuration.
    
    Auto-detects provider if not explicitly set:
    - If ANTHROPIC_API_KEY is set but OPENAI_API_KEY is not → use anthropic
    - If LOCAL_LLM_BASE_URL is set → use local
    - Otherwise → use openai (default)
    """
    config = LLM_CONFIG.copy()
    
    # Auto-detect provider if set to default and keys are available
    if config["provider"] == "openai" and not os.getenv("OPENAI_API_KEY"):
        if os.getenv("ANTHROPIC_API_KEY"):
            config["provider"] = "anthropic"
            print("ℹ️  Auto-detected Anthropic API key, using provider: anthropic")
        elif os.getenv("LOCAL_LLM_BASE_URL"):
            config["provider"] = "local"
            print("ℹ️  Auto-detected local LLM base URL, using provider: local")
    
    print(f"🤖 Using LLM provider: {config['provider']}")
    
    return config

def get_agent_config() -> Dict[str, Any]:
    """Returns the agent coordination configuration."""
    return AGENT_CONFIG
