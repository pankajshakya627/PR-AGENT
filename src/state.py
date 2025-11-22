from typing import TypedDict, List, Dict, Any, Optional, Literal

class PRAgentState(TypedDict):
    """State for the PR Agent system."""
    pr_requirements: str

    # GitHub Context
    github_token: Optional[str]
    pr_url: Optional[str]
    diff_content: Optional[str]
    pr_details: Optional[Dict[str, Any]]
    file_tree: Optional[List[str]]

    task_graph: Dict[str, List[str]]  # Task dependencies
    execution_mode: Literal["parallel", "sequential", "hybrid"]
    agent_results: Dict[str, Any]
    final_pr: Optional[Dict]
    errors: List[str]
