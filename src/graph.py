import asyncio
import re
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from src.state import PRAgentState
from src.analyzer import TaskDependencyAnalyzer
from src.agents.specialized import CodeReviewAgent, TestingAgent, DocumentationAgent, SecurityAgent
from src.github_provider import GitHubProvider
from src.utils import format_file_tree

# Initialize agents
analyzer = TaskDependencyAnalyzer()
agents = {
    "code_review": CodeReviewAgent(),
    "testing": TestingAgent(),
    "documentation": DocumentationAgent(),
    "security": SecurityAgent(),
}

async def context_loader(state: PRAgentState) -> Dict[str, Any]:
    """
    Loads context from GitHub based on the PR URL.
    """
    requirements = state.get("pr_requirements", "")
    
    # Try to find a URL in the requirements
    url_match = re.search(r"https://github\.com/[\w-]+/[\w-]+/pull/\d+", requirements)
    pr_url = url_match.group(0) if url_match else state.get("pr_url")
    
    updates = {}
    if pr_url:
        updates["pr_url"] = pr_url
        try:
            github = GitHubProvider(token=state.get("github_token"))
            
            # Fetch PR details
            details = github.get_pr_details(pr_url)
            updates["pr_details"] = details
            
            # Fetch File Tree
            files = github.get_files_in_repo(pr_url)
            updates["file_tree"] = files
            
            # Fetch Diff (optional here, agents might fetch it themselves, but good to have)
            # diff = github.get_pr_diff(pr_url)
            # updates["diff_content"] = diff
            
        except Exception as e:
            print(f"Error loading context: {e}")
            updates["errors"] = [str(e)]
            
    return updates

async def requirement_analyzer(state: PRAgentState) -> Dict[str, Any]:
    """Analyzes requirements and determines task dependencies."""
    requirements = state["pr_requirements"]
    task_graph = await analyzer.analyze(requirements)
    
    # Simple logic to determine execution mode
    # In a real system, this would be more sophisticated based on the graph structure
    mode = "hybrid" 
    
    return {"task_graph": task_graph, "execution_mode": mode}

async def parallel_executor(state: PRAgentState) -> Dict[str, Any]:
    """Executes independent tasks in parallel."""
    # For simplicity, let's assume we run all agents that have no dependencies
    tasks_to_run = []
    for name, agent in agents.items():
        deps = agent.get_dependencies()
        if not deps:
            tasks_to_run.append(agent.execute(state))
    
    results = await asyncio.gather(*tasks_to_run)
    
    # Aggregate results
    new_results = {}
    for res in results:
        new_results.update(res)
        
    return {"agent_results": new_results}

async def sequential_executor(state: PRAgentState) -> Dict[str, Any]:
    """Executes dependent tasks sequentially."""
    # For simplicity, let's run agents that HAVE dependencies
    # In a real hybrid model, we'd topologically sort the graph
    current_results = state.get("agent_results", {})
    
    for name, agent in agents.items():
        deps = agent.get_dependencies()
        if deps:
            # Check if dependencies are met
            # For now, just run them
            res = await agent.execute(state)
            current_results.update(res)
            
    return {"agent_results": current_results}

async def pr_generator(state: PRAgentState) -> Dict[str, Any]:
    """Generates the final PR."""
    results = state.get("agent_results", {})
    
    # Construct final PR object
    final_pr = {
        "title": "Generated PR",
        "description": f"PR generated based on requirements: {state['pr_requirements']}",
        "changes": results
    }
    return {"final_pr": final_pr}

# Define the graph
workflow = StateGraph(PRAgentState)

workflow.add_node("context_loader", context_loader)
workflow.add_node("requirement_analyzer", requirement_analyzer)
workflow.add_node("parallel_executor", parallel_executor)
workflow.add_node("sequential_executor", sequential_executor)
workflow.add_node("pr_generator", pr_generator)

workflow.set_entry_point("context_loader")

workflow.add_edge("context_loader", "requirement_analyzer")
workflow.add_edge("requirement_analyzer", "parallel_executor")
workflow.add_edge("parallel_executor", "sequential_executor")
workflow.add_edge("sequential_executor", "pr_generator")
workflow.add_edge("pr_generator", END)

app = workflow.compile()
