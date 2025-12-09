"""
Streamlit UI for PR-Agent MCP Server

A web interface to interact with the PR-Agent FastMCP server.
Features secure login/registration with streamlit-authenticator.
"""

import streamlit as st
import streamlit_authenticator as stauth
import bcrypt
import yaml
from yaml.loader import SafeLoader
import asyncio
import os
import sys
import re
from pathlib import Path
import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Config file path
CONFIG_FILE = project_root / "config" / "auth_config.yaml"


def load_config():
    """Load authentication config from YAML file."""
    if not CONFIG_FILE.exists():
        # Create default config
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        default_config = {
            'credentials': {
                'usernames': {
                    'admin': {
                        'email': 'admin@pragent.com',
                        'name': 'Administrator',
                        'password': bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt()).decode()
                    }
                }
            },
            'cookie': {
                'expiry_days': 30,
                'key': 'pr_agent_auth_secret_key',
                'name': 'pr_agent_auth'
            },
            'pre-authorized': {
                'emails': ['admin@pragent.com']
            }
        }
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(default_config, f)
        return default_config
    
    with open(CONFIG_FILE) as f:
        return yaml.load(f, Loader=SafeLoader)


def save_config(config):
    """Save authentication config to YAML file."""
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


# Page configuration
st.set_page_config(
    page_title="PR-Agent Interactive UI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling (theme-aware)
st.markdown("""
<style>
    /* Auth header styling */
    .auth-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .auth-header h1 {
        font-size: 2.5rem;
        background: linear-gradient(120deg, #00d4ff, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .auth-header p {
        opacity: 0.7;
        font-size: 1rem;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        justify-content: center;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        font-weight: 600;
    }
    
    /* Input styling - theme aware */
    .stTextInput > div > div > input {
        border-radius: 10px;
    }
    
    /* Button styling */
    .stButton > button[kind="primary"] {
        background: linear-gradient(120deg, #7c3aed, #00d4ff);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.4);
    }
    
    /* Alert styling */
    .stAlert {
        border-radius: 10px;
    }
    
    /* Tool card styling */
    .tool-card {
        padding: 1.5rem;
        border-radius: 15px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 1rem;
    }
    
    .result-box {
        padding: 1.5rem;
        border-radius: 15px;
        font-family: 'Fira Code', 'Courier New', monospace;
        white-space: pre-wrap;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    
    /* Sidebar user info */
    .user-info {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        text-align: center;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    
    .user-avatar {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Load config
config = load_config()

# Initialize authenticator (removed pre-authorized as it's deprecated)
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)


def show_auth_page():
    """Display authentication page with login and register tabs."""
    # Centered container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Header
        st.markdown("""
        <div class="auth-header">
            <h1>🤖 PR-Agent</h1>
            <p>Intelligent Pull Request Analysis</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Tabs for Login and Register
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
        
        with tab1:
            # Login form
            try:
                authenticator.login(location='main', key='login')
            except Exception as e:
                st.error(f"Login error: {e}")
            
            if st.session_state.get("authentication_status") == False:
                st.error("❌ Invalid username or password")
            elif st.session_state.get("authentication_status") is None:
                st.info("👆 Enter your credentials to continue")
        
        with tab2:
            # Registration form
            st.markdown("### Create Account")
            
            with st.form("register_form", clear_on_submit=True):
                new_email = st.text_input("📧 Email", placeholder="your.email@example.com")
                new_username = st.text_input("👤 Username", placeholder="Choose a username")
                new_name = st.text_input("📝 Full Name", placeholder="Your full name")
                new_password = st.text_input("🔒 Password", type="password", placeholder="Min 8 characters")
                new_password_repeat = st.text_input("🔒 Confirm Password", type="password", placeholder="Repeat password")
                
                register_btn = st.form_submit_button("Create Account", use_container_width=True)
                
                if register_btn:
                    # Validation
                    errors = []
                    
                    if not new_email or '@' not in new_email:
                        errors.append("Valid email is required")
                    
                    if not new_username or len(new_username) < 3:
                        errors.append("Username must be at least 3 characters")
                    
                    if new_username in config['credentials']['usernames']:
                        errors.append("Username already exists")
                    
                    for user_data in config['credentials']['usernames'].values():
                        if user_data.get('email', '').lower() == new_email.lower():
                            errors.append("Email already registered")
                            break
                    
                    if len(new_password) < 8:
                        errors.append("Password must be at least 8 characters")
                    
                    if new_password != new_password_repeat:
                        errors.append("Passwords do not match")
                    
                    if errors:
                        for error in errors:
                            st.error(f"❌ {error}")
                    else:
                        # Hash password and save user
                        hashed_pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                        config['credentials']['usernames'][new_username] = {
                            'email': new_email,
                            'name': new_name,
                            'password': hashed_pw
                        }
                        save_config(config)
                        st.success("✅ Account created successfully! Please login.")
                        st.balloons()


# ============== AUTHENTICATION CHECK ==============
if st.session_state.get("authentication_status") != True:
    show_auth_page()
    st.stop()

# ============== MAIN APP (after authentication) ==============

# Import after auth check to avoid loading issues
from src.config import get_llm_config, get_agent_config
from src.agents.specialized import (
    CodeReviewAgent, PRDescriptionAgent, CodeImprovementAgent,
    PRQuestionsAgent, ChangelogAgent, CommitPRGeneratorAgent, BranchPRGeneratorAgent
)
from src.github_provider import GitHubProvider

# Initialize session state
if 'provider' not in st.session_state:
    st.session_state.provider = 'openai'
if 'results' not in st.session_state:
    st.session_state.results = {}

# Sidebar - User Info and Configuration
with st.sidebar:
    # User info section
    st.markdown(f"""
    <div class="user-info">
        <div class="user-avatar">👤</div>
        <strong>{st.session_state.get('name', 'User')}</strong>
        <br>
        <small style="color: #a0aec0;">@{st.session_state.get('username', '')}</small>
    </div>
    """, unsafe_allow_html=True)
    
    # Logout button
    authenticator.logout('🚪 Logout', 'sidebar', key='logout')
    
    st.divider()
    
    st.title("⚙️ Configuration")
    
    # Provider Selection
    st.subheader("LLM Provider")
    provider = st.selectbox(
        "Select Provider",
        options=['groq', 'openrouter', 'openai', 'anthropic', 'local'],
        index=0,
        help="Choose your LLM provider"
    )
    
    # Update provider in session state
    if provider != st.session_state.provider:
        st.session_state.provider = provider
        os.environ['LLM_PROVIDER'] = provider
    
    # Provider-specific configuration
    st.subheader("API Configuration")
    
    if provider == 'groq':
        api_key = st.text_input(
            "Groq API Key",
            value=os.getenv('GROQ_API_KEY', ''),
            type="password",
            help="Your Groq API key (free at console.groq.com)"
        )
        if api_key:
            os.environ['GROQ_API_KEY'] = api_key
            
        model = st.selectbox(
            "Model",
            options=['llama-3.1-8b-instant', 'llama-3.3-70b-versatile', 'mixtral-8x7b-32768'],
            help="Groq model to use"
        )
        os.environ['GROQ_MODEL'] = model
    
    elif provider == 'openai':
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
            
        model = st.selectbox(
            "Model",
            options=[
                'amazon/nova-2-lite-v1:free',
                'google/gemini-2.0-flash-exp:free',
                'x-ai/grok-beta'
            ],
            help="OpenRouter model to use"
        )
        os.environ['OPENROUTER_MODEL'] = model
            
    elif provider == 'local':
        base_url = st.text_input(
            "Base URL",
            value=os.getenv('LOCAL_LLM_BASE_URL', 'http://localhost:1234/v1'),
            help="LM Studio or Ollama base URL"
        )
        if base_url:
            os.environ['LOCAL_LLM_BASE_URL'] = base_url
            
        model = st.text_input(
            "Model Name",
            value=os.getenv('LOCAL_LLM_MODEL', 'local-model'),
            help="Model identifier"
        )
        if model:
            os.environ['LOCAL_LLM_MODEL'] = model
    
    # Context Size limit (General Setting)
    st.divider()
    max_context = st.number_input(
        "Max Context Chars (Diff Limit)",
        min_value=1000,
        max_value=128000,
        value=int(os.getenv('LLM_MAX_CONTEXT_CHARS', '12000')),
        step=1000,
        help="Limit input size (diff) to avoid context overflow. ~4 chars = 1 token. Decrease if getting 400 errors."
    )
    os.environ['LLM_MAX_CONTEXT_CHARS'] = str(max_context)
    
    # Current configuration display
    st.divider()
    st.subheader("📊 Current Config")
    config_display = get_llm_config()
    st.json({
        "provider": config_display["provider"],
        "temperature": config_display["temperature"],
        "max_tokens": config_display["max_tokens"],
        "max_context_chars": config_display.get("max_context_chars", 12000)
    })

# Main content
st.title("🤖 PR-Agent Interactive UI")
st.markdown("*Analyze Pull Requests with AI-powered insights*")

# Tool selection
st.subheader("🛠️ Select Analysis Tool")

tool_options = {
    "📋 Code Review": "Comprehensive code review with issues and suggestions",
    "📝 PR Description": "Generate PR title and description",
    "💡 Code Improvement": "Suggest code improvements and refactoring",
    "❓ PR Questions": "Answer questions about the PR",
    "📜 Changelog": "Generate changelog entry",
    "🔧 Generate PR from Commit": "Generate PR title & description from a commit URL",
    "🔀 Generate PR from Branches": "Compare branches and generate PR (includes all commits)"
}

selected_tool = st.selectbox(
    "Choose a tool",
    options=list(tool_options.keys()),
    format_func=lambda x: f"{x} - {tool_options[x]}"
)

# Input section
st.subheader("📥 Input")

# Different input based on tool type
repo_name = None
head_branch = None
base_branch = "main"

if "Branches" in selected_tool:
    st.info("🔀 Compare two branches to generate a PR description with all commits included.")
    repo_name = st.text_input(
        "Repository",
        placeholder="owner/repo (e.g., pankajshakya627/PR-AGENT)",
        help="Repository name in format 'owner/repo'"
    )
    col1, col2 = st.columns(2)
    with col1:
        head_branch = st.text_input(
            "Source Branch (head)",
            placeholder="develop",
            help="The branch with your changes"
        )
    with col2:
        base_branch = st.text_input(
            "Target Branch (base)",
            value="main",
            help="The branch to merge into"
        )
    url_input = repo_name  # Use repo_name for validation
    pr_url = None
    commit_url = None
elif "Commit" in selected_tool:
    url_input = st.text_input(
        "Commit URL",
        placeholder="https://github.com/owner/repo/commit/abc123",
        help="Enter the full GitHub commit URL"
    )
    pr_url = None
    commit_url = url_input
else:
    url_input = st.text_input(
        "Pull Request URL",
        placeholder="https://github.com/owner/repo/pull/123",
        help="Enter the full GitHub PR URL"
    )
    pr_url = url_input
    commit_url = None

# Additional inputs based on tool
additional_input = None
if "Questions" in selected_tool:
    additional_input = st.text_area(
        "Your Question",
        placeholder="What does this PR change?",
        help="Enter your question about the PR"
    )

# Run analysis button
if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
    if not url_input:
        st.error("Please enter a URL")
    else:
        with st.spinner("🔄 Analyzing..."):
            try:
                # Create agent based on selection
                if "Code Review" in selected_tool:
                    agent = CodeReviewAgent()
                elif "PR Description" in selected_tool:
                    agent = PRDescriptionAgent()
                elif "Code Improvement" in selected_tool:
                    agent = CodeImprovementAgent()
                elif "Questions" in selected_tool:
                    agent = PRQuestionsAgent()
                elif "Changelog" in selected_tool:
                    agent = ChangelogAgent()
                elif "Commit" in selected_tool:
                    agent = CommitPRGeneratorAgent()
                elif "Branches" in selected_tool:
                    agent = BranchPRGeneratorAgent()
                
                # Prepare state based on tool type
                if "Branches" in selected_tool:
                    state = {
                        "repo_name": repo_name,
                        "head_branch": head_branch,
                        "base_branch": base_branch
                    }
                elif commit_url:
                    state = {"commit_url": commit_url}
                else:
                    state = {"pr_url": pr_url}
                if additional_input:
                    state["question"] = additional_input
                
                # Run analysis
                result = asyncio.run(agent.execute(state))
                
                # Store and display result
                # Create unique key with timestamp to preserve history and ordering
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                unique_key = f"{selected_tool} ({timestamp})"
                st.session_state.results[unique_key] = result
                
                st.success("✅ Analysis complete!")
                
                # Store for PR creation if it's a commit or branch analysis
                if "Commit" in selected_tool and "pr_from_commit" in result:
                    st.session_state['last_pr_content'] = result.get('pr_from_commit', '')
                    st.session_state['last_commit_url'] = commit_url
                elif "Branches" in selected_tool and "pr_from_branch" in result:
                    st.session_state['last_pr_content'] = result.get('pr_from_branch', '')
                    st.session_state['last_repo_name'] = repo_name
                    st.session_state['last_head_branch'] = head_branch
                    st.session_state['last_base_branch'] = base_branch
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# Display results
if st.session_state.results:
    st.subheader("📊 Results")
    
    # Show latest results first
    for tool, result in reversed(list(st.session_state.results.items())):
        with st.expander(f"Results: {tool}", expanded=True):
            if isinstance(result, dict):
                # Try multiple possible keys
                possible_keys = ['content', 'code_review', 'review', 'description', 'pr_description', 'changelog_entry', 
                                'code_improvements', 'improvements', 'answer', 'response', 'pr_from_commit', 'pr_from_branch']
                content = None
                for key in possible_keys:
                    if key in result:
                        val = result[key]
                        # Handle nested dict case
                        if isinstance(val, dict):
                            content = str(val)
                        else:
                            content = val
                        break
                
                if content is None:
                    content = str(result)
                    
                st.markdown(content)
            else:
                st.markdown(str(result))

# PR Creation Section - shown AFTER generating PR from commit or branches
if st.session_state.get('last_pr_content') and (st.session_state.get('last_commit_url') or st.session_state.get('last_repo_name')):
    st.divider()
    st.subheader("🚀 Create Pull Request on GitHub")
    st.info("👆 **Review the generated PR description above**, then create the PR:")
    
    # Determine repo from commit URL or stored repo_name
    if st.session_state.get('last_commit_url'):
        last_commit_url = st.session_state.get('last_commit_url', '')
        parts = last_commit_url.rstrip('/').split('/')
        try:
            commit_idx = parts.index('commit')
            stored_repo = f"{parts[commit_idx - 2]}/{parts[commit_idx - 1]}"
        except:
            stored_repo = "Unknown"
        stored_head = None
        stored_base = "main"
    else:
        stored_repo = st.session_state.get('last_repo_name', 'Unknown')
        stored_head = st.session_state.get('last_head_branch', '')
        stored_base = st.session_state.get('last_base_branch', 'main')
    
    # Parse title from content
    import re
    pr_content = st.session_state.get('last_pr_content', '')
    title_match = re.search(r'## Title\s*\n\*?\*?([^\n*]+)', pr_content)
    title = title_match.group(1).strip() if title_match else "PR from commit"
    
    # Branch inputs (pre-fill if from branch comparison)
    col1, col2 = st.columns(2)
    with col1:
        pr_head_branch = st.text_input(
            "Source Branch (head)",
            value=stored_head or "",
            placeholder="your-feature-branch",
            help="The branch containing your changes",
            key="pr_create_head"
        )
    with col2:
        pr_base_branch = st.text_input(
            "Target Branch (base)",
            value=stored_base,
            help="The branch to merge into (e.g., main, master)",
            key="pr_create_base"
        )
    
    # Show preview
    if pr_head_branch:
        st.success(f"""
        **📁 Repository:** `{stored_repo}`  
        **🔀 Merge:** `{pr_head_branch}` → `{pr_base_branch}`  
        **📝 Title:** {title}
        """)
        
        if st.button("✅ Create PR on GitHub", type="primary", use_container_width=True):
            try:
                provider = GitHubProvider()
                result = provider.create_pr(
                    repo_name=stored_repo,
                    title=title,
                    body=pr_content,
                    head=pr_head_branch,
                    base=pr_base_branch
                )
                
                if result.get("success"):
                    st.balloons()
                    st.success(f"✅ PR created successfully!")
                    st.markdown(f"### 🔗 [View PR #{result['pr_number']}]({result['pr_url']})")
                    # Clear the stored content
                    st.session_state.pop('last_pr_content', None)
                    st.session_state.pop('last_commit_url', None)
                    st.session_state.pop('last_repo_name', None)
                    st.session_state.pop('last_head_branch', None)
                    st.session_state.pop('last_base_branch', None)
                else:
                    st.error(f"❌ Failed to create PR: {result.get('error')}")
            except Exception as e:
                st.error(f"❌ Error creating PR: {str(e)}")
    else:
        st.warning("⚠️ Enter the source branch name to create a PR")

