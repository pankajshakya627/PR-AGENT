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

    async def _run_tool(self, command: List[str], cwd: str = None) -> str:
        """
        Safely executes a shell command and returns the output.
        
        Args:
            command: List of command arguments.
            cwd: Working directory for execution.
            
        Returns:
            Combined stdout and stderr.
        """
        import asyncio
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            stdout, stderr = await process.communicate()
            
            output = ""
            if stdout:
                output += f"Output:\n{stdout.decode().strip()}\n"
            if stderr:
                output += f"Errors:\n{stderr.decode().strip()}\n"
                
            if process.returncode != 0:
                logger.warning(f"Command {' '.join(command)} failed with code {process.returncode}")
                # We return output even on failure as tools like linters return non-zero exit codes for issues
                
            return output
        except Exception as e:
            logger.error(f"Failed to execute command {' '.join(command)}: {e}")
            return f"Error executing tool: {e}"
