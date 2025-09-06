# haske/routing.py
"""
Routing utilities and path parameter converters for Haske framework.

This module provides enhanced routing capabilities with type conversion
for path parameters and flexible route pattern matching.
"""

from typing import Callable, List, Any, Dict
from starlette.routing import Route as StarletteRoute
import re

# Import Rust path functions if available
try:
    from _haske_core import compile_path, match_path
    HAS_RUST_ROUTING = True
except ImportError:
    HAS_RUST_ROUTING = False

class Route(StarletteRoute):
    """
    Haske Route class extending Starlette's Route.
    
    Provides enhanced route handling with additional functionality.
    """

    def __init__(self, path: str, endpoint: Callable, methods: List[str] = None, 
                 name: str = None, **kwargs):
        """
        Initialize route.
        
        Args:
            path: URL path pattern
            endpoint: Route handler function
            methods: HTTP methods, defaults to ["GET"]
            name: Route name, defaults to None
            **kwargs: Additional route options
        """
        # Convert path to regex using Rust if available
        if HAS_RUST_ROUTING:
            try:
                # Try to compile with Rust
                regex_path = compile_path(path)
                # Use the compiled regex path
                super().__init__(regex_path, endpoint, methods=methods or ["GET"], name=name, **kwargs)
                return
            except Exception:
                # Fall back to Starlette if Rust compilation fails
                pass
        
        # Fall back to Starlette path handling
        super().__init__(path, endpoint, methods=methods or ["GET"], name=name, **kwargs)

class PathConverter:
    """
    Base class for path parameter converters.
    
    Provides default string conversion behavior.
    
    Attributes:
        regex: Regular expression pattern for parameter matching
    """
    
    regex = "[^/]+"
    
    def to_python(self, value: str) -> Any:
        """
        Convert string value to Python type.
        
        Args:
            value: String value from URL
            
        Returns:
            Any: Converted value
        """
        return value
    
    def to_string(self, value: Any) -> str:
        """
        Convert Python value to string for URL generation.
        
        Args:
            value: Python value
            
        Returns:
            str: String representation
        """
        return str(value)

class IntConverter(PathConverter):
    """
    Converter for integer path parameters.
    """
    
    regex = "[0-9]+"
    
    def to_python(self, value: str) -> int:
        """
        Convert string to integer.
        
        Args:
            value: String representation of integer
            
        Returns:
            int: Converted integer
            
        Raises:
            ValueError: If value cannot be converted to integer
        """
        return int(value)
    
    def to_string(self, value: int) -> str:
        """
        Convert integer to string.
        
        Args:
            value: Integer value
            
        Returns:
            str: String representation
        """
        return str(value)

class FloatConverter(PathConverter):
    """
    Converter for float path parameters.
    """
    
    regex = "[0-9]+(\\.[0-9]+)?"
    
    def to_python(self, value: str) -> float:
        """
        Convert string to float.
        
        Args:
            value: String representation of float
            
        Returns:
            float: Converted float
            
        Raises:
            ValueError: If value cannot be converted to float
        """
        return float(value)
    
    def to_string(self, value: float) -> str:
        """
        Convert float to string.
        
        Args:
            value: Float value
            
        Returns:
            str: String representation
        """
        return str(value)

class UUIDConverter(PathConverter):
    """
    Converter for UUID path parameters.
    """
    
    regex = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    
    def to_python(self, value: str):
        """
        Convert string to UUID.
        
        Args:
            value: String representation of UUID
            
        Returns:
            UUID: Converted UUID object
            
        Raises:
            ValueError: If value is not a valid UUID
        """
        import uuid
        return uuid.UUID(value)
    
    def to_string(self, value) -> str:
        """
        Convert UUID to string.
        
        Args:
            value: UUID value
            
        Returns:
            str: String representation
        """
        return str(value)

class PathConverterRegistry:
    """
    Registry for path parameter converters.
    
    Manages available converter types and provides conversion utilities.
    """
    
    def __init__(self):
        """
        Initialize converter registry with built-in converters.
        """
        self.converters = {
            "int": IntConverter(),
            "float": FloatConverter(),
            "uuid": UUIDConverter(),
            "str": PathConverter(),  # Default
        }
    
    def register_converter(self, name: str, converter: PathConverter):
        """
        Register a custom converter.
        
        Args:
            name: Converter name
            converter: Converter instance
        """
        self.converters[name] = converter
    
    def get_converter(self, name: str) -> PathConverter:
        """
        Get converter by name.
        
        Args:
            name: Converter name
            
        Returns:
            PathConverter: Converter instance
            
        Note:
            Falls back to string converter if name not found
        """
        return self.converters.get(name, self.converters["str"])
    
    def convert_path(self, path: str) -> str:
        """
        Convert path with converters to regex pattern.
        
        Args:
            path: URL path with converter patterns
            
        Returns:
            str: Regular expression pattern
            
        Example:
            >>> registry.convert_path("/user/<int:id>")
            '/user/(?P<id>[0-9]+)'
        """
        # Example: "/user/<int:id>" -> "/user/(?P<id>[0-9]+)"
        pattern = r"<(?:(?P<converter>\w+):)?(?P<name>\w+)>"
        
        def replacer(match):
            converter_name = match.group("converter") or "str"
            param_name = match.group("name")
            converter = self.get_converter(converter_name)
            return f"(?P<{param_name}>{converter.regex})"
        
        return re.sub(pattern, replacer, path)

# Global converter registry
default_converter_registry = PathConverterRegistry()

def convert_path(path: str) -> str:
    """
    Convert a path with converters to regex pattern.
    
    Args:
        path: URL path with converter patterns
        
    Returns:
        str: Regular expression pattern
        
    Example:
        >>> convert_path("/user/<int:id>/post/<uuid:post_id>")
    """
    if HAS_RUST_ROUTING:
        try:
            return compile_path(path)
        except Exception:
            # Fall back to Python implementation
            pass
    
    # Fallback Python implementation
    return default_converter_registry.convert_path(path)