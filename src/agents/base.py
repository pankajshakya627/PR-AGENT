from abc import ABC, abstractmethod
from typing import Dict, List, Any
from src.state import PRAgentState

class BaseAgent(ABC):
    """Abstract base class for all agents."""

    @abstractmethod
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        """Executes the agent's task."""
        pass

    @abstractmethod
    async def validate_input(self, context: PRAgentState) -> bool:
        """Validates the input context."""
        pass

    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """Returns a list of task dependencies."""
        pass
