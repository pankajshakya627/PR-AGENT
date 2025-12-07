"""
User Authentication Module
Handles registration, login, and security validation.
"""
import json
import hashlib
import secrets
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# Path to users database
USERS_FILE = Path(__file__).parent.parent / "data" / "users.json"


def _load_users() -> Dict:
    """Load users from JSON file."""
    if not USERS_FILE.exists():
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USERS_FILE.write_text('{"users": []}')
        return {"users": []}
    
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def _save_users(data: Dict) -> None:
    """Save users to JSON file."""
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def hash_password(password: str) -> str:
    """Hash password with salt using SHA-256."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    try:
        salt, hashed = stored_hash.split("$")
        return hashlib.sha256((password + salt).encode()).hexdigest() == hashed
    except ValueError:
        return False


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not email:
        return False, "Email is required"
    if not re.match(pattern, email):
        return False, "Invalid email format"
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username format."""
    if not username:
        return False, "Username is required"
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 20:
        return False, "Username must be at most 20 characters"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    return True, ""


def email_exists(email: str) -> bool:
    """Check if email already exists."""
    data = _load_users()
    return any(u["email"].lower() == email.lower() for u in data["users"])


def username_exists(username: str) -> bool:
    """Check if username already exists."""
    data = _load_users()
    return any(u["username"].lower() == username.lower() for u in data["users"])


def create_user(username: str, email: str, password: str) -> Tuple[bool, str]:
    """
    Create a new user with validation.
    Returns (success, message).
    """
    # Validate inputs
    valid, msg = validate_username(username)
    if not valid:
        return False, msg
    
    valid, msg = validate_email(email)
    if not valid:
        return False, msg
    
    valid, msg = validate_password(password)
    if not valid:
        return False, msg
    
    # Check for duplicates
    if username_exists(username):
        return False, "Username already exists"
    
    if email_exists(email):
        return False, "Email already registered"
    
    # Create user
    data = _load_users()
    user = {
        "id": secrets.token_hex(8),
        "username": username,
        "email": email.lower(),
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat()
    }
    data["users"].append(user)
    _save_users(data)
    
    logger.info(f"User created: {username}")
    return True, "Account created successfully!"


def authenticate_user(username_or_email: str, password: str) -> Tuple[bool, Optional[Dict], str]:
    """
    Authenticate user by username or email.
    Returns (success, user_data, message).
    """
    if not username_or_email or not password:
        return False, None, "Username/email and password are required"
    
    data = _load_users()
    
    # Find user by username or email
    user = None
    for u in data["users"]:
        if u["username"].lower() == username_or_email.lower() or \
           u["email"].lower() == username_or_email.lower():
            user = u
            break
    
    if not user:
        return False, None, "Invalid username or email"
    
    if not verify_password(password, user["password_hash"]):
        return False, None, "Incorrect password"
    
    # Return user data without password hash
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    logger.info(f"User logged in: {user['username']}")
    return True, safe_user, "Login successful!"


def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get user by ID."""
    data = _load_users()
    for user in data["users"]:
        if user["id"] == user_id:
            return {k: v for k, v in user.items() if k != "password_hash"}
    return None
