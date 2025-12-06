from typing import TypedDict, List, Dict, Any, Optional, Literal, Annotated
from operator import add

def merge_agent_results(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """
    Custom reducer to merge agent results without overwriting.
    
    Merges dictionaries recursively, concatenates lists, and preserves newer values
    for scalar types when conflicts occur.
    """
    if not left:
        return right
    if not right:
        return left
        
    merged = left.copy()
    for key, value in right.items():
        if key in merged:
            # If both are dicts, merge recursively
            if isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = {**merged[key], **value}
            # If both are lists, concatenate
            elif isinstance(merged[key], list) and isinstance(value, list):
                merged[key] = merged[key] + value
            else:
                # Otherwise, prefer newer value (right)
                merged[key] = value
        else:
            merged[key] = value
    return merged

class PRAgentState(TypedDict):
    """Enhanced state for the PR Agent system with custom reducers."""
    pr_requirements: str

    # GitHub Context
    github_token: Optional[str]
    pr_url: Optional[str]
    diff_content: Optional[str]
    pr_details: Optional[Dict[str, Any]]
    file_tree: Optional[List[str]]

    # Execution tracking
    task_graph: Dict[str, List[str]]  # Task dependencies
    execution_mode: Literal["parallel", "sequential", "hybrid"]
    
    # Accumulated results with custom merging
    agent_results: Annotated[Dict[str, Any], merge_agent_results]
    # Auto-concatenate errors from different nodes
    errors: Annotated[List[str], add]
    
    final_pr: Optional[Dict]

