import os
from typing import Dict, Any, Literal

# ============================================================================
# LLM Configuration
# ============================================================================
# Provider options: "openai", "anthropic", "local", "openrouter"
# Set via environment variable LLM_PROVIDER (default: openai)

LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "openai"),
    
    # OpenAI Configuration
    "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    
    # Anthropic Configuration  
    "anthropic_model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620"),
    
    # OpenRouter Configuration (for models like Grok, Llama, etc.)
    "openrouter_model": os.getenv("OPENROUTER_MODEL", "x-ai/grok-beta"),
    "openrouter_base_url": "https://openrouter.ai/api/v1",
    
    # Local LLM Configuration (for llama.cpp, Ollama, LM Studio, etc.)
    "local_base_url": os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:12434/engines/llama.cpp/v1"),
    "local_model": os.getenv("LOCAL_LLM_MODEL", "ai/llama3.2:latest"),
    
    # Shared Settings
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "8000")),  # Increased default for larger models
}

# ============================================================================
# Agent Coordination Configuration
# ============================================================================

AGENT_CONFIG = {
    "parallel_threshold": int(os.getenv("PARALLEL_THRESHOLD", "3")),  # Min tasks to consider parallel execution
    "timeout_per_agent": int(os.getenv("AGENT_TIMEOUT", "300")),  # 5 minutes default
    "max_retries": int(os.getenv("AGENT_MAX_RETRIES", "2")),
    "enable_caching": True,
}

# Setup logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_llm_config() -> Dict[str, Any]:
    """
    Returns the LLM configuration.
    
    Auto-detects provider if not explicitly set:
    - If ANTHROPIC_API_KEY is set but OPENAI_API_KEY is not → use anthropic
    - If LOCAL_LLM_BASE_URL is set → use local
    - Otherwise → use openai (default)
    """
    config = LLM_CONFIG.copy()
    
    # Check for conflicting API keys
    api_keys_present = []
    if os.getenv("OPENAI_API_KEY"):
        api_keys_present.append("OpenAI")
    if os.getenv("ANTHROPIC_API_KEY"):
        api_keys_present.append("Anthropic")
    if os.getenv("OPENROUTER_API_KEY"):
        api_keys_present.append("OpenRouter")
    if os.getenv("LOCAL_LLM_BASE_URL"):
        api_keys_present.append("Local")
    
    if len(api_keys_present) > 1:
        logger.warning(f"⚠️  Multiple LLM configurations detected: {', '.join(api_keys_present)}. Using: {config['provider']}")
    
    # Auto-detect provider if set to default and keys are available
    if config["provider"] == "openai" and not os.getenv("OPENAI_API_KEY"):
        if os.getenv("ANTHROPIC_API_KEY"):
            config["provider"] = "anthropic"
            logger.info("ℹ️  Auto-detected Anthropic API key, using provider: anthropic")
        elif os.getenv("LOCAL_LLM_BASE_URL"):
            config["provider"] = "local"
            logger.info("ℹ️  Auto-detected local LLM base URL, using provider: local")
    
    logger.info(f"🤖 Using LLM provider: {config['provider']}")
    
    return config

def get_agent_config() -> Dict[str, Any]:
    """Returns the agent coordination configuration."""
    return AGENT_CONFIG
