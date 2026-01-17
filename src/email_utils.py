"""
Email Utilities Module

Handles email sending for password reset verification codes.

Configuration (via environment variables):
    - SMTP_SERVER: SMTP server address (default: smtp.gmail.com)
    - SMTP_PORT: SMTP port (default: 587)
    - SMTP_EMAIL: Sender email address
    - SMTP_PASSWORD: App password for SMTP authentication

Usage:
    from src.email_utils import send_verification_email, generate_verification_code
    
    code = generate_verification_code()
    success = send_verification_email("user@example.com", code, "username")
"""

import os
import random
import string
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def generate_verification_code(length: int = 6) -> str:
    """
    Generate a random numeric verification code.
    
    Args:
        length: Length of the code (default: 6)
        
    Returns:
        A random numeric string of specified length
    """
    return ''.join(random.choices(string.digits, k=length))


def get_smtp_config() -> Tuple[str, int, str, str]:
    """
    Get SMTP configuration from environment variables.
    
    Supports both SMTP_SERVER and SMTP_HOST variable names.
    
    Returns:
        Tuple of (server, port, email, password)
        
    Raises:
        ValueError: If required configuration is missing
    """
    # Support both SMTP_SERVER and SMTP_HOST
    server = os.getenv('SMTP_SERVER') or os.getenv('SMTP_HOST', 'smtp.gmail.com')
    port = int(os.getenv('SMTP_PORT', '587'))
    email = os.getenv('SMTP_EMAIL', '')
    password = os.getenv('SMTP_PASSWORD', '')
    
    # Remove spaces from password (Gmail app passwords are sometimes copied with spaces)
    # Note: Ensure your SMTP password in .env does not contain leading/trailing spaces.
    password = password.strip() if password else ''
    
    if not email or not password:
        raise ValueError(
            "SMTP_EMAIL and SMTP_PASSWORD must be set in environment variables. "
            "Please configure these in your .env file."
        )
    
    return server, port, email, password


def send_verification_email(to_email: str, code: str, username: str) -> bool:
    """
    Send a verification code email for password reset.
    
    Args:
        to_email: Recipient email address
        code: Verification code to send
        username: Username for personalization
        
    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        server, port, sender_email, password = get_smtp_config()
        
        # Create the email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '🔐 PR-Agent Password Reset Code'
        msg['From'] = f'PR-Agent <{sender_email}>'
        msg['To'] = to_email
        
        # Plain text version
        text_content = f"""
PR-Agent Password Reset

Hello {username},

You requested to reset your password for PR-Agent.

Your verification code is: {code}

This code will expire in 5 minutes.

If you did not request this reset, please ignore this email.

Best regards,
PR-Agent Team
"""
        
        # HTML version
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .header h1 {{ color: #7c3aed; margin: 0; }}
        .code-box {{ 
            background: linear-gradient(135deg, rgba(124, 58, 237, 0.1), rgba(0, 212, 255, 0.1));
            border: 2px dashed #7c3aed;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
        }}
        .code {{ 
            font-size: 32px; 
            font-weight: bold; 
            color: #7c3aed; 
            letter-spacing: 8px;
            font-family: monospace;
        }}
        .warning {{ 
            background: #fef3cd; 
            border-left: 4px solid #ffc107; 
            padding: 10px 15px; 
            margin: 20px 0;
            border-radius: 4px;
            color: #856404;
        }}
        .footer {{ 
            text-align: center; 
            color: #666; 
            font-size: 12px; 
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 PR-Agent</h1>
            <p>Password Reset Request</p>
        </div>
        
        <p>Hello <strong>{username}</strong>,</p>
        
        <p>You requested to reset your password for PR-Agent. Use the verification code below:</p>
        
        <div class="code-box">
            <div class="code">{code}</div>
        </div>
        
        <div class="warning">
            ⏰ This code will expire in <strong>5 minutes</strong>.
        </div>
        
        <p>If you did not request this password reset, please ignore this email. Your password will remain unchanged.</p>
        
        <div class="footer">
            <p>This email was sent by PR-Agent</p>
            <p>Intelligent Pull Request Analysis</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Attach both versions
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send the email
        with smtplib.SMTP(server, port) as smtp:
            smtp.starttls()
            smtp.login(sender_email, password)
            smtp.send_message(msg)
        
        logger.info(f"Verification email sent to {to_email} for user {username}")
        return True
        
    except ValueError as e:
        logger.error(f"SMTP configuration error: {e}")
        raise
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        raise ValueError("Email authentication failed. Check your SMTP credentials.")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        return False


def is_code_valid(stored_code: str, stored_time: datetime, entered_code: str, 
                  expiry_minutes: int = 5) -> Tuple[bool, str]:
    """
    Validate a verification code.
    
    Args:
        stored_code: The original generated code
        stored_time: When the code was generated
        entered_code: The code entered by the user
        expiry_minutes: Minutes until code expires (default: 5)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if code has expired
    if datetime.now() > stored_time + timedelta(minutes=expiry_minutes):
        return False, "Verification code has expired. Please request a new one."
    
    # Check if code matches
    if stored_code != entered_code:
        return False, "Invalid verification code. Please try again."
    
    return True, ""
