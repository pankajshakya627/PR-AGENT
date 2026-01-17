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
        github_token="fake_token"
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
