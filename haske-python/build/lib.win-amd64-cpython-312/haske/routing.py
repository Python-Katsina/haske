# Route decorator, converters, path params
from typing import Callable, List, Any, Dict
from starlette.routing import Route as StarletteRoute
import re

class Route(StarletteRoute):
    """Haske Route class extending Starlette's Route."""
    
    def __init__(self, path: str, endpoint: Callable, methods: List[str] = None, 
                 name: str = None, **kwargs):
        super().__init__(path, endpoint, methods=methods or ["GET"], name=name, **kwargs)

class PathConverter:
    """Base class for path parameter converters"""
    
    regex = "[^/]+"
    
    def to_python(self, value: str) -> Any:
        return value
    
    def to_string(self, value: Any) -> str:
        return str(value)

class IntConverter(PathConverter):
    """Converter for integer path parameters"""
    
    regex = "[0-9]+"
    
    def to_python(self, value: str) -> int:
        return int(value)
    
    def to_string(self, value: int) -> str:
        return str(value)

class FloatConverter(PathConverter):
    """Converter for float path parameters"""
    
    regex = "[0-9]+(\\.[0-9]+)?"
    
    def to_python(self, value: str) -> float:
        return float(value)
    
    def to_string(self, value: float) -> str:
        return str(value)

class UUIDConverter(PathConverter):
    """Converter for UUID path parameters"""
    
    regex = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    
    def to_python(self, value: str):
        import uuid
        return uuid.UUID(value)
    
    def to_string(self, value) -> str:
        return str(value)

class PathConverterRegistry:
    """Registry for path parameter converters"""
    
    def __init__(self):
        self.converters = {
            "int": IntConverter(),
            "float": FloatConverter(),
            "uuid": UUIDConverter(),
            "str": PathConverter(),  # Default
        }
    
    def register_converter(self, name: str, converter: PathConverter):
        """Register a custom converter"""
        self.converters[name] = converter
    
    def get_converter(self, name: str) -> PathConverter:
        """Get converter by name"""
        return self.converters.get(name, self.converters["str"])
    
    def convert_path(self, path: str) -> str:
        """Convert path with converters to regex pattern"""
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
    """Convert a path with converters to regex pattern"""
    return default_converter_registry.convert_path(path)