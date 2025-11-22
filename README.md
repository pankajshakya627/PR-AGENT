# PR Agent with TOON Support

An intelligent, agentic system designed to automate and enhance Pull Request workflows. It leverages **LangGraph** for orchestration, **FastMCP** for tool exposure, and **TOON (Token Oriented Object Notation)** for efficient, structured LLM communication.

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
