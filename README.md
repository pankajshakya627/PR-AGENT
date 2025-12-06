# PR-Agent: Intelligent Pull Request Agent System

## Overview

PR-Agent is an intelligent system that uses LangGraph and LangChain to coordinate multiple specialized agents for comprehensive pull request analysis. The system analyzes task dependencies and orchestrates agents through parallel, sequential, or hybrid execution patterns based on requirements.

---

## Terminal Usage Guide

### Prerequisites

1. **Python 3.10+** installed
2. **Virtual environment** activated
3. **API Keys** configured (OpenAI or Anthropic)

### Setup

```bash
# 1. Clone and navigate to the project
cd /Volumes/CrucialX9_MAC/Local_MCPs/pr-agent

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install dependencies (if not already installed)
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env  # Create if doesn't exist
# Edit .env and add your API keys:
# OPENAI_API_KEY=your_key_here
# or
# ANTHROPIC_API_KEY=your_key_here
# GITHUB_TOKEN=your_github_token  # Optional, for private repos
```

---

### Usage Option 1: FastMCP Server (Recommended)

The PR-Agent exposes all functionality via FastMCP protocol for use with Claude Desktop or other MCP clients.

#### Start the MCP Server

```bash
# Run the server
python main.py

# Or use the helper script
./run_agent.sh
```

#### Available MCP Tools

Once the server is running, the following tools are available:

1. **review_pr** - Perform code review on a PR
2. **describe_pr** - Generate PR description
3. **improve_code** - Suggest code improvements
4. **ask_pr** - Ask questions about a PR
5. **update_changelog** - Generate changelog entry
6. **create_pull_request** - Create PR from requirements

#### Available MCP Prompts

Access system prompts for each agent:
- `code_review_prompt()`
- `pr_description_prompt()`
- `code_improvement_prompt()`
- `pr_questions_prompt()`
- `changelog_prompt()`
- `task_dependency_prompt()`

---

### Usage Option 2: Direct Python API

Use the PR-Agent directly from Python scripts or terminal.

#### Basic Example

```python
import asyncio
from src.graph import app

async def review_pr(pr_url: str):
    """Review a pull request."""
    
    # Initial state
    initial_state = {
        "pr_requirements": f"Review this PR: {pr_url}",
        "pr_url": pr_url,
        "github_token": None,  # Loaded from env
        "task_graph": {},
        "execution_mode": "hybrid",
        "agent_results": {},
        "errors": [],
        "final_pr": None
    }
    
    # Configuration for state persistence
    config = {
        "configurable": {
            "thread_id": "pr-review-001"  # Unique ID for resumption
        }
    }
    
    # Execute workflow
    result = await app.ainvoke(initial_state, config=config)
    
    return result

# Run it
if __name__ == "__main__":
    pr_url = "https://github.com/owner/repo/pull/123"
    result = asyncio.run(review_pr(pr_url))
    print(result)
```

#### Using Individual Agents

```python
from src.agents.specialized import CodeReviewAgent, PRDescriptionAgent
from src.state import PRAgentState

async def run_code_review(pr_url: str):
    """Run code review agent directly."""
    
    state: PRAgentState = {
        "pr_requirements": "",
        "pr_url": pr_url,
        "github_token": None,
        "agent_results": {},
        "execution_mode": "sequential",
        "task_graph": {},
        "final_pr": None,
        "errors": []
    }
    
    agent = CodeReviewAgent()
    result = await agent.execute(state)
    
    return result.get("code_review", {})
```

---

### Usage Option 3: Command Line Scripts

#### Create a Quick Review Script

Save this as `quick_review.py`:

```python
#!/usr/bin/env python
"""Quick PR review from command line."""

import asyncio
import sys
from src.agents.specialized import CodeReviewAgent

async def main(pr_url: str):
    state = {
        "pr_requirements": "",
        "pr_url": pr_url,
        "github_token": None,
        "agent_results": {},
        "execution_mode": "sequential",
        "task_graph": {},
        "final_pr": None,
        "errors": []
    }
    
    agent = CodeReviewAgent()
    result = await agent.execute(state)
    
    review = result.get("code_review", {})
    print("\n=== Code Review Results ===\n")
    print(review)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quick_review.py <PR_URL>")
        sys.exit(1)
    
    asyncio.run(main(sys.argv[1]))
```

Run it:
```bash
python quick_review.py https://github.com/owner/repo/pull/123
```

---

### Complete Workflow Examples

#### Example 1: Full PR Analysis with All Agents

```python
import asyncio
from src.graph import app

async def full_analysis():
    initial_state = {
        "pr_requirements": """
        Analyze PR for security issues, generate description, 
        and create changelog entry:
        https://github.com/owner/repo/pull/123
        """,
        "pr_url": None,  # Extracted from requirements
        "github_token": None,
        "task_graph": {},
        "execution_mode": "hybrid",
        "agent_results": {},
        "errors": [],
        "final_pr": None
    }
    
    config = {"configurable": {"thread_id": "full-analysis-001"}}
    result = await app.ainvoke(initial_state, config=config)
    
    # Access results
    print("Agent Results:", result["agent_results"])
    print("Errors:", result.get("errors", []))
    print("Final PR:", result.get("final_pr"))

asyncio.run(full_analysis())
```

#### Example 2: Resume Interrupted Workflow

```python
import asyncio
from src.graph import app

async def resume_workflow():
    """Resume a previously interrupted workflow."""
    
    # Same thread_id as before
    config = {"configurable": {"thread_id": "full-analysis-001"}}
    
    # Pass None to continue from last checkpoint
    result = await app.ainvoke(None, config=config)
    
    return result

asyncio.run(resume_workflow())
```

#### Example 3: Ask Questions About a PR

```python
import asyncio
from src.agents.specialized import PRQuestionsAgent

async def ask_question(pr_url: str, question: str):
    state = {
        "pr_requirements": "",
        "pr_url": pr_url,
        "question": question,
        "github_token": None,
        "agent_results": {},
        "execution_mode": "sequential",
        "task_graph": {},
        "final_pr": None,
        "errors": []
    }
    
    agent = PRQuestionsAgent()
    result = await agent.execute(state)
    
    print(f"\nQ: {question}")
    print(f"A: {result.get('answer', 'No answer')}\n")

# Run it
pr_url = "https://github.com/owner/repo/pull/123"
question = "What are the main changes in this PR?"
asyncio.run(ask_question(pr_url, question))
```

---

### Environment Variables

Create a `.env` file in the project root:

```bash
# LLM Provider Configuration
LLM_PROVIDER=openai  # or 'anthropic' or 'local'

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# GitHub Token (optional, for private repos)
GITHUB_TOKEN=ghp_...

# Local LLM Configuration (if using local provider)
LOCAL_LLM_BASE_URL=http://localhost:12434/engines/llama.cpp/v1
LOCAL_LLM_MODEL=ai/llama3.2:latest
```

---

### Testing Your Setup

#### Quick Test

```bash
# Test imports
python -c "from src.graph import app; print('✅ Setup OK')"

# Test state reducers
python -c "from src.state import merge_agent_results; print('✅ Reducers OK')"
```

#### Run Tests (if available)

```bash
pytest tests/ -v
```

---

### Troubleshooting

#### "No module named 'langgraph'"
```bash
pip install langgraph langchain langchain-openai langchain-anthropic
```

#### "OPENAI_API_KEY not found"
```bash
# Make sure .env file exists and is loaded
echo "OPENAI_API_KEY=your_key" >> .env
source .env  # Or restart terminal
```

#### "Import Error: cannot import FastMCP"
```bash
pip install fastmcp
```

#### Graph Import Fails (API Key Required)
The analyzer initializes LLM on import. Ensure API keys are set:
```bash
export OPENAI_API_KEY=your_key_here
# Then run Python
```

---

### Advanced Usage

#### Custom Execution Modes

```python
# Force parallel execution only
initial_state["execution_mode"] = "parallel"

# Force sequential execution only  
initial_state["execution_mode"] = "sequential"

# Hybrid (auto-determined, default)
initial_state["execution_mode"] = "hybrid"
```

#### Accessing Checkpointed State

```python
from src.graph import app

# Get state history for a thread
thread_id = "my-workflow"
config = {"configurable": {"thread_id": thread_id}}

# This will show all checkpoints
state_snapshot = app.get_state(config)
print(state_snapshot)
```

#### Custom Agent Configuration

Edit `src/config.py`:

```python
AGENT_CONFIG = {
    "parallel_threshold": 3,
    "timeout_per_agent": 300,  # 5 minutes
    "max_retries": 2,
    "enable_caching": True,
}
```

---

### Output Format

All agents return results in **TOON** (Token Oriented Object Notation) format for efficiency:

```
summary: Code review completed
status: REQUEST_CHANGES
issues[3]{severity,type,file,line,description,suggestion}:
critical,security,api.py,45,SQL injection risk,Use parameterized queries
major,bug,utils.py,12,Uncaught exception,Add try-catch block
minor,style,main.py,8,Missing docstring,Add module docstring
```

---

## Architecture

- **LangGraph** - Workflow orchestration with state persistence
- **LangChain** - LLM integration (OpenAI, Anthropic, Local)
- **FastMCP** - Model Context Protocol server
- **Specialized Agents** - Code Review, Testing, Documentation, Security
- **Task Analyzer** - Dependency analysis and execution planning

---

## Key Features

✅ **State Persistence** - Workflows resume after interruption  
✅ **Conditional Routing** - Smart execution (parallel/sequential/hybrid)  
✅ **Dependency Management** - Topological sort for optimal execution  
✅ **Error Handling** - Retry logic with exponential backoff  
✅ **Observability** - Comprehensive logging throughout  
✅ **TOON Format** - Token-efficient structured output  

---

## Features

-   **Specialized Agents**:
    -   `CodeReviewAgent`: Analyzes diffs and reports issues (bugs, style, docs) in a structured table.
    -   `PRDescriptionAgent`: Generates comprehensive PR titles, summaries, and walkthroughs.
    -   `CodeImprovementAgent`: Suggests code optimizations and refactoring.
    -   `PRQuestionsAgent`: Answers specific questions about the PR content.
    -   `ChangelogAgent`: Generates concise changelog entries.
-   **TOON Integration**: Uses Token Oriented Object Notation for highly efficient, structured data exchange with LLMs, reducing token usage and improving parsing reliability.
-   **Local LLM Support**: Configurable to work with local LLMs (e.g., via LM Studio, Ollama) in addition to OpenAI and Anthropic.
-   **LangGraph Orchestration**: Manages complex agent workflows and state.
-   **FastMCP Server**: Exposes all capabilities as standard MCP tools for integration with IDEs (Cursor, VS Code) and AI assistants (Claude Desktop).

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/pankajshakya627/PR-AGENT.git
    cd PR-AGENT
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Create a `.env` file in the root directory with your API keys and configuration:

```bash
# LLM Provider (openai, anthropic, or local)
LLM_PROVIDER=openai

# API Keys
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...

# Local LLM Configuration (if LLM_PROVIDER=local)
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LOCAL_LLM_MODEL=qwen2.5-coder-32b-instruct
```

## Usage

### Running the Server

Start the MCP server:

```bash
python main.py
```

### Available Tools

The server exposes the following tools:

-   **`describe_pr(pr_url)`**: Generates a full PR description (Title, Type, Summary, Walkthrough, Labels).
-   **`review_code(pr_url)`**: Performs a detailed code review, listing issues with severity and suggestions.
-   **`improve_code(pr_url)`**: Suggests code improvements and refactoring opportunities.
-   **`ask_pr(pr_url, question)`**: Answers specific questions about the PR.
-   **`update_changelog(pr_url)`**: Generates a changelog entry for the PR.
-   **`get_repo_structure(repo_url)`**: Returns the file structure of the repository.

## Directory Structure

```
pr-agent
├── .env
├── .gitignore
├── README.md
├── main.py
├── requirements.txt
├── run_agent.sh
├── src
│   ├── __init__.py
│   ├── __pycache__
│   ├── agents
│   │   ├── __pycache__
│   │   ├── base.py
│   │   └── specialized.py
│   ├── analyzer.py
│   ├── config.py
│   ├── github_provider.py
│   ├── graph.py
│   ├── prompts.py
│   ├── state.py
│   ├── toon_io.py
│   └── utils.py
├── tests
│   ├── test_functionality.py
│   └── verify_mcp.py
└── venv
```

## TOON Format

This project uses [TOON](https://github.com/toon-format/toon-python) for LLM outputs. TOON uses a compact table syntax for lists of objects, saving tokens compared to JSON.

**Example TOON Output:**
```toon
issues[2]{type,file,description}:
bug,main.py,Fix null pointer exception
style,utils.py,Add missing docstring
```
