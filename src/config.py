import os
from typing import Dict, Any, Literal

# ============================================================================
# LLM Configuration
# ============================================================================
# Provider options: "openai", "anthropic", "local", "openrouter", "groq", "nvidia"
# Set via environment variable LLM_PROVIDER (default: openrouter)

LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "groq"),  # Default to groq
    
    # OpenAI Configuration
    "openai_model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    
    # Anthropic Configuration  
    "anthropic_model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
    
    # OpenRouter Configuration (for models like Grok, Llama, etc.)
    "openrouter_model": os.getenv("OPENROUTER_MODEL", "xiaomi/mimo-v2-flash:free"),
    "openrouter_base_url": "https://openrouter.ai/api/v1",
    
    # Groq Configuration (for fast Llama, Mixtral models)
    "groq_model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
    "groq_base_url": "https://api.groq.com/openai/v1",
    
    # Local LLM Configuration (for llama.cpp, Ollama, LM Studio, etc.)
    "local_base_url": os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:12434/engines/llama.cpp/v1"),
    "local_model": os.getenv("LOCAL_LLM_MODEL", "ai/llama3.2:latest"),
    
    # NVIDIA Configuration
    "nvidia_model": os.getenv("NVIDIA_MODEL", "minimaxai/minimax-m2.7"),
    "nvidia_base_url": os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    
    # Shared Settings
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
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
    Returns the LLM configuration with FRESH environment variables.
    
    This reads env vars each time to support dynamic updates from Streamlit UI.
    
    Auto-detects provider if not explicitly set:
    - If ANTHROPIC_API_KEY is set but OPENAI_API_KEY is not → use anthropic
    - If LOCAL_LLM_BASE_URL is set → use local
    - Otherwise → use openai (default)
    """
    # Read FRESH values from environment each time
    config = {
        "provider": os.getenv("LLM_PROVIDER", "groq"),
        
        # OpenAI Configuration
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        
        # Anthropic Configuration  
        "anthropic_model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
        
        # OpenRouter Configuration
        "openrouter_model": os.getenv("OPENROUTER_MODEL", "xiaomi/mimo-v2-flash:free"),
        "openrouter_base_url": "https://openrouter.ai/api/v1",
        
        # Groq Configuration
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        "groq_base_url": "https://api.groq.com/openai/v1",
        
        # Local LLM Configuration
        "local_base_url": os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:12434/engines/llama.cpp/v1"),
        "local_model": os.getenv("LOCAL_LLM_MODEL", "ai/llama3.2:latest"),
        
        # NVIDIA Configuration
        "nvidia_model": os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
        "nvidia_base_url": os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        
        # Shared Settings
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "8000")),
    }
    
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
    if os.getenv("NVIDIA_API_KEY"):
        api_keys_present.append("Nvidia")

    
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
    
    logger.info(f"🤖 Using LLM provider: {config['provider']} with model: {config.get(config['provider'] + '_model', 'N/A')}")
    
    return config

def get_agent_config() -> Dict[str, Any]:
    """Returns the agent coordination configuration."""
    return AGENT_CONFIG
