# haske/auth.py
"""
Authentication and authorization utilities for Haske.

This module provides comprehensive authentication management including
session tokens, password hashing, CSRF protection, and role-based access control.
"""

import time
import json
from typing import Dict, Any, Optional
from _haske_core import sign_cookie, verify_cookie, hash_password, verify_password, generate_random_bytes

def create_session_token(secret: str, payload: dict, expires_in: int = 3600) -> str:
    """
    Create a signed session token.
    
    Args:
        secret: Secret key for signing
        payload: Token payload data
        expires_in: Token expiration time in seconds, defaults to 3600 (1 hour)
        
    Returns:
        str: Signed session token
        
    Example:
        >>> token = create_session_token("secret", {"user_id": 123})
    """
    payload = payload.copy()
    payload["exp"] = int(time.time()) + expires_in
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return sign_cookie(secret, payload_json)

def verify_session_token(secret: str, token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a session token.
    
    Args:
        secret: Secret key used for signing
        token: Token to verify
        
    Returns:
        Optional[dict]: Decoded payload if valid, None otherwise
        
    Example:
        >>> payload = verify_session_token("secret", token)
    """
    payload_str = verify_cookie(secret, token)
    if payload_str is None:
        return None
    
    try:
        payload = json.loads(payload_str)
        # Check expiration
        if "exp" in payload and payload["exp"] < time.time():
            return None
        return payload
    except json.JSONDecodeError:
        return None

def create_password_hash(password: str) -> tuple:
    """
    Create a password hash and salt.
    
    Args:
        password: Plain text password
        
    Returns:
        tuple: (hash_bytes, salt_bytes) tuple
        
    Example:
        >>> hash_val, salt = create_password_hash("password123")
    """
    return hash_password(password)

def verify_password_hash(password: str, hash_val: bytes, salt: bytes) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        password: Plain text password to verify
        hash_val: Password hash to compare against
        salt: Salt used in hashing
        
    Returns:
        bool: True if password matches hash, False otherwise
        
    Example:
        >>> is_valid = verify_password_hash("password123", hash_val, salt)
    """
    return verify_password(password, hash_val, salt)

def generate_csrf_token() -> str:
    """
    Generate a CSRF token.
    
    Returns:
        str: Cryptographically secure random token as hex string
        
    Example:
        >>> token = generate_csrf_token()
    """
    return generate_random_bytes(32).hex()

def validate_csrf_token(token: str, expected: str) -> bool:
    """
    Validate a CSRF token using constant-time comparison.
    
    Args:
        token: Token to validate
        expected: Expected token value
        
    Returns:
        bool: True if tokens match, False otherwise
        
    Note:
        Uses constant-time comparison to prevent timing attacks.
    """
    if len(token) != len(expected):
        return False
    
    # Constant-time comparison to prevent timing attacks
    result = 0
    for x, y in zip(token, expected):
        result |= ord(x) ^ ord(y)
    return result == 0

class AuthManager:
    """
    Comprehensive authentication manager.
    
    Provides session management, authentication decorators, and role-based
    access control for Haske applications.
    
    Attributes:
        secret_key (str): Secret key for token signing
        session_cookie_name (str): Session cookie name, defaults to "session"
        session_expiry (int): Session expiration in seconds, defaults to 3600
    """
    
    def __init__(self, secret_key: str, session_cookie_name: str = "session", 
                 session_expiry: int = 3600):
        """
        Initialize authentication manager.
        
        Args:
            secret_key: Secret key for token signing
            session_cookie_name: Session cookie name, defaults to "session"
            session_expiry: Session expiration in seconds, defaults to 3600
        """
        self.secret_key = secret_key
        self.session_cookie_name = session_cookie_name
        self.session_expiry = session_expiry
    
    def create_session(self, response, user_id: Any, user_data: Dict[str, Any] = None) -> None:
        """
        Create a session and set cookie.
        
        Args:
            response: Response object to set cookie on
            user_id: User identifier
            user_data: Additional user data to include in session
            
        Example:
            >>> auth.create_session(response, user.id, {"username": user.name})
        """
        payload = {"user_id": user_id}
        if user_data:
            payload.update(user_data)
        
        token = create_session_token(self.secret_key, payload, self.session_expiry)
        
        # Set cookie on response
        response.set_cookie(
            self.session_cookie_name,
            token,
            max_age=self.session_expiry,
            httponly=True,
            secure=True,  # Should be True in production
            samesite="lax"
        )
    
    def get_session(self, request) -> Optional[Dict[str, Any]]:
        """
        Get session from request.
        
        Args:
            request: Request object
            
        Returns:
            Optional[dict]: Session data if valid, None otherwise
        """
        token = request.cookies.get(self.session_cookie_name)
        if not token:
            return None
        
        return verify_session_token(self.secret_key, token)
    
    def clear_session(self, response) -> None:
        """
        Clear session cookie.
        
        Args:
            response: Response object to clear cookie from
        """
        response.delete_cookie(self.session_cookie_name)
    
    def login_required(self, handler):
        """
        Decorator to require authentication.
        
        Args:
            handler: Route handler function
            
        Returns:
            Callable: Wrapped handler that requires authentication
            
        Raises:
            AuthenticationError: If no valid session is found
            
        Example:
            @app.route("/protected")
            @auth.login_required
            async def protected_route(request):
                return {"user": request.user}
        """
        from functools import wraps
        from .exceptions import AuthenticationError
        
        @wraps(handler)
        async def wrapper(request, *args, **kwargs):
            session = self.get_session(request)
            if not session:
                raise AuthenticationError("Authentication required")
            
            # Add user info to request
            request.user = session
            return await handler(request, *args, **kwargs)
        
        return wrapper
    
    def roles_required(self, *roles):
        """
        Decorator to require specific roles.
        
        Args:
            *roles: Required role names
            
        Returns:
            Callable: Decorator function
            
        Raises:
            AuthenticationError: If no valid session is found
            PermissionError: If user doesn't have required roles
            
        Example:
            @app.route("/admin")
            @auth.roles_required("admin", "moderator")
            async def admin_dashboard(request):
                return {"message": "Welcome admin"}
        """
        from functools import wraps
        from .exceptions import PermissionError
        
        def decorator(handler):
            @wraps(handler)
            async def wrapper(request, *args, **kwargs):
                session = self.get_session(request)
                if not session:
                    raise AuthenticationError("Authentication required")
                
                user_roles = session.get("roles", [])
                if not any(role in user_roles for role in roles):
                    raise PermissionError("Insufficient permissions")
                
                request.user = session
                return await handler(request, *args, **kwargs)
            
            return wrapper
        return decorator