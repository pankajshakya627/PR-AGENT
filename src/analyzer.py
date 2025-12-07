from typing import Dict, List
from langchain_core.prompts import ChatPromptTemplate
from src.config import get_llm_config
from src.prompts import TASK_DEPENDENCY_SYSTEM_PROMPT
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
        elif self.provider == "openrouter":
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=config["openrouter_model"],
                    base_url=config["openrouter_base_url"],
                    api_key=os.getenv("OPENROUTER_API_KEY"),
                    temperature=config["temperature"],
                    max_tokens=config["max_tokens"]
                )
            except ImportError:
                raise ImportError("langchain-openai is not installed. Please install it with: pip install langchain-openai")
            except Exception as e:
                raise ConnectionError(f"Failed to connect to OpenRouter: {e}")
        elif self.provider == "local":
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=config["local_model"],
                    base_url=config["local_base_url"],
                    api_key="not-required",
                    temperature=0.1,
                    streaming=True,
                    max_tokens=config["max_tokens"]
                )
            except ImportError:
                raise ImportError("langchain-openai is not installed. Please install it with: pip install langchain-openai")
            except Exception as e:
                raise ConnectionError(f"Failed to connect to local LLM at {config['local_base_url']}: {e}")
        elif self.provider == "groq":
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=config["groq_model"],
                    base_url=config["groq_base_url"],
                    api_key=os.getenv("GROQ_API_KEY"),
                    temperature=config["temperature"],
                    max_tokens=config["max_tokens"]
                )
            except ImportError:
                raise ImportError("langchain-openai is not installed. Please install it with: pip install langchain-openai")
            except Exception as e:
                raise ConnectionError(f"Failed to connect to Groq: {e}")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def analyze(self, requirements: str) -> Dict[str, List[str]]:
        """
        Analyzes requirements and returns a DAG of tasks.
        Output format: {"task_name": ["dependency1", "dependency2"]}
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", TASK_DEPENDENCY_SYSTEM_PROMPT),
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
