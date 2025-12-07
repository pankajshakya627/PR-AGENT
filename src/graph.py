import asyncio
import logging
import re
from typing import Dict, Any, List, Literal
from collections import deque
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.state import PRAgentState
from src.analyzer import TaskDependencyAnalyzer
from src.agents.specialized import CodeReviewAgent, TestingAgent, DocumentationAgent, SecurityAgent
from src.github_provider import GitHubProvider
from src.utils import format_file_tree
from src.config import AGENT_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize agents
analyzer = TaskDependencyAnalyzer()
agents = {
    "code_review": CodeReviewAgent(),
    "testing": TestingAgent(),
    "documentation": DocumentationAgent(),
    "security": SecurityAgent(),
}

# ============================================================================
# Helper Functions
# ============================================================================

def topological_sort(task_graph: Dict[str, List[str]]) -> List[List[str]]:
    """
    Performs topological sort on task graph to identify execution levels.
    
    Returns a list of lists, where each inner list contains tasks that can
    be executed in parallel (have no dependencies on each other).
    
    Raises:
        ValueError: If cyclic dependencies are detected.
    """
    from collections import defaultdict
    
    # Calculate in-degrees using defaultdict for better readability
    in_degree = defaultdict(int)
    for task in task_graph:
        in_degree[task] = 0  # Initialize all tasks
    
    for task, deps in task_graph.items():
        for dep in deps:
            if dep in task_graph:
                in_degree[dep] += 1
    
    # Find tasks with no dependencies (in-degree = 0)
    queue = deque([task for task, degree in in_degree.items() if degree == 0])
    levels = []
    processed_count = 0
    
    while queue:
        # All tasks in current level can execute in parallel
        current_level = list(queue)
        levels.append(current_level)
        processed_count += len(current_level)
        queue.clear()
        
        # Process current level
        for task in current_level:
            # Reduce in-degree for dependent tasks
            for next_task in task_graph:
                if task in task_graph[next_task]:
                    in_degree[next_task] -= 1
                    if in_degree[next_task] == 0:
                        queue.append(next_task)
    
    # Cycle detection: if we haven't processed all tasks, there's a cycle
    if processed_count < len(task_graph):
        unprocessed = [t for t in task_graph if t not in [task for level in levels for task in level]]
        raise ValueError(f"Cyclic dependencies detected in task graph. Affected tasks: {unprocessed}")
    
    return levels

async def retry_with_backoff(func, *args, max_retries=None, timeout=None, **kwargs):
    """
    Wrapper to retry async functions with exponential backoff.
    
    Uses configuration from AGENT_CONFIG if not specified.
    """
    max_retries = max_retries or AGENT_CONFIG.get("max_retries", 2)
    timeout = timeout or AGENT_CONFIG.get("timeout_per_agent", 300)
    
    for attempt in range(max_retries + 1):
        try:
            # Apply timeout
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.error(f"Timeout after {timeout}s on attempt {attempt + 1}/{max_retries + 1}")
            if attempt == max_retries:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            logger.error(f"Error on attempt {attempt + 1}/{max_retries + 1}: {str(e)}")
            if attempt == max_retries:
                raise
            await asyncio.sleep(2 ** attempt)

# ============================================================================
# Node Functions
# ============================================================================

async def context_loader(state: PRAgentState) -> Dict[str, Any]:
    """
    Loads context from GitHub based on the PR URL.
    Includes error handling and loads diff content.
    """
    logger.info("Starting context_loader node")
    requirements = state.get("pr_requirements", "")
    
    # Try to find a URL in the requirements
    url_match = re.search(r"https://github\.com/[\w-]+/[\w-]+/pull/\d+", requirements)
    pr_url = url_match.group(0) if url_match else state.get("pr_url")
    
    updates = {}
    errors = []
    
    if pr_url:
        updates["pr_url"] = pr_url
        try:
            github = GitHubProvider(token=state.get("github_token"))
            
            # Fetch PR details
            logger.info(f"Fetching PR details for {pr_url}")
            details = github.get_pr_details(pr_url)
            updates["pr_details"] = details
            
            # Fetch File Tree
            logger.info("Fetching file tree")
            files = github.get_files_in_repo(pr_url)
            updates["file_tree"] = files
            
            # Fetch Diff content (load once, share via state)
            logger.info("Fetching diff content")
            diff = github.get_pr_diff(pr_url)
            updates["diff_content"] = diff
            
            logger.info("Context loaded successfully")
            
        except Exception as e:
            error_msg = f"Error loading context: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    else:
        error_msg = "No PR URL found in requirements or state"
        logger.error(error_msg)
        errors.append(error_msg)
    
    if errors:
        updates["errors"] = errors
            
    return updates

async def requirement_analyzer(state: PRAgentState) -> Dict[str, Any]:
    """
    Analyzes requirements and determines task dependencies and execution mode.
    Now actually determines mode based on task graph structure.
    """
    logger.info("Starting requirement_analyzer node")
    requirements = state["pr_requirements"]
    
    try:
        task_graph = await retry_with_backoff(analyzer.analyze, requirements)
        logger.info(f"Task graph generated: {task_graph}")
        
        # Determine execution mode based on task graph structure
        if not task_graph:
            mode = "sequential"
        else:
            # Check if there are any dependencies
            has_dependencies = any(deps for deps in task_graph.values())
            
            if not has_dependencies:
                # All tasks independent -> parallel
                mode = "parallel"
            elif all(deps for deps in task_graph.values()):
                # All tasks have dependencies -> sequential
                mode = "sequential"
            else:
                # Mix of independent and dependent -> hybrid
                mode = "hybrid"
        
        logger.info(f"Determined execution mode: {mode}")
        return {"task_graph": task_graph, "execution_mode": mode}
        
    except Exception as e:
        error_msg = f"Error in requirement analysis: {str(e)}"
        logger.error(error_msg)
        # Fallback to simple sequential mode
        return {
            "task_graph": {},
            "execution_mode": "sequential",
            "errors": [error_msg]
        }

async def parallel_executor(state: PRAgentState) -> Dict[str, Any]:
    """
    Executes independent tasks in parallel using topological sort.
    Now properly uses task_graph from state.
    """
    logger.info("Starting parallel_executor node")
    task_graph = state.get("task_graph", {})
    
    if not task_graph:
        logger.warning("No task graph available, skipping parallel execution")
        return {}
    
    # Get tasks with no dependencies (first level from topological sort)
    sorted_levels = topological_sort(task_graph)
    if not sorted_levels:
        logger.warning("No tasks to execute in parallel")
        return {}
    
    # Execute first level (tasks with no dependencies) in parallel
    first_level_tasks = sorted_levels[0]
    logger.info(f"Executing {len(first_level_tasks)} tasks in parallel: {first_level_tasks}")
    
    tasks_to_run = []
    for task_name in first_level_tasks:
        if task_name in agents:
            agent = agents[task_name]
            logger.info(f"Adding {task_name} to parallel execution")
            tasks_to_run.append(retry_with_backoff(agent.execute, state))
    
    if not tasks_to_run:
        logger.warning("No valid agents found for parallel execution")
        return {}
    
    # Execute in parallel with error handling
    results = await asyncio.gather(*tasks_to_run, return_exceptions=True)
    
    # Aggregate results and handle errors
    new_results = {}
    errors = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            error_msg = f"Parallel task {first_level_tasks[i]} failed: {str(result)}"
            logger.error(error_msg)
            errors.append(error_msg)
        else:
            new_results.update(result)
            logger.info(f"Parallel task completed: {first_level_tasks[i]}")
    
    updates = {"agent_results": new_results}
    if errors:
        updates["errors"] = errors
    
    return updates

async def sequential_executor(state: PRAgentState) -> Dict[str, Any]:
    """
    Executes dependent tasks sequentially, checking dependencies are met.
    Now properly verifies dependencies before execution.
    """
    logger.info("Starting sequential_executor node")
    task_graph = state.get("task_graph", {})
    current_results = state.get("agent_results", {})
    
    if not task_graph:
        logger.warning("No task graph available, skipping sequential execution")
        return {}
    
    # Get all levels from topological sort
    sorted_levels = topological_sort(task_graph)
    
    # Skip first level (already executed in parallel)
    if len(sorted_levels) > 1:
        remaining_levels = sorted_levels[1:]
    else:
        logger.info("No additional levels to execute sequentially")
        return {}
    
    errors = []
    
    # Execute each remaining level
    for level_idx, level_tasks in enumerate(remaining_levels, start=1):
        logger.info(f"Executing level {level_idx}: {level_tasks}")
        
        for task_name in level_tasks:
            if task_name not in agents:
                logger.warning(f"Agent {task_name} not found, skipping")
                continue
            
            agent = agents[task_name]
            
            # Check if dependencies are met
            dependencies = task_graph.get(task_name, [])
            missing_deps = [dep for dep in dependencies if dep not in current_results]
            
            if missing_deps:
                error_msg = f"Cannot execute {task_name}: missing dependencies {missing_deps}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
            
            # Execute agent with retry
            try:
                logger.info(f"Executing {task_name}")
                result = await retry_with_backoff(agent.execute, state)
                current_results.update(result)
                logger.info(f"Completed {task_name}")
            except Exception as e:
                error_msg = f"Sequential task {task_name} failed: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
    
    updates = {"agent_results": current_results}
    if errors:
        updates["errors"] = errors
    
    return updates

async def pr_generator(state: PRAgentState) -> Dict[str, Any]:
    """Generates the final PR from aggregated results."""
    logger.info("Starting pr_generator node")
    results = state.get("agent_results", {})
    
    # Construct final PR object
    final_pr = {
        "title": "Generated PR",
        "description": f"PR generated based on requirements: {state['pr_requirements']}",
        "changes": results
    }
    
    logger.info("PR generation complete")
    return {"final_pr": final_pr}

# ============================================================================
# Router Functions
# ============================================================================

def route_execution(state: PRAgentState) -> Literal["parallel_executor", "sequential_executor", "pr_generator"]:
    """
    Routes workflow based on execution mode.
    
    - parallel: Only execute parallel_executor, skip sequential
    - sequential: Skip parallel, only execute sequential  
    - hybrid: Execute both parallel then sequential
    """
    mode = state.get("execution_mode", "hybrid")
    logger.info(f"Routing based on execution mode: {mode}")
    
    if mode == "parallel":
        # Only parallel execution, skip sequential
        return "parallel_executor"
    elif mode == "sequential":
        # Only sequential execution
        return "sequential_executor"
    else:  # hybrid
        # Execute both: parallel first
        return "parallel_executor"

def route_after_parallel(state: PRAgentState) -> Literal["sequential_executor", "pr_generator"]:
    """Route after parallel execution in hybrid mode."""
    mode = state.get("execution_mode", "hybrid")
    
    if mode == "hybrid":
        # Continue to sequential executor
        return "sequential_executor"
    else:
        # Skip to PR generation
        return "pr_generator"

# ============================================================================
# Graph Construction
# ============================================================================

# Initialize checkpointer for state persistence
memory = MemorySaver()

# Define the graph
workflow = StateGraph(PRAgentState)

# Add nodes
workflow.add_node("context_loader", context_loader)
workflow.add_node("requirement_analyzer", requirement_analyzer)
workflow.add_node("parallel_executor", parallel_executor)
workflow.add_node("sequential_executor", sequential_executor)
workflow.add_node("pr_generator", pr_generator)

# Set entry point
workflow.set_entry_point("context_loader")

# Add edges
workflow.add_edge("context_loader", "requirement_analyzer")

# Conditional routing based on execution mode
workflow.add_conditional_edges(
    "requirement_analyzer",
    route_execution,
    {
        "parallel_executor": "parallel_executor",
        "sequential_executor": "sequential_executor",
        "pr_generator": "pr_generator"
    }
)

# Route after parallel execution
workflow.add_conditional_edges(
    "parallel_executor",
    route_after_parallel,
    {
        "sequential_executor": "sequential_executor",
        "pr_generator": "pr_generator"
    }
)

# Always go to PR generator after sequential
workflow.add_edge("sequential_executor", "pr_generator")
workflow.add_edge("pr_generator", END)

# Compile with checkpointer for state persistence
app = workflow.compile(checkpointer=memory)

logger.info("LangGraph workflow compiled successfully with state persistence")
