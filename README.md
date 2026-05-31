# 🤖 PR-Agent: Intelligent Pull Request Agent System

PR-Agent is an advanced AI-powered system that orchestrates multiple specialized agents to analyze, review, and document pull requests. It supports multiple interfaces including a FastMCP server, a Streamlit Web UI, and GitHub Actions CI/CD integration.

## 🏗️ System Architecture

```mermaid
graph TB
    Developer[Developer] -->|Push/Open PR| GitHub[GitHub/GitLab]
    GitHub -->|Webhook| Gateway[API Gateway]

    Gateway --> Orchestrator{PR Supervisor Agent}

    subgraph "Agent Squad (The Reviewers)"
        Orchestrator --> DescAgent[📝 Description Agent]
        Orchestrator --> ReviewAgent[👓 Code Review Agent]
        Orchestrator --> SecAgent[🔒 Security Agent]
        Orchestrator --> PerfAgent[🚀 Performance Agent]
        Orchestrator --> TestAgent[🧪 QA/Test Agent]

        ReviewAgent --Checks Style--> Linter[Pylint/Flake8]
        SecAgent --Scans--> SAST[Bandit]
        PerfAgent --Profiles--> Profiler[Complexity Analyzer]
    end

    subgraph "Knowledge Base"
        VectorDB[(Codebase Context)]
        Rules[Style Guide / Best Practices]
    end

    DescAgent & ReviewAgent & SecAgent --> VectorDB
    ReviewAgent --> Rules

    Orchestrator -->|Post Comments| GitHub
```

## 🔒 Multi-Tenant Security & 🧠 Three-Tiered Cognitive Memory Architecture

PR-Agent implements an enterprise-grade multi-tenant security architecture and a **Three-Tiered Cognitive Memory Architecture** to guarantee absolute data isolation, high-performance context processing, and smart episodic context retrieval:

### 1. 🔒 Enterprise Multi-Tenant Security & Isolation

* **Contextvars-Based Propagation**: Uses Python `contextvars` to safely propagate `tenant_id` across asynchronous context switches and concurrent threads.
* **Tenant-Scoped Caching**: An isolated caching mechanism (`_tenant_cache`) that automatically scopes cache keys strictly by the active tenant ID to prevent any potential cross-tenant cache pollution.
* **Structured Auditing**: Formats and logs every tenant action (e.g., agent runs, cache queries) into `config/tenant_audit.log` for transparency and compliance.
* **Prompt Injection Protection**: Dynamic instruction hierarchy overrides that bind prompt execution scopes strictly within the active tenant boundaries.

### 2. 🧠 Three-Tiered Cognitive Memory Architecture

* **Tier 1: Working Memory (L1 - Immediate Focus)**: Employs high-density KV Cache prefix optimization and sliding-window diff slicing (`L1WorkingMemory.optimize_diff_context`) to fit large files into the active context window and prevent token limit overflows.
* **Tier 2: Episodic Memory (L2 - Events & Trajectories)**: Implements experience replay per tenant. Automatically logs execution results of successful agent trajectories and allows `PRQuestionsAgent` to retrieve past episodes to answer complex questions about past turns.
* **Tier 3: Semantic Memory (L3 - Facts & Rules)**: Enforces persistent style guidelines and custom team rules per tenant. Team rules are registered dynamically and injected into the LLM system prompt for strict guidelines enforcement.

### 3. ⚙️ Active Configuration & Usage

#### Setting/Managing Tenant Isolation

By default, the supervisor orchestrator and all specialized agents resolve the current tenant scope automatically based on the active thread or async task `contextvars`. You can manage it programmatically or via environment variables:

* **Environment Variable Override**: Set the primary tenant context using `DEFAULT_TENANT_ID`.

  ```bash
  export DEFAULT_TENANT_ID="enterprise_client_a"
  ```

* **Programmatic Assignment**: Scope agent executions dynamically within specific tenant namespaces in your Python code:

  ```python
  from src.tenant import set_current_tenant_id, tenant_scoped

  # Programmatic propagation across execution contexts
  set_current_tenant_id("customer_account_b")
  ```

#### Registering Semantic Style Guidelines (L3)

You can append custom guidelines or business rules directly into the L3 Semantic Memory layer per tenant to guide review logic:

```python
from src.memory import L3SemanticMemory
from src.tenant import set_current_tenant_id

set_current_tenant_id("engineering_team_x")
L3SemanticMemory.register_rule("All public REST endpoints must include explicit OAuth decorators.")
```

## 📂 Directory Structure

```plaintext
pr-agent/
├── 📂 .github/              # GitHub Actions & Dependabot
│   ├── workflows/           # CI/CD Workflows
│   │   └── security-scan.yml
│   └── dependabot.yml       # Dependency updates
├── 📂 docs/                 # Documentation
│   ├── CICD_SETUP.md        # GitHub Actions Setup
│   ├── PORTABLE_WORKFLOW.md # Portable usage guide
│   ├── QUICKSTART.md        # Quick start guide
│   ├── SECURITY.md          # Security policy
│   └── STREAMLIT_FORMATTING.md
├── 📂 src/                  # Source Code
│   ├── 📂 agents/           # Specialized LLM Agents
│   │   ├── base.py          # Base agent class
│   │   └── specialized.py   # All agent implementations
│   ├── analyzer.py          # Task dependency analyzer
│   ├── auth.py              # Authentication logic
│   ├── config.py            # Configuration management
│   ├── github_commenter.py  # GitHub PR commenting
│   ├── github_provider.py   # GitHub API interaction
│   ├── graph.py             # LangGraph orchestration
│   ├── memory.py            # Three-tiered cognitive memory system
│   ├── prompts.py           # Centralized LLM prompts
│   ├── schemas.py           # Pydantic validation schemas
│   ├── state.py             # Agent state definitions
│   ├── tenant.py            # Async-safe multi-tenant isolation
│   ├── tracing.py           # Optional Langfuse tracing integration
│   └── utils.py             # Utility functions
├── 📂 tests/                # Test suite
│   ├── test_functionality.py
│   └── verify_mcp.py
├── .env.example             # Environment variables template
├── cli.py                   # CLI Entry point
├── main.py                  # FastMCP Server Entry point
├── streamlit_app.py         # Streamlit Web UI Entry point
├── run_streamlit.sh         # Streamlit launcher script
├── run_agent.sh             # Agent launcher script
└── requirements.txt         # Python dependencies
```

## 🔄 How It Works

### 1. 🖥️ Streamlit Web UI (Interactive Mode)

**Interaction:** Users log in via the Web UI and interact directly with agents.

- **Architecture:** The Streamlit app imports agent classes (e.g., `CodeReviewAgent`) directly from `src.agents`.
- **Flow:** User Input → Streamlit App → `Agent.execute()` → LLM → Streamlit UI

#### 🔐 Authentication Features

| Feature             | Description                                                    |
| ------------------- | -------------------------------------------------------------- |
| **Login**           | Secure login with username/password using bcrypt hashing       |
| **Registration**    | New user registration with email and password validation       |
| **Forgot Password** | Email verification code flow for secure password reset         |
| **Change Password** | Logged-in users can update their password via sidebar expander |

**Security:**

- Passwords hashed using `bcrypt` with salt rounds (12)
- Session managed via encrypted cookies (configurable expiry: 30 days default)
- User credentials stored in `config/auth_config.yaml`
- Uses `streamlit-authenticator` library for secure authentication

### 2. 🔌 FastMCP Server (Assistant Mode)

**Interaction:** Designed for AI Assistants (like Claude Desktop) or IDEs (Cursor).

- **Architecture:** `main.py` uses `fastmcp` to expose functions as standardized tools.
- **Flow:** Claude/IDE → MCP Protocol → `main.py` → `app.ainvoke()` → Agents → Response
- **Tools:** Exposes `review_pr`, `describe_pr`, `ask_pr`, etc.

### 3. 📈 Langfuse Tracing & Monitoring

PR-Agent can emit LangChain/LangGraph traces to Langfuse for monitoring LLM calls, fallbacks, latency, token usage, and per-tenant agent behavior. Tracing is optional and stays disabled unless Langfuse credentials are configured.

```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
# PR-Agent accepts LANGFUSE_BASE_URL and maps it to the SDK's LANGFUSE_HOST.
export LANGFUSE_BASE_URL="https://cloud.langfuse.com"
# Optional explicit switch. Credentials alone also enable tracing.
export LANGFUSE_ENABLED=true
```

Each specialized agent invocation is traced with:

- `langfuse_user_id`: active `tenant_id`
- `langfuse_session_id`: PR URL, commit URL, or branch comparison key
- tags: `pr-agent` plus the agent run name
- metadata: tenant, agent name, and active LLM provider

This follows the Langfuse tracing model of one trace per system invocation and session grouping around the PR under review.

### 4. 🚀 GitHub Actions (CI/CD Mode)

**Interaction:** Validates code automatically on every Pull Request.

- **Architecture:** `cli.py` is invoked by the GitHub Action container.
- **Flow:** PR Event → GitHub Action → `cli.py` → `GitHubProvider` → Agents → PR Comment
- **Triggers:** `opened`, `synchronize`, `reopened` events or manual `workflow_dispatch`.

### 5. 🤖 Specialized Agent Squad

The system deploys a squad of specialized agents, each acting as a "Staff Engineer" in their domain:

| Agent                 | Persona           | Responsibilities                                           | Tools Integrated    |
| --------------------- | ----------------- | ---------------------------------------------------------- | ------------------- |
| **Code Review Agent** | Senior SWE        | General code quality, style, and logic checks.             | `pylint`, `flake8`  |
| **Security Agent**    | InfoSec Lead      | Vulnerability scanning (SQLi, Secrets, XSS).               | `bandit` (SAST)     |
| **Performance Agent** | SRE / Perf Expert | Identifying N+1 queries, complexity, and resource leaks.   | Complexity Analyzer |
| **Test Agent**        | QA Architect      | Verifying test coverage and suggesting missing test cases. | -                   |
| **Description Agent** | Technical Writer  | generating comprehensive PR descriptions and titles.       | -                   |

**Hybrid Neuro-Symbolic Analysis**:
Agents don't just "guess" based on the diff. They run actual static analysis tools (like `pylint` and `bandit`) on the code, ingest the structured output, and then use the LLM to interpret the results and provide actionable fixes.

### 6. 🧠 Knowledge Base (RAG)

_Note: This component is in active development._

The system utilizes a **Vector Database** (VectorDB) to provide agents with broader codebase context, moving beyond single-file analysis.

- **Purpose**: Enables agents to understand project-specific patterns, existing utilities, and architectural standards.
- **Workflow**:
  1. Codebase is indexed into a VectorDB (e.g., Chroma/Pinecone).
  2. Agents query the DB for relevant snippets (e.g., "Find all auth decorators").
  3. Retrieved context is injected into the prompt (RAG).
- **Style Guide**: A dedicated "Rules DB" ensures code adheres to team-specific conventions.

## 📚 Documentation

| Document                                           | Description                      |
| -------------------------------------------------- | -------------------------------- |
| [**Quick Start**](docs/QUICKSTART.md)              | Get up and running in minutes    |
| [**CI/CD Setup**](docs/CICD_SETUP.md)              | Integrate with GitHub Actions    |
| [**Portable Workflow**](docs/PORTABLE_WORKFLOW.md) | Drop-in workflow for any repo    |
| [**Security Policy**](docs/SECURITY.md)            | Vulnerability reporting & policy |

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- API Key (OpenAI, Anthropic, Groq, or OpenRouter)

### Installation

1. **Clone & Install**

   ```bash
   git clone https://github.com/pankajshakya627/PR-AGENT.git
   cd PR-AGENT
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Config**

   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run Streamlit UI**

   ```bash
   ./run_streamlit.sh
   # Opens http://localhost:8501
   ```

4. **Run MCP Server**
   ```bash
   python main.py
   # Starts FastMCP server
   ```

## 🛡️ License

Proprietary License. See [LICENSE.md](LICENSE.md) for details.
