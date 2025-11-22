from typing import Dict, List
from langchain_core.prompts import ChatPromptTemplate
from src.config import get_llm_config
import json
import os

class TaskDependencyAnalyzer:
    """Analyzes PR requirements to determine task dependencies."""

    def __init__(self):
        config = get_llm_config()
        self.provider = config["provider"]
        
        if self.provider == "openai":
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=config["openai_model"],
                temperature=config["temperature"],
                max_tokens=config["max_tokens"]
            )
        elif self.provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
                self.llm = ChatAnthropic(
                    model=config["anthropic_model"],
                    temperature=config["temperature"],
                    max_tokens=config["max_tokens"]
                )
            except ImportError:
                raise ImportError("langchain-anthropic is not installed. Please install it or use OpenAI.")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def analyze(self, requirements: str) -> Dict[str, List[str]]:
        """
        Analyzes requirements and returns a DAG of tasks.
        Output format: {"task_name": ["dependency1", "dependency2"]}
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a project manager. Analyze the following PR requirements and identify the necessary tasks and their dependencies. Return the result as a JSON object where keys are task names (code_review, testing, documentation, security) and values are lists of dependencies."),
            ("user", "{requirements}")
        ])

        chain = prompt | self.llm
        response = await chain.ainvoke({"requirements": requirements})
        
        try:
            # Basic parsing, in a real scenario we'd use a structured output parser
            content = response.content
            # Find the first '{' and last '}' to extract JSON
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = content[start:end]
                return json.loads(json_str)
            else:
                # Fallback default
                return {
                    "code_review": [],
                    "testing": ["code_review"],
                    "documentation": [],
                    "security": ["code_review"]
                }
        except Exception as e:
            print(f"Error parsing dependency analysis: {e}")
            return {
                "code_review": [],
                "testing": ["code_review"],
                "documentation": [],
                "security": ["code_review"]
            }
