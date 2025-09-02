# haske/templates.py
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from _haske_core import render_template as rust_render_template, precompile_template

_env = None  # global Jinja2 environment

def get_env(directory: str = "templates") -> Environment:
    global _env
    if _env is None:
        _env = Environment(
            loader=FileSystemLoader(directory),
            autoescape=select_autoescape(["html", "xml"]),
            enable_async=True
        )
    return _env

class TemplateEngine:
    def __init__(self, directory: str = "templates"):
        self.env = get_env(directory)
        self._precompiled_templates = {}

    def get_template(self, name: str):
        return self.env.get_template(name)

    async def TemplateResponse(self, template_name: str, context: dict):
        from .response import HTMLResponse
        template = self.get_template(template_name)
        content = await template.render_async(**context)
        return HTMLResponse(content)

    def precompile(self, template_name: str) -> str:
        """Precompile template for faster rendering"""
        template = self.get_template(template_name)
        source = template.source
        precompiled = precompile_template(source)
        
        # Store precompiled version
        self._precompiled_templates[template_name] = precompiled
        return precompiled

    async def render_precompiled(self, template_name: str, context: dict) -> str:
        """Render precompiled template"""
        if template_name not in self._precompiled_templates:
            self.precompile(template_name)
        
        precompiled = self._precompiled_templates[template_name]
        
        # Try Rust rendering first
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
    Direct helper to render template and return HTML string
    """
    env = get_env()
    template = env.get_template(template_name)
    return template.render(**context)

async def render_template_async(template_name: str, **context) -> str:
    """
    Async version of render_template
    """
    env = get_env()
    template = env.get_template(template_name)
    return await template.render_async(**context)

def template_response(template_name: str, **context):
    """
    Create a TemplateResponse directly
    """
    from .response import HTMLResponse
    content = render_template(template_name, **context)
    return HTMLResponse(content)