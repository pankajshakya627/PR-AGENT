"""
Streamlit UI for PR-Agent MCP Server

A web interface to interact with the PR-Agent FastMCP server.

Authentication Features:
    - **Login**: Secure login with username/password using bcrypt hashing
    - **Registration**: New user registration with email and password validation
    - **Forgot Password**: Email-based verification code flow for secure password reset
    - **Change Password**: Logged-in users can update their password via sidebar

Configuration:
    - User credentials stored in config/auth_config.yaml
    - Cookie-based session management with configurable expiry
    - Uses streamlit-authenticator library for secure authentication

Security Notes:
    - Passwords are hashed using bcrypt (salt rounds: 12)
    - Session cookies are encrypted with a secret key
    - Forgot password displays new password on screen (no email delivery configured)
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
import secrets
from pathlib import Path
import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Config file path
CONFIG_FILE = project_root / "config" / "auth_config.yaml"
KNOWN_ADMIN123_HASH = "$2b$12$G5j7jSSt8xOE9yICktUqGuIT3GrJGxHTvSqvWDJVtlcEOxtjH.CLy"

_secure_auth_key = None

def load_config():
    """Load authentication config from YAML file with environment overrides."""
    config = None
    if not CONFIG_FILE.exists():
        # Create default config
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        default_config = {
            'credentials': {
                'usernames': {}
            },
            'cookie': {
                'expiry_days': 30,
                'key': secrets.token_hex(32),  # Dynamically generate secure default key
                'name': 'pr_agent_auth'
            },
            'pre-authorized': {
                'emails': []
            }
        }
        admin_hash = os.getenv("ADMIN_PASSWORD_HASH", "").strip()
        if admin_hash:
            default_config['credentials']['usernames']['admin'] = {
                'email': 'admin@pragent.com',
                'name': 'Administrator',
                'password': admin_hash
            }
            default_config['pre-authorized']['emails'].append('admin@pragent.com')
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(default_config, f)
        config = default_config
    else:
        with open(CONFIG_FILE) as f:
            config = yaml.load(f, Loader=SafeLoader)
            
    # Apply dynamic secure key generation if weak static default is detected
    global _secure_auth_key
    if 'cookie' in config:
        cookie_key = os.getenv("AUTH_COOKIE_KEY")
        if cookie_key and cookie_key.strip():
            config['cookie']['key'] = cookie_key.strip()
        elif config['cookie'].get('key') in ('pr_agent_auth_secret_key', 'YOUR_SECRET_KEY_HERE', '', None):
            if not _secure_auth_key:
                _secure_auth_key = secrets.token_hex(32)
            config['cookie']['key'] = _secure_auth_key
            
    # Apply environment overrides for user credentials to prevent committing password hashes
    if 'credentials' in config and 'usernames' in config['credentials']:
        usernames = config['credentials']['usernames']
        for user, env_var in [('admin', 'ADMIN_PASSWORD_HASH'), ('pankaj', 'PANKAJ_PASSWORD_HASH')]:
            pwd_hash = os.getenv(env_var)
            if pwd_hash and pwd_hash.strip():
                if user not in usernames:
                    usernames[user] = {'email': f'{user}@pragent.com', 'name': user.capitalize()}
                usernames[user]['password'] = pwd_hash.strip()
        admin_user = usernames.get('admin')
        unsafe_admin_passwords = {KNOWN_ADMIN123_HASH, "CHANGE_ME_IMMEDIATELY", "", None}
        if admin_user and admin_user.get('password') in unsafe_admin_passwords and not os.getenv("ADMIN_PASSWORD_HASH"):
            usernames.pop('admin')
                
    return config


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
    
    /* Password display styling */
    .password-box {
        padding: 1.5rem;
        border-radius: 10px;
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.1), rgba(0, 212, 255, 0.1));
        border: 2px dashed rgba(124, 58, 237, 0.4);
        text-align: center;
        margin: 1rem 0;
    }
    
    .password-box code {
        font-size: 1.4rem;
        font-weight: 600;
        letter-spacing: 2px;
        color: #7c3aed;
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
        
        # Tabs for Login, Register, and Forgot Password
        tab1, tab2, tab3 = st.tabs(["🔐 Login", "📝 Register", "🔑 Forgot Password"])
        
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
        
        with tab3:
            # Forgot Password with Email Verification
            st.markdown("### 🔑 Reset Your Password")
            
            # Import email utilities
            from src.email_utils import generate_verification_code, send_verification_email, is_code_valid
            from datetime import datetime
            
            # Initialize session state for password reset flow
            if 'reset_step' not in st.session_state:
                st.session_state.reset_step = 1
            if 'reset_username' not in st.session_state:
                st.session_state.reset_username = None
            if 'reset_email' not in st.session_state:
                st.session_state.reset_email = None
            if 'reset_code' not in st.session_state:
                st.session_state.reset_code = None
            if 'reset_code_time' not in st.session_state:
                st.session_state.reset_code_time = None
            
            # Step indicator
            step = st.session_state.reset_step
            st.markdown(f"**Step {step} of 3**")
            st.progress(step / 3)
            
            # ========== STEP 1: Enter Username ==========
            if step == 1:
                st.markdown("Enter your username to receive a verification code via email.")
                
                with st.form("reset_step1", clear_on_submit=False):
                    reset_username = st.text_input("👤 Username", placeholder="Enter your username")
                    submit_step1 = st.form_submit_button("📧 Send Verification Code", use_container_width=True)
                    
                    if submit_step1:
                        if not reset_username:
                            st.error("❌ Please enter your username")
                        elif reset_username not in config['credentials']['usernames']:
                            st.error("❌ Username not found. Please check and try again.")
                        else:
                            # Get user email
                            user_data = config['credentials']['usernames'][reset_username]
                            user_email = user_data.get('email', '')
                            
                            if not user_email:
                                st.error("❌ No email associated with this account.")
                            else:
                                # Generate and send verification code
                                code = generate_verification_code()
                                
                                try:
                                    success = send_verification_email(user_email, code, reset_username)
                                    
                                    if success:
                                        # Store in session state
                                        st.session_state.reset_username = reset_username
                                        st.session_state.reset_email = user_email
                                        st.session_state.reset_code = code
                                        st.session_state.reset_code_time = datetime.now()
                                        st.session_state.reset_step = 2
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to send email. Please try again later.")
                                except ValueError as e:
                                    st.error(f"❌ Email configuration error: {e}")
                                    st.info("💡 Please configure SMTP settings in your .env file.")
            
            # ========== STEP 2: Enter Verification Code ==========
            elif step == 2:
                # Mask email for display
                email = st.session_state.reset_email or ""
                masked_email = email[:3] + "***" + email[email.find("@"):] if "@" in email else email
                
                st.success(f"✅ Verification code sent to **{masked_email}**")
                st.info("⏰ Code expires in 5 minutes. Check your spam folder if not received.")
                
                with st.form("reset_step2", clear_on_submit=False):
                    entered_code = st.text_input("🔢 Verification Code", placeholder="Enter 6-digit code", max_chars=6)
                    submit_step2 = st.form_submit_button("✅ Verify Code", use_container_width=True)
                    
                    if submit_step2:
                        if not entered_code:
                            st.error("❌ Please enter the verification code")
                        else:
                            is_valid, error_msg = is_code_valid(
                                st.session_state.reset_code,
                                st.session_state.reset_code_time,
                                entered_code
                            )
                            
                            if is_valid:
                                st.session_state.reset_step = 3
                                st.rerun()
                            else:
                                st.error(f"❌ {error_msg}")
                
                # Back button
                if st.button("← Back to Step 1"):
                    st.session_state.reset_step = 1
                    st.session_state.reset_code = None
                    st.rerun()
            
            # ========== STEP 3: Set New Password ==========
            elif step == 3:
                st.success("✅ Code verified! Now set your new password.")
                
                with st.form("reset_step3", clear_on_submit=False):
                    new_password = st.text_input("🔒 New Password", type="password", placeholder="Min 8 characters")
                    confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Repeat password")
                    submit_step3 = st.form_submit_button("🔐 Update Password", use_container_width=True)
                    
                    if submit_step3:
                        errors = []
                        
                        if len(new_password) < 8:
                            errors.append("Password must be at least 8 characters")
                        if not any(c.isupper() for c in new_password):
                            errors.append("Password must contain at least one uppercase letter")
                        if not any(c.islower() for c in new_password):
                            errors.append("Password must contain at least one lowercase letter")
                        if not any(c.isdigit() for c in new_password):
                            errors.append("Password must contain at least one number")
                        if new_password != confirm_password:
                            errors.append("Passwords do not match")
                        
                        if errors:
                            for error in errors:
                                st.error(f"❌ {error}")
                        else:
                            # Update password
                            username = st.session_state.reset_username
                            hashed_pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                            config['credentials']['usernames'][username]['password'] = hashed_pw
                            save_config(config)
                            
                            # Clear session state
                            st.session_state.reset_step = 1
                            st.session_state.reset_username = None
                            st.session_state.reset_email = None
                            st.session_state.reset_code = None
                            st.session_state.reset_code_time = None
                            
                            st.success("🎉 Password updated successfully! You can now login with your new password.")
                            st.balloons()
                
                # Back button
                if st.button("← Back to Step 2"):
                    st.session_state.reset_step = 2
                    st.rerun()


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
from src.github_commenter import GitHubCommenter

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
    authenticator.logout('🚪 Logout', 'sidebar', key='sidebar_logout_btn')
    
    # Password Reset for logged-in users
    with st.expander("🔐 Change Password"):
        st.markdown("Update your account password.")
        try:
            if authenticator.reset_password(
                st.session_state['username'],
                location='main',
                key='reset_password',
                clear_on_submit=True
            ):
                save_config(config)
                st.success("✅ Password changed successfully!")
                st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")
    
    st.divider()
    
    st.title("⚙️ Configuration")
    
    # Provider Selection
    st.subheader("LLM Provider")
    provider = st.selectbox(
        "Select Provider",
        options=['groq', 'nvidia', 'openrouter', 'openai', 'anthropic', 'local'],
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
            
        groq_models = ['llama-3.1-8b-instant', 'llama-3.3-70b-versatile', 'mixtral-8x7b-32768']
        # Use CLI model as default if provided and valid
        cli_model = st.session_state.get('cli_model')
        default_groq_model = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
        groq_index = groq_models.index(default_groq_model) if default_groq_model in groq_models else 0
        model = st.selectbox(
            "Model",
            options=groq_models,
            index=groq_index,
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
            
        openrouter_models = [
            'xiaomi/mimo-v2-flash:free',
            'mistralai/devstral-2512:free',
            'google/gemini-2.0-flash-exp:free',
            'x-ai/grok-beta'
        ]
        # Use CLI model as default if provided and valid
        default_or_model = os.getenv('OPENROUTER_MODEL', 'xiaomi/mimo-v2-flash:free')
        or_index = openrouter_models.index(default_or_model) if default_or_model in openrouter_models else 0
        model = st.selectbox(
            "Model",
            options=openrouter_models,
            index=or_index,
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
            
    elif provider == 'nvidia':
        api_key = st.text_input(
            "NVIDIA API Key",
            value=os.getenv('NVIDIA_API_KEY', ''),
            type="password",
            help="Your NVIDIA API key (free at build.nvidia.com)"
        )
        if api_key:
            os.environ['NVIDIA_API_KEY'] = api_key
            
        base_url = st.text_input(
            "Base URL",
            value=os.getenv('NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1'),
            help="NVIDIA API endpoint or local Ollama base URL"
        )
        if base_url:
            os.environ['NVIDIA_BASE_URL'] = base_url
            
        model = st.text_input(
            "Model Name",
            value=os.getenv('NVIDIA_MODEL', 'nvidia/nemotron-3-super-120b-a12b'),
            help="NVIDIA or Ollama model name"
        )
        if model:
            os.environ['NVIDIA_MODEL'] = model
    
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

    # Optional Langfuse observability
    st.divider()
    st.subheader("Langfuse Observability")
    langfuse_enabled = st.checkbox(
        "Enable Langfuse tracing",
        value=os.getenv('LANGFUSE_ENABLED', '').lower() in ('1', 'true', 'yes', 'on') or bool(os.getenv('LANGFUSE_PUBLIC_KEY')),
        help="Capture LangChain traces for monitoring, debugging, latency, and token usage."
    )
    os.environ['LANGFUSE_ENABLED'] = "true" if langfuse_enabled else "false"
    if langfuse_enabled:
        public_key = st.text_input(
            "Langfuse Public Key",
            value=os.getenv('LANGFUSE_PUBLIC_KEY', ''),
            type="password",
            help="Your Langfuse project public key"
        )
        if public_key:
            os.environ['LANGFUSE_PUBLIC_KEY'] = public_key

        secret_key = st.text_input(
            "Langfuse Secret Key",
            value=os.getenv('LANGFUSE_SECRET_KEY', ''),
            type="password",
            help="Your Langfuse project secret key"
        )
        if secret_key:
            os.environ['LANGFUSE_SECRET_KEY'] = secret_key

        base_url = st.text_input(
            "Langfuse Base URL",
            value=os.getenv('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com'),
            help="Use https://us.cloud.langfuse.com for the US region"
        )
        if base_url:
            os.environ['LANGFUSE_BASE_URL'] = base_url
    
    # Current configuration display
    st.divider()
    st.subheader("📊 Current Config")
    config_display = get_llm_config()
    st.json({
        "provider": config_display["provider"],
        "temperature": config_display["temperature"],
        "max_tokens": config_display["max_tokens"],
        "max_context_chars": config_display.get("max_context_chars", 12000),
        "langfuse_tracing": os.getenv('LANGFUSE_ENABLED', 'false')
    })
    
    st.divider()
    st.subheader("🛡️ Security Audit Logs")
    with st.expander("View Access Audit Trails"):
        from src.tenant import get_tenant_audit_logs
        logs = get_tenant_audit_logs(limit=25)
        if logs:
            # Display inside a scrollable box
            logs_formatted = "\n".join(logs)
            st.text_area("Audit Trails", value=logs_formatted, height=200, disabled=True)
        else:
            st.caption("No audit events recorded yet.")

# Main content
st.title("🤖 PR-Agent Interactive UI")
st.markdown("*Analyze Pull Requests with AI-powered insights*")

# Tenant Isolation Badge
st.markdown(f"""
<div style="display: flex; gap: 12px; align-items: center; background: rgba(124, 58, 237, 0.1); border: 1px solid rgba(124, 58, 237, 0.3); padding: 12px 18px; border-radius: 12px; margin-bottom: 22px; margin-top: 10px;">
    <span style="font-size: 1.4rem;">🔒</span>
    <div>
        <strong style="color: #7c3aed; font-size: 1.05rem;">Tenant Isolation: Level 1 Metadata Filtering Enabled</strong><br/>
        <span style="color: #a0aec0; font-size: 0.9rem;">Active Scope: <strong>{st.session_state.get('username', 'default_tenant')}</strong> (Strict boundary segregation active)</span>
    </div>
</div>
""", unsafe_allow_html=True)

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
    
    # Commit limit option
    commit_limit = st.number_input(
        "Limit to last N commits (0 = all)",
        min_value=0,
        max_value=100,
        value=0,
        help="Limit analysis to the last N commits. Set to 0 to include all commits."
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
                        "base_branch": base_branch,
                        "commit_limit": commit_limit if commit_limit > 0 else None
                    }
                elif commit_url:
                    state = {"commit_url": commit_url}
                else:
                    state = {"pr_url": pr_url}
                if additional_input:
                    state["question"] = additional_input
                
                # Inject active tenant context strictly before execution
                state["tenant_id"] = st.session_state.get("username", "default_tenant")
                
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
                
                # Store code review result for posting to GitHub
                if "Code Review" in selected_tool:
                    review_content = result.get('code_review') or result.get('review') or result.get('content', '')
                    if review_content:
                        st.session_state['last_code_review'] = review_content
                        st.session_state['last_review_pr_url'] = pr_url
                
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

# Post Code Review to GitHub Section
if st.session_state.get('last_code_review') and st.session_state.get('last_review_pr_url'):
    st.divider()
    st.subheader("💬 Post Review to GitHub")
    
    # Parse PR URL to get repo and PR number
    review_pr_url = st.session_state.get('last_review_pr_url', '')
    try:
        parts = review_pr_url.rstrip('/').split('/')
        pr_idx = parts.index('pull')
        review_repo = f"{parts[pr_idx - 2]}/{parts[pr_idx - 1]}"
        review_pr_number = int(parts[pr_idx + 1])
        
        st.info(f"""
        📁 **Repository:** `{review_repo}`  
        🔢 **PR Number:** `#{review_pr_number}`
        """)
        
        # Preview the comment
        with st.expander("📝 Preview Comment", expanded=False):
            st.markdown(st.session_state.get('last_code_review', ''))
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("💬 Post as PR Comment", type="primary", use_container_width=True):
                try:
                    commenter = GitHubCommenter()
                    
                    # Format the comment with PR-Agent branding
                    comment_body = f"""## 🤖 PR-Agent Code Review

{st.session_state.get('last_code_review', '')}

---
*Generated by [PR-Agent](https://github.com/pankajshakya627/PR-AGENT) | Powered by AI*
"""
                    
                    success = commenter.post_comment(
                        repo=review_repo,
                        pr_number=review_pr_number,
                        body=comment_body
                    )
                    
                    if success:
                        st.balloons()
                        st.success(f"✅ Code review posted to PR #{review_pr_number}!")
                        st.markdown(f"[🔗 View on GitHub]({review_pr_url})")
                        # Clear the stored review
                        st.session_state.pop('last_code_review', None)
                        st.session_state.pop('last_review_pr_url', None)
                    else:
                        st.error("❌ Failed to post comment. Check your GitHub token permissions.")
                except ValueError as e:
                    st.error(f"❌ GitHub token not configured: {e}")
                    st.info("💡 Set GITHUB_TOKEN in your .env file with repo write access.")
                except Exception as e:
                    st.error(f"❌ Error posting comment: {str(e)}")
        
        with col2:
            if st.button("🗑️ Discard", use_container_width=True):
                st.session_state.pop('last_code_review', None)
                st.session_state.pop('last_review_pr_url', None)
                st.rerun()
                
    except (ValueError, IndexError):
        st.error("❌ Could not parse PR URL. Please ensure it's a valid GitHub PR URL.")
        if st.button("🗑️ Clear"):
            st.session_state.pop('last_code_review', None)
            st.session_state.pop('last_review_pr_url', None)
            st.rerun()

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
    
    # Parse title from content (handle error case where content is dict)
    import re
    pr_content = st.session_state.get('last_pr_content', '')
    if isinstance(pr_content, dict):
        # Error case - clear and skip PR creation
        if 'error' in pr_content:
            st.error(f"❌ Error in PR generation: {pr_content.get('error')}")
            st.session_state.pop('last_pr_content', None)
            st.stop()
        pr_content = str(pr_content)
    title_match = re.search(r'## Title\s*\n\*?\*?([^\n*]+)', pr_content)
    title = title_match.group(1).strip() if title_match else "PR from commit"
    
    # Fetch branches from repository for dropdown
    try:
        provider = GitHubProvider()
        available_branches = provider.get_repo_branches(stored_repo)
        # Sort with common defaults first
        priority_branches = ['main', 'master', 'develop', 'dev']
        sorted_branches = sorted(available_branches, 
                                 key=lambda x: (x not in priority_branches, x))
    except Exception as e:
        sorted_branches = ['main', 'master', 'develop']  # Fallback
        st.warning(f"⚠️ Could not fetch branches: {str(e)[:50]}...")
    
    # Branch selection dropdowns
    col1, col2 = st.columns(2)
    with col1:
        # Find default index for head branch
        head_default = stored_head if stored_head in sorted_branches else (sorted_branches[0] if sorted_branches else "")
        head_idx = sorted_branches.index(head_default) if head_default in sorted_branches else 0
        
        pr_head_branch = st.selectbox(
            "Source Branch (head)",
            options=sorted_branches,
            index=head_idx,
            help="The branch containing your changes",
            key="pr_create_head"
        )
    with col2:
        # Find default index for base branch  
        base_default = stored_base if stored_base in sorted_branches else "main"
        base_idx = sorted_branches.index(base_default) if base_default in sorted_branches else 0
        
        pr_base_branch = st.selectbox(
            "Target Branch (base)",
            options=sorted_branches,
            index=base_idx,
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
                    action = result.get("action", "created")
                    if action == "updated":
                        st.success(f"✅ Existing PR updated successfully!")
                    else:
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
