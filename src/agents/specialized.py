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
    # Provider fallback order
    PROVIDER_ORDER = ["groq", "openrouter", "openai", "anthropic"]
    
    def __init__(self):
        config = get_llm_config()
        self.config = config
        self.llm = None
        self.provider = None
        
        # Try providers in order until one works
        providers_to_try = [config["provider"]] + [p for p in self.PROVIDER_ORDER if p != config["provider"]]
        
        for provider in providers_to_try:
            try:
                self.llm = self._create_llm(provider, config)
                self.provider = provider
                break
            except Exception as e:
                import logging
                logging.warning(f"Failed to initialize {provider}: {e}, trying next provider...")
                continue
        
        if self.llm is None:
            raise ValueError("All LLM providers failed to initialize")
    
    def _create_llm(self, provider: str, config: dict):
        """Create LLM instance for given provider."""
        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not set")
            from langchain_openai import ChatOpenAI
            model = config["groq_model"] or "llama-3.1-8b-instant"
            return ChatOpenAI(
                model=model,
                base_url=config["groq_base_url"],
                api_key=api_key,
                temperature=config["temperature"],
                max_tokens=config["max_tokens"]
            )
        elif provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not set")
            from langchain_openai import ChatOpenAI
            model = config["openrouter_model"] or "amazon/nova-2-lite-v1:free"
            return ChatOpenAI(
                model=model,
                base_url=config["openrouter_base_url"],
                api_key=api_key,
                temperature=config["temperature"],
                max_tokens=config["max_tokens"]
            )
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            from langchain_openai import ChatOpenAI
            model = config["openai_model"] or "gpt-4.1-mini"
            return ChatOpenAI(
                model=model,
                api_key=api_key,
                temperature=0.2,
                max_tokens=config["max_tokens"]
            )
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            from langchain_anthropic import ChatAnthropic
            model = config["anthropic_model"] or "claude-sonnet-4-5-20250929"
            return ChatAnthropic(
                model=model,
                api_key=api_key,
                temperature=0.2,
                max_tokens=config["max_tokens"]
            )
        elif provider == "local":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=config["local_model"],
                base_url=config["local_base_url"],
                api_key="not-required",
                temperature=0.1,
                streaming=True,
                max_tokens=config["max_tokens"]
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

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
            
            # Return raw markdown directly - prompts output markdown now
            return {"code_review": response.content}

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
            
            # Return raw markdown directly
            return {"pr_description": response.content}
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
            
            # Return raw markdown directly
            return {"code_improvements": response.content}
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
            
            # Return raw markdown directly
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
