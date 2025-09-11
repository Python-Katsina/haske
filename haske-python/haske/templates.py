# haske/templates.py
"""
Template rendering utilities for Haske framework.

This module provides Jinja2 template rendering with optional Rust
acceleration for improved performance, as well as utilities for
managing template and static directories.
"""

import os
import inspect
from typing import Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Try loading Rust-powered template functions
try:
    from _haske_core import render_template as rust_render_template, precompile_template
    HAS_RUST_TEMPLATES = True
except ImportError:
    HAS_RUST_TEMPLATES = False


# Globals
_env: Optional[Environment] = None
_template_dir: str = "templates"
_static_dir: str = "static"


# ---------------------------
# CONFIGURATION
# ---------------------------
def configure_templates(template_dir: str = "templates", static_dir: str = "static"):
    """Configure global template + static directories."""
    global _template_dir, _static_dir, _env
    _template_dir = template_dir or "templates"
    _static_dir = static_dir or "static"
    _env = None  # reset env, will re-init on next get_env()


def get_env(template_dir: Optional[str] = None, static_dir: Optional[str] = None) -> Environment:
    """Get or create Jinja2 environment."""
    global _env, _template_dir, _static_dir

    if template_dir:
        _template_dir = template_dir
    if static_dir:
        _static_dir = static_dir

    if _env is None:
        abs_template = os.path.abspath(_template_dir)
        abs_static = os.path.abspath(_static_dir)

        # Ensure directories exist
        if not os.path.isdir(abs_template):
            print(f"[Haske] Templates directory not found: {abs_template}, creating it.")
            os.makedirs(abs_template, exist_ok=True)

        if not os.path.isdir(abs_static):
            print(f"[Haske] Static directory not found: {abs_static}, creating it.")
            os.makedirs(abs_static, exist_ok=True)

        # Init Jinja2 env
        _env = Environment(
            loader=FileSystemLoader(abs_template),
            autoescape=select_autoescape(["html", "xml"]),
            enable_async=True,
        )

        # Inject static_url helper
        _env.globals["static_url"] = lambda filename: f"/static/{filename}"

        print(f"[Haske] Using templates from: {abs_template}")
        print(f"[Haske] Static files served from: {abs_static}")

    return _env


# ---------------------------
# HELPER: AUTO-INJECT REQUEST
# ---------------------------
def _inject_request(context: dict) -> dict:
    """Ensure `request` is available in context without explicit passing."""
    if "request" not in context:
        frame = inspect.currentframe()
        while frame:
            local_req = frame.f_locals.get("request")
            if local_req is not None:
                context["request"] = local_req
                break
            frame = frame.f_back
    return context


# ---------------------------
# TEMPLATE ENGINE CLASS
# ---------------------------
class TemplateEngine:
    """Template engine with Rust acceleration and precompilation."""

    def __init__(self, directory: str = None, static_dir: str = None):
        self.env = get_env(directory or _template_dir, static_dir or _static_dir)
        self._precompiled_templates = {}

    def get_template(self, name: str):
        """Return Jinja2 template object by name."""
        return self.env.get_template(name)

    async def TemplateResponse(self, template_name: str, context: dict):
        """Render template into an HTMLResponse."""
        from .response import HTMLResponse
        context = _inject_request(context)
        template = self.get_template(template_name)
        content = await template.render_async(**context)
        return HTMLResponse(content)

    def precompile(self, template_name: str) -> str:
        """Precompile template source (optionally Rust-accelerated)."""
        template = self.get_template(template_name)
        source = template.source

        if HAS_RUST_TEMPLATES:
            precompiled = precompile_template(source)
        else:
            precompiled = source

        self._precompiled_templates[template_name] = precompiled
        return precompiled

    async def render_precompiled(self, template_name: str, context: dict) -> str:
        """Render precompiled template with fallback to Jinja2."""
        context = _inject_request(context)
        if template_name not in self._precompiled_templates:
            self.precompile(template_name)

        precompiled = self._precompiled_templates[template_name]

        if HAS_RUST_TEMPLATES:
            try:
                result = rust_render_template(precompiled, context)
                if result:
                    return result
            except Exception:
                pass  # Fallback below

        template = self.get_template(template_name)
        return await template.render_async(**context)


# ---------------------------
# FLASK-STYLE HELPERS
# ---------------------------
def render_template(template_name: str, **context) -> str:
    """Synchronous template render, returns HTML string."""
    env = get_env(_template_dir, _static_dir)
    context = _inject_request(context)
    template = env.get_template(template_name)
    return template.render(**context)


async def render_template_async(template_name: str, **context) -> str:
    """Asynchronous template render, returns HTML string."""
    env = get_env(_template_dir, _static_dir)
    context = _inject_request(context)
    template = env.get_template(template_name)
    return await template.render_async(**context)


def template_response(template_name: str, **context):
    """Render template directly into an HTMLResponse."""
    from .response import HTMLResponse
    context = _inject_request(context)
    content = render_template(template_name, **context)
    return HTMLResponse(content)
