import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.specialized import SecurityAgent, PerformanceAgent, TestAgent
from src.state import PRAgentState

@pytest.fixture
def mock_llm_config():
    with patch("src.agents.specialized.get_llm_config") as mock:
        mock.return_value = {
            "provider": "openai",
            "openai_model": "gpt-4-test",
            "max_tokens": 1000
        }
        yield mock

@pytest.fixture
def mock_chain():
    mock = AsyncMock()
    mock.ainvoke.return_value = MagicMock(content="Mocked LLM Response")
    return mock

@pytest.fixture
def state():
    return PRAgentState(
        pr_url="https://github.com/test/repo/pull/1",
        github_token="fake_token",
        tenant_id="test_tenant"
    )

@pytest.mark.asyncio
async def test_security_agent(mock_llm_config, mock_chain, state):
    with patch("src.agents.specialized.BaseLLMAgent._create_llm", return_value=MagicMock()), \
         patch("src.agents.specialized.GitHubProvider") as MockGitHubProvider:
        
        # Instantiate agent
        agent = SecurityAgent()
        agent.llm = MagicMock()
        
        # Instance mocks
        agent._get_diff = AsyncMock(return_value="diff content")
        agent._run_tool = AsyncMock(return_value="Bandit output")
        
        # Mock GitHubProvider
        mock_gh_instance = MockGitHubProvider.return_value
        mock_gh_instance.get_pr_files_content.return_value = {"secure.py": "print('password')"}
        
        # Mock Chain
        with patch("src.agents.specialized.ChatPromptTemplate.from_messages") as mock_prompt:
            mock_prompt_obj = MagicMock()
            mock_prompt.return_value = mock_prompt_obj
            mock_chain_obj = AsyncMock()
            mock_chain_obj.ainvoke.return_value = MagicMock(content="## Vulnerabilities Found")
            mock_prompt_obj.__or__.return_value = mock_chain_obj
            
            result = await agent.execute(state)
            
            # Assertions
            mock_gh_instance.get_pr_files_content.assert_called_once()
            agent._run_tool.assert_called_once()
            assert "security_analysis" in result


@pytest.mark.asyncio
async def test_performance_agent(mock_llm_config, mock_chain, state):
    with patch("src.agents.specialized.BaseLLMAgent._create_llm", return_value=MagicMock()), \
         patch("src.agents.specialized.BaseLLMAgent._get_diff", new_callable=AsyncMock) as mock_get_diff:
        
        mock_get_diff.return_value = "diff content"
        
        agent = PerformanceAgent()
        agent.llm = MagicMock()
        
        with patch("src.agents.specialized.ChatPromptTemplate.from_messages") as mock_prompt:
            mock_prompt_obj = MagicMock()
            mock_prompt.return_value = mock_prompt_obj
            mock_chain_obj = AsyncMock()
            mock_chain_obj.ainvoke.return_value = MagicMock(content="## Performance Assessment\n\nNo issues found.")
            mock_prompt_obj.__or__.return_value = mock_chain_obj
            
            result = await agent.execute(state)
            
            assert "performance_analysis" in result
            assert "Performance Assessment" in result["performance_analysis"]

@pytest.mark.asyncio
async def test_test_agent(mock_llm_config, mock_chain, state):
    with patch("src.agents.specialized.BaseLLMAgent._create_llm", return_value=MagicMock()), \
         patch("src.agents.specialized.BaseLLMAgent._get_diff", new_callable=AsyncMock) as mock_get_diff:
        
        mock_get_diff.return_value = "diff content"
        
        agent = TestAgent()
        agent.llm = MagicMock()
        
        with patch("src.agents.specialized.ChatPromptTemplate.from_messages") as mock_prompt:
            mock_prompt_obj = MagicMock()
            mock_prompt.return_value = mock_prompt_obj
            mock_chain_obj = AsyncMock()
            mock_chain_obj.ainvoke.return_value = MagicMock(content="## Missing Tests\n\n- test_auth")
            mock_prompt_obj.__or__.return_value = mock_chain_obj
            
            result = await agent.execute(state)
            
@pytest.mark.asyncio
async def test_code_review_agent_with_tool(mock_llm_config, mock_chain, state):
    from src.agents.specialized import CodeReviewAgent
    with patch("src.agents.specialized.BaseLLMAgent._create_llm", return_value=MagicMock()), \
         patch("src.agents.specialized.GitHubProvider") as MockGitHubProvider:
        
        agent = CodeReviewAgent()
        agent.llm = MagicMock()
        
        agent._get_diff = AsyncMock(return_value="diff content")
        agent._run_tool = AsyncMock(return_value="Pylint output")
        
        mock_gh_instance = MockGitHubProvider.return_value
        mock_gh_instance.get_pr_files_content.return_value = {"main.py": "def foo(): pass"}
        
        with patch("src.agents.specialized.ChatPromptTemplate.from_messages") as mock_prompt:
            mock_prompt_obj = MagicMock()
            mock_prompt.return_value = mock_prompt_obj
            mock_chain_obj = AsyncMock()
            mock_chain_obj.ainvoke.return_value = MagicMock(content="## Review")
            mock_prompt_obj.__or__.return_value = mock_chain_obj
            
            result = await agent.execute(state)
            
            mock_gh_instance.get_pr_files_content.assert_called_once()
            agent._run_tool.assert_called_once()
            assert "code_review" in result


@pytest.mark.asyncio
async def test_pr_questions_agent(mock_llm_config, mock_chain, state):
    from src.agents.specialized import PRQuestionsAgent
    with patch("src.agents.specialized.BaseLLMAgent._create_llm", return_value=MagicMock()):
        agent = PRQuestionsAgent()
        agent.llm = MagicMock()
        
        agent._get_diff = AsyncMock(return_value="diff content")
        
        with patch("src.agents.specialized.ChatPromptTemplate.from_messages") as mock_prompt:
            mock_prompt_obj = MagicMock()
            mock_prompt.return_value = mock_prompt_obj
            mock_chain_obj = AsyncMock()
            mock_chain_obj.ainvoke.return_value = MagicMock(content="Answer to question")
            mock_prompt_obj.__or__.return_value = mock_chain_obj
            
            state["question"] = "What does this PR do?"
            result = await agent.execute(state)
            
            assert "answer" in result
            assert result["answer"] == "Answer to question"


@pytest.mark.asyncio
async def test_changelog_agent(mock_llm_config, mock_chain, state):
    import os
    os.environ["ENABLE_CACHING"] = "False"
    from src.agents.specialized import ChangelogAgent
    with patch("src.agents.specialized.BaseLLMAgent._create_llm", return_value=MagicMock()):
        agent = ChangelogAgent()
        agent.llm = MagicMock()
        
        agent._get_diff = AsyncMock(return_value="diff content")
        
        with patch("src.agents.specialized.ChatPromptTemplate.from_messages") as mock_prompt:
            mock_prompt_obj = MagicMock()
            mock_prompt.return_value = mock_prompt_obj
            mock_chain_obj = AsyncMock()
            
            # Invalid non-JSON responses are rejected rather than accepted raw.
            mock_chain_obj.ainvoke.return_value = MagicMock(content="- Added: new functionality")
            mock_prompt_obj.__or__.return_value = mock_chain_obj
            
            result = await agent.execute(state)
            assert "changelog_entry" in result
            assert result["changelog_entry"].startswith("Error: Invalid changelog response")
            
            # Test Pydantic JSON mock response parsing
            mock_chain_obj.ainvoke.return_value = MagicMock(content='{"entries": [{"type": "feat", "description": "Test feature"}]}')
            result_json = await agent.execute(state)
            assert result_json["changelog_entry"] == "- feat: Test feature"


@pytest.mark.asyncio
async def test_dynamic_execution_fallback(mock_llm_config, mock_chain, state):
    from src.agents.specialized import ChangelogAgent
    import os
    os.environ["ENABLE_CACHING"] = "False"
    
    # Configure mock config to use openrouter as primary
    mock_llm_config.return_value["provider"] = "openrouter"
    
    # We mock _create_llm to simulate a primary provider failure and successful fallback
    mock_primary_llm = MagicMock()
    # The primary provider throws an error during ainvoke
    mock_primary_llm.ainvoke = AsyncMock(side_effect=ValueError("Primary provider execution error"))
    
    mock_fallback_llm = MagicMock()
    # The fallback provider successfully returns the JSON response
    mock_fallback_llm.ainvoke = AsyncMock(return_value=MagicMock(content='{"entries": [{"type": "fix", "description": "Fallback success"}]}'))
    
    # Track calls to _create_llm
    created_providers = []
    def create_mock_llm(provider, config):
        created_providers.append(provider)
        if provider == "openrouter":
            return mock_primary_llm
        else:
            return mock_fallback_llm
            
    with patch("src.agents.specialized.BaseLLMAgent._create_llm", side_effect=create_mock_llm):
        # We start with openrouter as primary provider
        os.environ["LLM_PROVIDER"] = "openrouter"
        agent = ChangelogAgent()
        agent._get_diff = AsyncMock(return_value="diff content")
        
        # Verify that during execute:
        # 1. First openrouter tries and fails
        # 2. Automatically falls back to other providers in the list (e.g. nvidia)
        # 3. Succeeds using fallback
        result = await agent.execute(state)
        assert "changelog_entry" in result
        assert result["changelog_entry"] == "- fix: Fallback success"
        assert "openrouter" in created_providers
        assert len(created_providers) > 1


@pytest.mark.asyncio
async def test_fallback_proxy_concurrency(mock_llm_config, state):
    from src.agents.specialized import BaseLLMAgent
    import asyncio
    import os
    
    # Mock config to use groq as primary
    mock_llm_config.return_value["provider"] = "groq"
    
    # Create mock clients
    mock_groq = MagicMock()
    mock_groq.ainvoke = AsyncMock(side_effect=ValueError("Groq fail"))
    
    mock_nvidia = MagicMock()
    mock_nvidia.ainvoke = AsyncMock(return_value=MagicMock(content="Nvidia success"))
    
    def create_mock_llm(provider, config):
        if provider == "groq":
            return mock_groq
        return mock_nvidia
        
    with patch("src.agents.specialized.BaseLLMAgent._create_llm", side_effect=create_mock_llm):
        os.environ["LLM_PROVIDER"] = "groq"
        from src.agents.specialized import TestAgent
        agent = TestAgent()
        
        # Call ainvoke concurrently using asyncio.gather
        tasks = [
            agent.llm.ainvoke("test query 1"),
            agent.llm.ainvoke("test query 2"),
            agent.llm.ainvoke("test query 3")
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for res in results:
            assert res.content == "Nvidia success"
            
        assert agent.provider == "nvidia"


def test_pydantic_schema_validation():
    from src.schemas import ChangelogEntry, ChangelogResponse
    from pydantic import ValidationError
    
    # Valid model validation
    entry = ChangelogEntry(type="feat", description="Dynamic fallback")
    assert entry.type == "feat"
    
    resp = ChangelogResponse(entries=[entry])
    assert len(resp.entries) == 1
    
    # Invalid model validation
    with pytest.raises(ValidationError):
        ChangelogEntry(description="Missing type field")

    with pytest.raises(ValidationError):
        ChangelogEntry(type="misc", description="Unsupported type")

    with pytest.raises(ValidationError):
        ChangelogEntry(type="fix", description="   ")

    with pytest.raises(ValidationError):
        ChangelogResponse(entries=[])


def test_nvidia_key_validation_rejection(mock_llm_config):
    from src.agents.specialized import TestAgent
    import os

    # Instantiate agent using a mock _create_llm so init succeeds
    mock_llm = MagicMock()
    with patch("src.agents.specialized.BaseLLMAgent._create_llm", return_value=mock_llm):
        agent = TestAgent()

    # Now call the REAL _create_llm directly with an empty/whitespace-only key
    os.environ["NVIDIA_API_KEY"] = "   "
    try:
        with pytest.raises(ValueError, match="NVIDIA_API_KEY not set or empty"):
            agent._create_llm("nvidia", agent.config)
    finally:
        # Always clean up env var
        os.environ.pop("NVIDIA_API_KEY", None)


def test_nvidia_base_url_is_passed_to_client(mock_llm_config):
    from src.agents.specialized import TestAgent
    import os

    mock_llm = MagicMock()
    with patch("src.agents.specialized.BaseLLMAgent._create_llm", return_value=mock_llm):
        agent = TestAgent()

    os.environ["NVIDIA_API_KEY"] = "fake-key"
    try:
        llm = agent._create_llm(
            "nvidia",
            {
                "nvidia_model": "z-ai/glm-5.1",
                "nvidia_base_url": "https://example.test/v1",
                "temperature": 0.2,
                "max_tokens": 1000,
            },
        )
        assert str(llm.base_url) == "https://example.test/v1"
    finally:
        os.environ.pop("NVIDIA_API_KEY", None)
