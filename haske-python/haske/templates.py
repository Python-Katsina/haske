# haske/templates.py
"""
Template rendering utilities for Haske framework.

This module provides Jinja2 template rendering with Rust acceleration
for improved performance and additional template utilities.
"""

from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Import Rust template functions if available
try:
    from _haske_core import render_template as rust_render_template, precompile_template
    HAS_RUST_TEMPLATES = True
except ImportError:
    HAS_RUST_TEMPLATES = False

_env = None  # global Jinja2 environment

def get_env(directory: str = "templates") -> Environment:
    """
    Get or create Jinja2 environment.
    
    Args:
        directory: Templates directory, defaults to "templates"
        
    Returns:
        Environment: Jinja2 environment instance
    """
    global _env
    if _env is None:
        _env = Environment(
            loader=FileSystemLoader(directory),
            autoescape=select_autoescape(["html", "xml"]),
            enable_async=True
        )
    return _env

class TemplateEngine:
    """
    Template engine with Rust acceleration and precompilation.
    
    Provides template rendering with performance optimizations
    through Rust acceleration and template precompilation.
    
    Attributes:
        env: Jinja2 environment
        _precompiled_templates: Cache of precompiled templates
    """
    
    def __init__(self, directory: str = "templates"):
        """
        Initialize template engine.
        
        Args:
            directory: Templates directory, defaults to "templates"
        """
        self.env = get_env(directory)
        self._precompiled_templates = {}

    def get_template(self, name: str):
        """
        Get template by name.
        
        Args:
            name: Template name
            
        Returns:
            Template: Jinja2 template instance
        """
        return self.env.get_template(name)

    async def TemplateResponse(self, template_name: str, context: dict):
        """
        Create a template response.
        
        Args:
            template_name: Template name
            context: Template context
            
        Returns:
            HTMLResponse: Rendered template response
        """
        from .response import HTMLResponse
        template = self.get_template(template_name)
        content = await template.render_async(**context)
        return HTMLResponse(content)

    def precompile(self, template_name: str) -> str:
        """
        Precompile template for faster rendering.
        
        Args:
            template_name: Template name
            
        Returns:
            str: Precompiled template source
            
        Note:
            Stores precompiled version for future use
        """
        template = self.get_template(template_name)
        source = template.source
        
        if HAS_RUST_TEMPLATES:
            precompiled = precompile_template(source)
        else:
            # Fallback - just return the source
            precompiled = source
        
        # Store precompiled version
        self._precompiled_templates[template_name] = precompiled
        return precompiled

    async def render_precompiled(self, template_name: str, context: dict) -> str:
        """
        Render precompiled template.
        
        Args:
            template_name: Template name
            context: Template context
            
        Returns:
            str: Rendered template content
            
        Note:
            Falls back to Jinja2 if Rust rendering fails
        """
        if template_name not in self._precompiled_templates:
            self.precompile(template_name)
        
        precompiled = self._precompiled_templates[template_name]
        
        # Try Rust rendering first
        if HAS_RUST_TEMPLATES:
            try:
                result = rust_render_template(precompiled, context)
                if result:
                    return result
            except Exception:
                # Fall back to Jinja2
                pass
        
        # Fall back to standard rendering
        template = self.get_template(template_name)
        return await template.render_async(**context)

# --- Flask-style helper ---
def render_template(template_name: str, **context) -> str:
    """
    Direct helper to render template and return HTML string.
    
    Args:
        template_name: Template name
        **context: Template context variables
        
    Returns:
        str: Rendered HTML content
        
    Example:
        >>> html = render_template("index.html", title="Home", user=user)
    """
    env = get_env()
    template = env.get_template(template_name)
    return template.render(**context)

async def render_template_async(template_name: str, **context) -> str:
    """
    Async version of render_template.
    
    Args:
        template_name: Template name
        **context: Template context variables
        
    Returns:
        str: Rendered HTML content
        
    Example:
        >>> html = await render_template_async("index.html", title="Home")
    """
    env = get_env()
    template = env.get_template(template_name)
    return await template.render_async(**context)

def template_response(template_name: str, **context):
    """
    Create a TemplateResponse directly.
    
    Args:
        template_name: Template name
        **context: Template context variables
        
    Returns:
        HTMLResponse: Template response object
        
    Example:
        >>> return template_response("index.html", title="Home")
    """
    from .response import HTMLResponse
    content = render_template(template_name, **context)
    return HTMLResponse(content)