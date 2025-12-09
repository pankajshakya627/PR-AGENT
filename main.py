"""PR-Agent MCP Server - Provides tools for PR analysis via FastMCP."""
from typing import Dict, Any, List

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP  # noqa: E402

# Check PyGithub is installed
try:
    import importlib.util
    if importlib.util.find_spec("github") is None:
        raise ImportError()
except ImportError:
    print("\n❌ Error: 'PyGithub' not found.")
    print("Please ensure you are running in the virtual environment:")
    print("  source venv/bin/activate")
    print("  python main.py")
    print("OR")
    print("  ./venv/bin/python main.py\n")
    exit(1)

from src.graph import app  # noqa: E402
from src.config import LLM_CONFIG, AGENT_CONFIG  # noqa: E402
from src.prompts import (  # noqa: E402
    CODE_REVIEW_SYSTEM_PROMPT,
    PR_DESCRIPTION_SYSTEM_PROMPT,
    CODE_IMPROVEMENT_SYSTEM_PROMPT,
    PR_QUESTIONS_SYSTEM_PROMPT,
    CHANGELOG_SYSTEM_PROMPT,
    TASK_DEPENDENCY_SYSTEM_PROMPT,
    COMMIT_PR_GENERATOR_SYSTEM_PROMPT
)

mcp = FastMCP("pr-agent-system")

@mcp.resource("config://llm")
def get_llm_config() -> str:
    """Returns the current LLM configuration."""
    # Return a sanitized version (no API keys if they were there, though currently they are env vars)
    return str(LLM_CONFIG)

@mcp.resource("config://agent")
def get_agent_config() -> str:
    """Returns the current agent configuration."""
    return str(AGENT_CONFIG)

@mcp.prompt()
def code_review_prompt() -> str:
    """Returns the system prompt for the Code Review Agent."""
    return CODE_REVIEW_SYSTEM_PROMPT

@mcp.prompt()
def pr_description_prompt() -> str:
    """Returns the system prompt for the PR Description Agent."""
    return PR_DESCRIPTION_SYSTEM_PROMPT

@mcp.prompt()
def code_improvement_prompt() -> str:
    """Returns the system prompt for the Code Improvement Agent."""
    return CODE_IMPROVEMENT_SYSTEM_PROMPT

@mcp.prompt()
def pr_questions_prompt() -> str:
    """Returns the system prompt for the PR Questions Agent."""
    return PR_QUESTIONS_SYSTEM_PROMPT

@mcp.prompt()
def changelog_prompt() -> str:
    """Returns the system prompt for the Changelog Agent."""
    return CHANGELOG_SYSTEM_PROMPT

@mcp.prompt()
def task_dependency_prompt() -> str:
    """Returns the system prompt for the Task Dependency Analyzer."""
    return TASK_DEPENDENCY_SYSTEM_PROMPT

@mcp.prompt()
def commit_pr_generator_prompt() -> str:
    """Returns the system prompt for the Commit-Based PR Generator."""
    return COMMIT_PR_GENERATOR_SYSTEM_PROMPT


@mcp.tool()
async def create_pull_request(requirements: str) -> Dict[str, Any]:
    """
    Creates a pull request based on the provided requirements.
    
    Args:
        requirements: A string describing the PR requirements.
        
    Returns:
        A dictionary containing the generated PR details.
    """
    initial_state = {
        "pr_requirements": requirements,
        "task_graph": {},
        "execution_mode": "hybrid",
        "agent_results": {},
        "final_pr": None,
        "errors": []
    }
    
    result = await app.ainvoke(initial_state)
    return result.get("final_pr", {})

@mcp.tool()
async def analyze_dependencies(tasks: List[str]) -> Dict[str, List[str]]:
    """
    Analyzes task dependencies.
    
    Args:
        tasks: A list of task names.
        
    Returns:
        A dictionary representing the dependency graph.
    """
    # This is a simplified exposure of the analyzer logic
    # In a real scenario, we might want to reuse the analyzer instance
    from src.analyzer import TaskDependencyAnalyzer
    analyzer = TaskDependencyAnalyzer()
    # For this tool, we might need to adapt the input/output
    # But for now, let's just return a placeholder or reuse the analyze method if applicable
    return {"status": "Not fully implemented for direct tool access yet"}

@mcp.tool()
async def review_pr(pr_url: str) -> Dict[str, Any]:
    """
    Performs a code review on a specific Pull Request.
    
    Args:
        pr_url: The URL of the Pull Request to review.
        
    Returns:
        A dictionary containing the code review results.
    """
    from src.agents.specialized import CodeReviewAgent
    from src.state import PRAgentState
    
    # Create a minimal state for the agent
    state: PRAgentState = {
        "pr_requirements": "",
        "pr_url": pr_url,
        "github_token": None, # Will be loaded from env by provider
        "agent_results": {},
        "execution_mode": "sequential",
        "task_graph": {},
        "final_pr": None,
        "errors": []
    }
    
    agent = CodeReviewAgent()
    result = await agent.execute(state)
    return result.get("code_review", {})

@mcp.tool()
async def describe_pr(pr_url: str) -> Dict[str, Any]:
    """Generates a comprehensive description for a Pull Request."""
    from src.agents.specialized import PRDescriptionAgent
    from src.state import PRAgentState
    
    state: PRAgentState = {"pr_requirements": "", "pr_url": pr_url, "github_token": None, "agent_results": {}, "execution_mode": "sequential", "task_graph": {}, "final_pr": None, "errors": []}
    agent = PRDescriptionAgent()
    result = await agent.execute(state)
    return result.get("pr_description", {})

@mcp.tool()
async def improve_code(pr_url: str) -> Dict[str, Any]:
    """Suggests code improvements for a Pull Request."""
    from src.agents.specialized import CodeImprovementAgent
    from src.state import PRAgentState
    
    state: PRAgentState = {"pr_requirements": "", "pr_url": pr_url, "github_token": None, "agent_results": {}, "execution_mode": "sequential", "task_graph": {}, "final_pr": None, "errors": []}
    agent = CodeImprovementAgent()
    result = await agent.execute(state)
    return result.get("code_improvements", {})

@mcp.tool()
async def ask_pr(pr_url: str, question: str) -> str:
    """Asks a question about a Pull Request."""
    from src.agents.specialized import PRQuestionsAgent
    from src.state import PRAgentState
    
    state: PRAgentState = {"pr_requirements": "", "pr_url": pr_url, "question": question, "github_token": None, "agent_results": {}, "execution_mode": "sequential", "task_graph": {}, "final_pr": None, "errors": []}
    agent = PRQuestionsAgent()
    result = await agent.execute(state)
    return result.get("answer", "No answer generated.")

@mcp.tool()
async def update_changelog(pr_url: str) -> str:
    """Generates a changelog entry for a Pull Request."""
    from src.agents.specialized import ChangelogAgent
    from src.state import PRAgentState
    
    state: PRAgentState = {"pr_requirements": "", "pr_url": pr_url, "github_token": None, "agent_results": {}, "execution_mode": "sequential", "task_graph": {}, "final_pr": None, "errors": []}
    agent = ChangelogAgent()
    result = await agent.execute(state)
    return result.get("changelog_entry", "")

@mcp.tool()
async def generate_pr_from_commit(commit_url: str) -> Dict[str, Any]:
    """
    Generates a PR title and detailed description from a GitHub commit URL.
    
    Args:
        commit_url: The URL of the commit (e.g., https://github.com/owner/repo/commit/abc123)
        
    Returns:
        A dictionary containing the generated PR title and description in markdown format.
    """
    from src.agents.specialized import CommitPRGeneratorAgent
    from src.state import PRAgentState
    
    state: PRAgentState = {
        "pr_requirements": "",
        "commit_url": commit_url,
        "github_token": None,
        "agent_results": {},
        "execution_mode": "sequential",
        "task_graph": {},
        "final_pr": None,
        "errors": []
    }
    agent = CommitPRGeneratorAgent()
    result = await agent.execute(state)
    return result.get("pr_from_commit", {})


if __name__ == "__main__":
    mcp.run()
