"""
Streamlit UI for PR-Agent MCP Server

A web interface to interact with the PR-Agent FastMCP server.
Allows users to select LLM providers and execute tools interactively.
"""

import streamlit as st
import asyncio
import os
import sys
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config import get_llm_config, get_agent_config
from src.agents.specialized import (
    CodeReviewAgent, PRDescriptionAgent, CodeImprovementAgent,
    PRQuestionsAgent, ChangelogAgent
)

# Page configuration
st.set_page_config(
    page_title="PR-Agent Interactive UI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stAlert {
        margin-top: 1rem;
    }
    .tool-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .result-box {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'provider' not in st.session_state:
    st.session_state.provider = 'openai'
if 'results' not in st.session_state:
    st.session_state.results = {}

# Sidebar - Configuration
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # Provider Selection
    st.subheader("LLM Provider")
    provider = st.selectbox(
        "Select Provider",
        options=['openai', 'anthropic', 'openrouter', 'local'],
        index=0,
        help="Choose your LLM provider"
    )
    
    # Update provider in session state
    if provider != st.session_state.provider:
        st.session_state.provider = provider
        os.environ['LLM_PROVIDER'] = provider
    
    # Provider-specific configuration
    st.subheader("API Configuration")
    
    if provider == 'openai':
        api_key = st.text_input(
            "OpenAI API Key",
            value=os.getenv('OPENAI_API_KEY', ''),
            type="password",
            help="Your OpenAI API key"
        )
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key
            
        model = st.text_input(
            "Model",
            value=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            help="OpenAI model to use"
        )
        if model:
            os.environ['OPENAI_MODEL'] = model
            
    elif provider == 'anthropic':
        api_key = st.text_input(
            "Anthropic API Key",
            value=os.getenv('ANTHROPIC_API_KEY', ''),
            type="password",
            help="Your Anthropic API key"
        )
        if api_key:
            os.environ['ANTHROPIC_API_KEY'] = api_key
            
        model = st.text_input(
            "Model",
            value=os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20240620'),
            help="Anthropic model to use"
        )
        if model:
            os.environ['ANTHROPIC_MODEL'] = model
            
    elif provider == 'openrouter':
        api_key = st.text_input(
            "OpenRouter API Key",
            value=os.getenv('OPENROUTER_API_KEY', ''),
            type="password",
            help="Your OpenRouter API key"
        )
        if api_key:
            os.environ['OPENROUTER_API_KEY'] = api_key
            
        model = st.text_input(
            "Model",
            value=os.getenv('OPENROUTER_MODEL', 'x-ai/grok-beta'),
            help="OpenRouter model to use (e.g., x-ai/grok-beta, meta-llama/llama-3.1-8b-instruct:free)"
        )
        if model:
            os.environ['OPENROUTER_MODEL'] = model
            
    elif provider == 'local':
        base_url = st.text_input(
            "Base URL",
            value=os.getenv('LOCAL_LLM_BASE_URL', 'http://localhost:12434/engines/llama.cpp/v1'),
            help="Your local LLM endpoint"
        )
        if base_url:
            os.environ['LOCAL_LLM_BASE_URL'] = base_url
            
        model = st.text_input(
            "Model",
            value=os.getenv('LOCAL_LLM_MODEL', 'ai/llama3.2:latest'),
            help="Local model name"
        )
        if model:
            os.environ['LOCAL_LLM_MODEL'] = model
    
    # Advanced settings
    with st.expander("Advanced Settings"):
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=float(os.getenv('LLM_TEMPERATURE', '0.7')),
            step=0.1,
            help="Higher = more creative, Lower = more deterministic"
        )
        os.environ['LLM_TEMPERATURE'] = str(temperature)
        
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=100,
            max_value=128000,
            value=int(os.getenv('LLM_MAX_TOKENS', '8000')),
            step=100,
            help="Maximum tokens in response"
        )
        os.environ['LLM_MAX_TOKENS'] = str(max_tokens)
    
    # Display current config
    st.divider()
    config = get_llm_config()
    st.caption(f"🤖 Active Provider: **{config['provider']}**")
    st.caption(f"🌡️ Temperature: {config['temperature']}")
    st.caption(f"📊 Max Tokens: {config['max_tokens']}")

# Main content
st.title("🤖 PR-Agent Interactive UI")
st.markdown("Select a tool below and provide the required inputs to analyze pull requests.")

# Tool selection
tool_options = {
    "Code Review": {
        "agent": CodeReviewAgent,
        "description": "Perform comprehensive code review on a PR",
        "inputs": ["pr_url"],
        "icon": "🔍"
    },
    "PR Description": {
        "agent": PRDescriptionAgent,
        "description": "Generate detailed PR description with title, summary, and walkthrough",
        "inputs": ["pr_url"],
        "icon": "📝"
    },
    "Code Improvement": {
        "agent": CodeImprovementAgent,
        "description": "Suggest code optimizations and refactoring opportunities",
        "inputs": ["pr_url"],
        "icon": "⚡"
    },
    "PR Questions": {
        "agent": PRQuestionsAgent,
        "description": "Ask specific questions about the PR content",
        "inputs": ["pr_url", "question"],
        "icon": "❓"
    },
    "Changelog": {
        "agent": ChangelogAgent,
        "description": "Generate changelog entry for the PR",
        "inputs": ["pr_url"],
        "icon": "📋"
    },
}

selected_tool = st.selectbox(
    "Select Tool",
    options=list(tool_options.keys()),
    format_func=lambda x: f"{tool_options[x]['icon']} {x}",
    help="Choose which PR analysis tool to use"
)

tool_info = tool_options[selected_tool]

# Display tool description
st.info(f"**{tool_info['icon']} {selected_tool}**: {tool_info['description']}")

# Input form
with st.form(key='tool_form'):
    inputs = {}
    
    # PR URL input (required for all tools)
    pr_url = st.text_input(
        "PR URL *",
        placeholder="https://github.com/owner/repo/pull/123",
        help="Enter the GitHub pull request URL"
    )
    inputs['pr_url'] = pr_url
    
    # Optional GitHub token
    github_token = st.text_input(
        "GitHub Token (optional)",
        type="password",
        help="Only needed for private repositories",
        value=os.getenv('GITHUB_TOKEN', '')
    )
    inputs['github_token'] = github_token if github_token else None
    
    # Additional inputs for specific tools
    if 'question' in tool_info['inputs']:
        question = st.text_area(
            "Question *",
            placeholder="What are the main changes in this PR?",
            help="Enter your question about the PR"
        )
        inputs['question'] = question
    
    # Submit button
    col1, col2 = st.columns([1, 5])
    with col1:
        submit = st.form_submit_button("🚀 Run Analysis", use_container_width=True)
    with col2:
        if submit and not pr_url:
            st.error("PR URL is required!")

# Execute tool
if submit and pr_url:
    with st.spinner(f'Running {selected_tool}...'):
        try:
            # Create agent instance
            agent_class = tool_info['agent']
            agent = agent_class()
            
            # Prepare state
            state = {
                "pr_requirements": "",
                "pr_url": pr_url,
                "github_token": github_token,
                "agent_results": {},
                "execution_mode": "sequential",
                "task_graph": {},
                "final_pr": None,
                "errors": []
            }
            
            # Add question if needed
            if 'question' in inputs and inputs['question']:
                state['question'] = inputs['question']
            
            # Run async execution
            async def run_agent():
                return await agent.execute(state)
            
            result = asyncio.run(run_agent())
            
            # Display results
            st.success(f"✅ {selected_tool} completed successfully!")
            
            # Format and display results
            st.subheader("📊 Results")
            
            # Helper function to intelligently display content
            def display_formatted_content(content, title=None):
                """Intelligently format and display content based on its type."""
                
                if title:
                    st.markdown(f"**{title}**")
                
                # Handle different content types
                if isinstance(content, dict):
                    # Check if it's a structured result with multiple fields
                    for key, value in content.items():
                        st.markdown(f"### {key.replace('_', ' ').title()}")
                        if isinstance(value, str):
                            # Render markdown directly
                            st.markdown(value)
                        elif isinstance(value, (list, dict)):
                            with st.expander(f"📋 View Details"):
                                st.json(value)
                        else:
                            st.write(value)
                        st.divider()
                            
                elif isinstance(content, str):
                    # Render markdown directly - LLM now outputs proper markdown
                    st.markdown(content)
                    
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, str):
                            st.markdown(f"- {item}")
                        else:
                            st.json(item)
                    
                else:
                    st.write(content)
            
            # Find the result key (varies by agent)
            result_keys = list(result.keys())
            if result_keys:
                main_result = result[result_keys[0]]
                
                # Display with intelligent formatting
                display_formatted_content(main_result)
                
                # Add download button for results
                st.divider()
                col1, col2 = st.columns(2)
                
                with col1:
                    # Download as JSON
                    import json
                    json_str = json.dumps(result, indent=2)
                    st.download_button(
                        label="📥 Download as JSON",
                        data=json_str,
                        file_name=f"{selected_tool.lower().replace(' ', '_')}_result.json",
                        mime="application/json"
                    )
                
                with col2:
                    # Download as Markdown
                    if isinstance(main_result, str):
                        md_data = main_result
                    else:
                        md_data = json.dumps(main_result, indent=2)
                    
                    st.download_button(
                        label="📄 Download as Markdown",
                        data=md_data,
                        file_name=f"{selected_tool.lower().replace(' ', '_')}_result.md",
                        mime="text/markdown"
                    )
                
                # Store in session state
                st.session_state.results[selected_tool] = result
            else:
                st.warning("No results returned from agent")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            with st.expander("Show error details"):
                st.exception(e)

# Show previous results
if st.session_state.results:
    st.divider()
    st.subheader("📚 Previous Results")
    
    for tool_name, result in st.session_state.results.items():
        with st.expander(f"{tool_options[tool_name]['icon']} {tool_name}"):
            # Display with same formatting
            result_keys = list(result.keys())
            if result_keys:
                main_result = result[result_keys[0]]
                
                # Use tabs for better organization
                if isinstance(main_result, dict):
                    tabs = st.tabs(list(main_result.keys()))
                    for i, (key, value) in enumerate(main_result.items()):
                        with tabs[i]:
                            if isinstance(value, str):
                                st.markdown(value)
                            else:
                                st.json(value)
                else:
                    st.write(main_result)

# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🔧 Built with Streamlit")
with col2:
    st.caption("🤖 Powered by PR-Agent")
with col3:
    st.caption("📡 FastMCP Integration")
