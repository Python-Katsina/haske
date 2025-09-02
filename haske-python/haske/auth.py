import time
import json
from typing import Dict, Any, Optional
from _haske_core import sign_cookie, verify_cookie, hash_password, verify_password, generate_random_bytes

def create_session_token(secret: str, payload: dict, expires_in: int = 3600) -> str:
    """Create a signed session token"""
    payload = payload.copy()
    payload["exp"] = int(time.time()) + expires_in
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return sign_cookie(secret, payload_json)

def verify_session_token(secret: str, token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a session token"""
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
    """Create a password hash and salt"""
    return hash_password(password)

def verify_password_hash(password: str, hash_val: bytes, salt: bytes) -> bool:
    """Verify a password against a hash"""
    return verify_password(password, hash_val, salt)

def generate_csrf_token() -> str:
    """Generate a CSRF token"""
    return generate_random_bytes(32).hex()

def validate_csrf_token(token: str, expected: str) -> bool:
    """Validate a CSRF token using constant-time comparison"""
    if len(token) != len(expected):
        return False
    
    # Constant-time comparison to prevent timing attacks
    result = 0
    for x, y in zip(token, expected):
        result |= ord(x) ^ ord(y)
    return result == 0

class AuthManager:
    """Comprehensive authentication manager"""
    
    def __init__(self, secret_key: str, session_cookie_name: str = "session", 
                 session_expiry: int = 3600):
        self.secret_key = secret_key
        self.session_cookie_name = session_cookie_name
        self.session_expiry = session_expiry
    
    def create_session(self, response, user_id: Any, user_data: Dict[str, Any] = None) -> None:
        """Create a session and set cookie"""
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
        """Get session from request"""
        token = request.cookies.get(self.session_cookie_name)
        if not token:
            return None
        
        return verify_session_token(self.secret_key, token)
    
    def clear_session(self, response) -> None:
        """Clear session cookie"""
        response.delete_cookie(self.session_cookie_name)
    
    def login_required(self, handler):
        """Decorator to require authentication"""
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
        """Decorator to require specific roles"""
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