from typing import Dict, Any, List
from src.agents.base import BaseAgent
from src.state import PRAgentState
from src.github_provider import GitHubProvider
from src.config import get_llm_config
from src.toon_io import to_toon, from_toon
from langchain_core.prompts import ChatPromptTemplate
import json
import os
from src.prompts import (
    CODE_REVIEW_SYSTEM_PROMPT, CODE_REVIEW_USER_PROMPT,
    PR_DESCRIPTION_SYSTEM_PROMPT, PR_DESCRIPTION_USER_PROMPT,
    CODE_IMPROVEMENT_SYSTEM_PROMPT, CODE_IMPROVEMENT_USER_PROMPT,
    PR_QUESTIONS_SYSTEM_PROMPT, PR_QUESTIONS_USER_PROMPT,
    CHANGELOG_SYSTEM_PROMPT, CHANGELOG_USER_PROMPT
)

class BaseLLMAgent(BaseAgent):
    def __init__(self):
        config = get_llm_config()
        self.provider = config["provider"]
        
        if self.provider == "openai":
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=config["openai_model"],
                api_key=os.getenv("OPENAI_API_KEY"),
                temperature=0.2,
                max_tokens=config["max_tokens"]
            )
        elif self.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            self.llm = ChatAnthropic(
                model=config["anthropic_model"],
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                temperature=0.2,
                max_tokens=config["max_tokens"]
            )
        elif self.provider == "openrouter":
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=config["openrouter_model"],
                base_url=config["openrouter_base_url"],
                api_key=os.getenv("OPENROUTER_API_KEY"),
                temperature=config["temperature"],
                max_tokens=config["max_tokens"]
            )
        elif self.provider == "local":
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=config["local_model"],
                base_url=config["local_base_url"],
                api_key="not-required",
                temperature=0.1,
                streaming=True,
                max_tokens=config["max_tokens"]
            )
        elif self.provider == "groq":
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=config["groq_model"],
                base_url=config["groq_base_url"],
                api_key=os.getenv("GROQ_API_KEY"),
                temperature=config["temperature"],
                max_tokens=config["max_tokens"]
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def _get_diff(self, context: PRAgentState) -> str:
        pr_url = context.get("pr_url")
        if not pr_url:
            raise ValueError("No PR URL provided")
        
        github = GitHubProvider(token=context.get("github_token"))
        diff = github.get_pr_diff(pr_url)
        if not diff:
            raise ValueError("Empty diff")
        return diff

class CodeReviewAgent(BaseLLMAgent):
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        try:
            diff = await self._get_diff(context)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", CODE_REVIEW_SYSTEM_PROMPT),
                ("user", CODE_REVIEW_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({"diff": diff[:20000]})
            
            review_data = from_toon(response.content)
            
            if not isinstance(review_data, dict):
                 review_data = {"raw": response.content}

            return {"code_review": review_data}

        except Exception as e:
            return {"code_review": {"error": str(e)}}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "pr_url" in context

    def get_dependencies(self) -> List[str]:
        return []

class PRDescriptionAgent(BaseLLMAgent):
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        try:
            diff = await self._get_diff(context)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", PR_DESCRIPTION_SYSTEM_PROMPT),
                ("user", PR_DESCRIPTION_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({"diff": diff[:20000]})
            
            data = from_toon(response.content)
            
            if not isinstance(data, dict):
                 data = {"raw": response.content}
                
            return {"pr_description": data}
        except Exception as e:
            return {"pr_description": {"error": str(e)}}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "pr_url" in context

    def get_dependencies(self) -> List[str]:
        return []

class CodeImprovementAgent(BaseLLMAgent):
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        try:
            diff = await self._get_diff(context)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", CODE_IMPROVEMENT_SYSTEM_PROMPT),
                ("user", CODE_IMPROVEMENT_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({"diff": diff[:20000]})
            
            data = from_toon(response.content)
            
            if not isinstance(data, dict):
                 data = {"raw": response.content}
                
            return {"code_improvements": data}
        except Exception as e:
            return {"code_improvements": {"error": str(e)}}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "pr_url" in context

    def get_dependencies(self) -> List[str]:
        return []

class PRQuestionsAgent(BaseLLMAgent):
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        try:
            diff = await self._get_diff(context)
            question = context.get("question", "What does this PR do?")
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", PR_QUESTIONS_SYSTEM_PROMPT),
                ("user", PR_QUESTIONS_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({"diff": diff[:20000], "question": question})
            
            return {"answer": response.content}
        except Exception as e:
            return {"answer": f"Error: {str(e)}"}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "pr_url" in context

    def get_dependencies(self) -> List[str]:
        return []

class ChangelogAgent(BaseLLMAgent):
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        try:
            diff = await self._get_diff(context)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", CHANGELOG_SYSTEM_PROMPT),
                ("user", CHANGELOG_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({"diff": diff[:20000]})
            
            data = from_toon(response.content)
            
            if isinstance(data, dict) and "entries" in data:
                # Format nicely for the user
                entries = data["entries"] or []
                if isinstance(entries, list):
                    text = "\n".join([f"- {e.get('type')}: {e.get('description')}" for e in entries])
                    return {"changelog_entry": text}
            
            return {"changelog_entry": response.content}
        except Exception as e:
            return {"changelog_entry": f"Error: {str(e)}"}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "pr_url" in context

    def get_dependencies(self) -> List[str]:
        return []

# Legacy / Placeholder Agents
class TestingAgent(BaseLLMAgent):
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        return {"testing_results": "Testing agent not fully implemented yet."}
    async def validate_input(self, context: PRAgentState) -> bool:
        return True
    def get_dependencies(self) -> List[str]:
        return []

class DocumentationAgent(BaseLLMAgent):
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        return {"documentation": "Documentation agent not fully implemented yet."}
    async def validate_input(self, context: PRAgentState) -> bool:
        return True
    def get_dependencies(self) -> List[str]:
        return []

class SecurityAgent(BaseLLMAgent):
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        return {"security_analysis": "Security agent not fully implemented yet."}
    async def validate_input(self, context: PRAgentState) -> bool:
        return True
    def get_dependencies(self) -> List[str]:
        return []
