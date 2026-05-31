from typing import Dict, Any, List
from src.agents.base import BaseAgent
from src.state import PRAgentState
from src.github_provider import GitHubProvider
from src.config import get_llm_config
from src.tenant import tenant_scoped
from langchain_core.prompts import ChatPromptTemplate
import json
import os
import tempfile
from src.prompts import (
    CODE_REVIEW_SYSTEM_PROMPT, CODE_REVIEW_USER_PROMPT,
    PR_DESCRIPTION_SYSTEM_PROMPT, PR_DESCRIPTION_USER_PROMPT,
    CODE_IMPROVEMENT_SYSTEM_PROMPT, CODE_IMPROVEMENT_USER_PROMPT,
    PR_QUESTIONS_SYSTEM_PROMPT, PR_QUESTIONS_USER_PROMPT,
    CHANGELOG_SYSTEM_PROMPT, CHANGELOG_USER_PROMPT,
    COMMIT_PR_GENERATOR_SYSTEM_PROMPT, COMMIT_PR_GENERATOR_USER_PROMPT,
    BRANCH_PR_GENERATOR_SYSTEM_PROMPT, BRANCH_PR_GENERATOR_USER_PROMPT,
    SECURITY_AGENT_SYSTEM_PROMPT, SECURITY_AGENT_USER_PROMPT,
    PERFORMANCE_AGENT_SYSTEM_PROMPT, PERFORMANCE_AGENT_USER_PROMPT,
    TEST_AGENT_SYSTEM_PROMPT, TEST_AGENT_USER_PROMPT
)
from pydantic import BaseModel, Field

class ChangelogEntry(BaseModel):
    type: str = Field(description="e.g. feat, fix, chore, docs, refactor, performance, security")
    description: str = Field(description="Brief explanation of the changes")

class ChangelogResponse(BaseModel):
    entries: List[ChangelogEntry]

class BaseLLMAgent(BaseAgent):
    # Provider fallback order
    PROVIDER_ORDER = ["groq", "nvidia", "openrouter", "openai", "anthropic"]
    
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
        elif provider == "nvidia":
            api_key = os.getenv("NVIDIA_API_KEY")
            if not api_key:
                raise ValueError("NVIDIA_API_KEY not set")
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            model = config.get("nvidia_model") or "meta/llama2-70b"
            base_url = config.get("nvidia_base_url") or "https://integrate.api.nvidia.com/v1"
            return ChatNVIDIA(
                model=model,
                api_key=api_key,
                base_url=base_url,
                temperature=config["temperature"],
                max_tokens=config["max_tokens"]
            )
        elif provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not set")
            from langchain_openai import ChatOpenAI
            model = config["openrouter_model"] or "xiaomi/mimo-v2-flash:free"
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
            
        from src.memory import L1WorkingMemory
        max_chars = int(os.getenv("LLM_MAX_CONTEXT_CHARS", "12000"))
        return L1WorkingMemory.optimize_diff_context(diff, max_chars)

class CodeReviewAgent(BaseLLMAgent):
    @tenant_scoped
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        """
        Executes code review by analyzing the diff and running linters.
        """
        try:
            diff = await self._get_diff(context)
            
            # --- Tool Execution: Pylint ---
            tool_output = "No code analysis tools run (no python files found or tool execution failed)."
            try:
                # Fetch full file contents
                gh = GitHubProvider(token=context.get("github_token"))
                files_content = gh.get_pr_files_content(context.get("pr_url"))
                
                if files_content:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        files_to_scan = []
                        for filename, content in files_content.items():
                            if filename.endswith(".py"):
                                file_path = os.path.join(temp_dir, os.path.basename(filename))
                                with open(file_path, "w") as f:
                                    f.write(content)
                                files_to_scan.append(file_path)
                        
                        if files_to_scan:
                            # Run pylint
                            # -E: Errors only (to reduce noise)
                            # --output-format=text
                            command = ["pylint", "-E", "--output-format=text"] + files_to_scan
                            tool_output = await self._run_tool(command)
            except Exception as e:
                tool_output = f"Error running code analysis tools: {e}"
            # ------------------------------
            
            from src.memory import L1WorkingMemory, L3SemanticMemory
            max_chars = int(os.getenv("LLM_MAX_CONTEXT_CHARS", "12000"))
            diff_optimized = L1WorkingMemory.optimize_diff_context(diff, max_chars)
            
            # Retrieve semantic memory rules
            semantic_rules = L3SemanticMemory.get_rules()
            rules_prompt = "\n".join([f"- {r}" for r in semantic_rules])
            system_prompt = f"{CODE_REVIEW_SYSTEM_PROMPT}\n\n**Additional Semantic Rules to Enforce**:\n{rules_prompt}"
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", CODE_REVIEW_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({
                "diff": diff_optimized,
                "tool_output": tool_output[:5000]
            })
            
            # Return raw markdown directly - prompts output markdown now
            return {"code_review": response.content}

        except Exception as e:
            return {"code_review": {"error": str(e)}}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "pr_url" in context

    def get_dependencies(self) -> List[str]:
        return []

class PRDescriptionAgent(BaseLLMAgent):
    @tenant_scoped
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
    @tenant_scoped
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
    @tenant_scoped
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        try:
            from src.memory import L1WorkingMemory, L2EpisodicMemory
            diff = await self._get_diff(context)
            question = context.get("question", "")
            
            max_chars = int(os.getenv("LLM_MAX_CONTEXT_CHARS", "12000"))
            diff_optimized = L1WorkingMemory.optimize_diff_context(diff, max_chars)
            
            pr_url = context.get("pr_url") or ""
            episodes = L2EpisodicMemory.retrieve_episodes(pr_url)
            
            # Format episodes/trajectories
            episodes_context = ""
            if episodes:
                episodes_context = "\n\n**Episode Execution Trajectories (L2 Episodic Memory)**:\n"
                for name, ep in episodes.items():
                    data_str = str(ep["data"])[:2500]  # Keep high-density episodic scope
                    data_str = data_str.replace("{", "{{").replace("}", "}}")
                    episodes_context += f"### Episode: {name} (Recorded: {ep['timestamp']})\n{data_str}\n\n"
            
            system_prompt = f"{PR_QUESTIONS_SYSTEM_PROMPT}{episodes_context}"
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", PR_QUESTIONS_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({"diff": diff_optimized, "question": question})
            
            return {"answer": response.content}
        except Exception as e:
            return {"answer": f"Error: {str(e)}"}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "pr_url" in context

    def get_dependencies(self) -> List[str]:
        return []

class ChangelogAgent(BaseLLMAgent):
    @tenant_scoped
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        try:
            from src.memory import L1WorkingMemory
            diff = await self._get_diff(context)
            
            max_chars = int(os.getenv("LLM_MAX_CONTEXT_CHARS", "12000"))
            diff_optimized = L1WorkingMemory.optimize_diff_context(diff, max_chars)
            
            system_prompt = (
                f"{CHANGELOG_SYSTEM_PROMPT}\n\n"
                "**Response Requirement**:\n"
                "You MUST respond with a valid JSON object matching the following structure:\n"
                "{{\n  \"entries\": [\n    {{\n      \"type\": \"feat | fix | chore | docs | refactor | performance | security\",\n      \"description\": \"Brief explanation\"\n    }}\n  ]\n}}"
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", CHANGELOG_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({"diff": diff_optimized})
            
            content = response.content.strip()
            
            # Remove possible markdown code fences if present (e.g. ```json ... ```)
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                if content.endswith("```"):
                    content = content.rsplit("```", 1)[0]
                content = content.strip()
            
            # Validate utilizing Pydantic
            try:
                parsed = json.loads(content)
                validated = ChangelogResponse(**parsed)
                
                # Render validated JSON back to Keep-a-Changelog Markdown format
                lines = []
                for entry in validated.entries:
                    lines.append(f"- {entry.type}: {entry.description}")
                changelog_entry = "\n".join(lines)
            except Exception as parse_err:
                import logging
                logging.warning(f"ChangelogAgent: Pydantic validation failed ({parse_err}). Falling back to raw response.")
                changelog_entry = response.content
            
            return {"changelog_entry": changelog_entry}
        except Exception as e:
            return {"changelog_entry": f"Error: {str(e)}"}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "pr_url" in context

    def get_dependencies(self) -> List[str]:
        return []

class CommitPRGeneratorAgent(BaseLLMAgent):
    """Agent that generates PR title and description from a commit URL."""
    
    async def _get_commit_diff_and_details(self, context: PRAgentState) -> tuple[str, Dict[str, Any]]:
        """Fetch commit diff and details from GitHub."""
        commit_url = context.get("commit_url")
        if not commit_url:
            raise ValueError("No commit URL provided")
        
        github = GitHubProvider(token=context.get("github_token"))
        diff = github.get_commit_diff(commit_url)
        details = github.get_commit_details(commit_url)
        
        if not diff:
            raise ValueError("Empty diff")
            
        from src.memory import L1WorkingMemory
        max_chars = int(os.getenv("LLM_MAX_CONTEXT_CHARS", "12000"))
        diff_opt = L1WorkingMemory.optimize_diff_context(diff, max_chars)
        return diff_opt, details
    
    @tenant_scoped
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        try:
            diff, details = await self._get_commit_diff_and_details(context)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", COMMIT_PR_GENERATOR_SYSTEM_PROMPT),
                ("user", COMMIT_PR_GENERATOR_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({
                "diff": diff[:20000],
                "commit_message": details.get("message", ""),
                "author": details.get("author", "Unknown"),
                "files_changed": details.get("files_changed", 0),
                "additions": details.get("additions", 0),
                "deletions": details.get("deletions", 0)
            })
            
            # Return raw markdown directly
            return {"pr_from_commit": response.content}
        except Exception as e:
            return {"pr_from_commit": {"error": str(e)}}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "commit_url" in context

    def get_dependencies(self) -> List[str]:
        return []

class BranchPRGeneratorAgent(BaseLLMAgent):
    """Agent that generates PR title and description by comparing two branches."""
    
    @tenant_scoped
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        try:
            repo_name = context.get("repo_name")
            head_branch = context.get("head_branch")
            base_branch = context.get("base_branch", "main")
            commit_limit = context.get("commit_limit")  # None or int
            
            if not repo_name or not head_branch:
                raise ValueError("repo_name and head_branch are required")
            
            github = GitHubProvider(token=context.get("github_token"))
            comparison = github.compare_branches(repo_name, base_branch, head_branch)
            
            # Get commits (optionally limited)
            all_commits = comparison.get("commits", [])
            if commit_limit and len(all_commits) > commit_limit:
                # Take the last N commits (most recent)
                commits_to_use = all_commits[-commit_limit:]
                limit_note = f"(showing last {commit_limit} of {len(all_commits)} total)"
            else:
                commits_to_use = all_commits
                limit_note = ""
            
            # Format commits list
            commits_list = "\n".join([
                f"- {c['sha']}: {c['message']} ({c['author']})"
                for c in commits_to_use
            ])
            if limit_note:
                commits_list = f"{limit_note}\n{commits_list}"
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", BRANCH_PR_GENERATOR_SYSTEM_PROMPT),
                ("user", BRANCH_PR_GENERATOR_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({
                "head": head_branch,
                "base": base_branch,
                "total_commits": len(commits_to_use),
                "commits_list": commits_list or "No commits found",
                "diff": comparison.get("diff", "")[:20000],
                "files_changed": comparison.get("files_changed", 0),
                "additions": comparison.get("additions", 0),
                "deletions": comparison.get("deletions", 0)
            })
            
            return {
                "pr_from_branch": response.content,
                "branch_info": {
                    "head": head_branch,
                    "base": base_branch,
                    "total_commits": comparison.get("total_commits", 0),
                    "files_changed": comparison.get("files_changed", 0)
                }
            }
        except Exception as e:
            return {"pr_from_branch": {"error": str(e)}}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "repo_name" in context and "head_branch" in context

    def get_dependencies(self) -> List[str]:
        return []

class TestAgent(BaseLLMAgent):
    """Agent for analyzing test coverage and suggesting tests."""
    
    @tenant_scoped
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        try:
            diff = await self._get_diff(context)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", TEST_AGENT_SYSTEM_PROMPT),
                ("user", TEST_AGENT_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({"diff": diff[:20000]})
            
            return {"testing_results": response.content}
        except Exception as e:
            return {"testing_results": {"error": str(e)}}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "pr_url" in context

    def get_dependencies(self) -> List[str]:
        return []

class PerformanceAgent(BaseLLMAgent):
    """Agent for analyzing code performance and complexity."""
    
    @tenant_scoped
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        try:
            diff = await self._get_diff(context)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", PERFORMANCE_AGENT_SYSTEM_PROMPT),
                ("user", PERFORMANCE_AGENT_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({"diff": diff[:20000]})
            
            return {"performance_analysis": response.content}
        except Exception as e:
            return {"performance_analysis": {"error": str(e)}}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "pr_url" in context

    def get_dependencies(self) -> List[str]:
        return []

class SecurityAgent(BaseLLMAgent):
    """Agent for analyzing security vulnerabilities."""
    
    @tenant_scoped
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        try:
            diff = await self._get_diff(context)
            
            # --- Tool Execution: Bandit ---
            tool_output = "No security tools run (no python files found or tool execution failed)."
            try:
                 # Fetch full file contents
                gh = GitHubProvider(token=context.get("github_token"))
                files_content = gh.get_pr_files_content(context.get("pr_url"))
                
                if files_content:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Write files to temp dir
                        files_to_scan = []
                        for filename, content in files_content.items():
                            if filename.endswith(".py"):
                                file_path = os.path.join(temp_dir, os.path.basename(filename))
                                with open(file_path, "w") as f:
                                    f.write(content)
                                files_to_scan.append(file_path)
                        
                        if files_to_scan:
                            # Run bandit
                            # -r: recursive (though we list files)
                            # -f text: text format
                            # -ll: medium and high severity
                            command = ["bandit", "-f", "text", "-ll"] + files_to_scan
                            tool_output = await self._run_tool(command)
            except Exception as e:
                tool_output = f"Error running security tools: {e}"
            # ------------------------------

            prompt = ChatPromptTemplate.from_messages([
                ("system", SECURITY_AGENT_SYSTEM_PROMPT),
                ("user", SECURITY_AGENT_USER_PROMPT)
            ])

            chain = prompt | self.llm
            response = await chain.ainvoke({
                "diff": diff[:20000],
                "tool_output": tool_output[:5000] # Truncate to avoid context limit
            })
            
            return {"security_analysis": response.content}
        except Exception as e:
            return {"security_analysis": {"error": str(e)}}

    async def validate_input(self, context: PRAgentState) -> bool:
        return "pr_url" in context

    def get_dependencies(self) -> List[str]:
        return []

# Legacy / Placeholder Agents
class TestingAgent(TestAgent):
    """Legacy alias for TestAgent."""
    pass

class DocumentationAgent(BaseLLMAgent):
    @tenant_scoped
    async def execute(self, context: PRAgentState) -> Dict[str, Any]:
        return {"documentation": "Documentation agent not fully implemented yet."}
    async def validate_input(self, context: PRAgentState) -> bool:
        return True
    def get_dependencies(self) -> List[str]:
        return []
