# Quick Start Guide

## Choose Your LLM Provider

### Option 1: OpenAI (Default)
```bash
cp .env.example .env
# Edit .env and set:
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
```

### Option 2: Local LLM (llama.cpp/Ollama/LM Studio)
```bash
cp .env.example .env
# Edit .env and set:
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:12434/engines/llama.cpp/v1
LOCAL_LLM_MODEL=ai/llama3.2:latest
```

**Health Check** - Verify your local LLM is running:
```bash
# Test endpoint is responsive
curl http://localhost:12434/health

# Or for Ollama:
curl http://localhost:11434/api/tags

# Or test with a simple request:
curl http://localhost:12434/engines/llama.cpp/v1/models
```

### Option 3: Anthropic Claude
```bash
cp .env.example .env
# Edit .env and set:
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
```

## Run the Server
```bash
python main.py
```

That's it! The system will automatically use your chosen provider.
