# haske/admin.py
"""
Admin interface generation for Haske applications.

This module provides utilities to automatically generate admin interfaces
for database models, including both visual interfaces and RESTful APIs.
"""

from typing import List, Dict, Any
from starlette.responses import HTMLResponse, JSONResponse
from jinja2 import Template
import inspect

def generate_admin_index(models: List[type]) -> HTMLResponse:
    """
    Generate an HTML admin index page showing all registered models.
    
    Args:
        models: List of SQLAlchemy model classes or similar ORM models
        
    Returns:
        HTMLResponse: Rendered admin interface with model information
        
    Example:
        >>> from myapp.models import User, Post
        >>> app.route("/admin")(generate_admin_index([User, Post]))
    """
    rows = []
    for m in models:
        model_name = m.__name__
        model_fields = []
        
        # Inspect model fields if it's a SQLAlchemy model or similar
        if hasattr(m, '__table__') and hasattr(m.__table__, 'columns'):
            for column in m.__table__.columns:
                model_fields.append({
                    'name': column.name,
                    'type': str(column.type),
                    'nullable': column.nullable,
                })
        elif hasattr(m, '__annotations__'):
            for field_name, field_type in m.__annotations__.items():
                model_fields.append({
                    'name': field_name,
                    'type': str(field_type),
                })
        
        rows.append({
            'name': model_name,
            'fields': model_fields,
            'count': getattr(m, 'query', None).count() if hasattr(m, 'query') else 'N/A'
        })
    
    tpl = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Haske Admin</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; }
            .model { background: #f5f5f5; padding: 20px; margin-bottom: 20px; border-radius: 8px; }
            .model h2 { margin-top: 0; }
            .field { background: white; padding: 8px; margin: 5px 0; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>Haske Admin</h1>
        {% for model in models %}
        <div class="model">
            <h2>{{ model.name }} ({{ model.count }})</h2>
            {% for field in model.fields %}
            <div class="field">
                <strong>{{ field.name }}</strong>: {{ field.type }}
                {% if field.nullable %}<em>nullable</em>{% endif %}
            </div>
            {% endfor %}
        </div>
        {% endfor %}
    </body>
    </html>
    """
    
    t = Template(tpl)
    return HTMLResponse(t.render(models=rows))

def generate_admin_api(models: List[type]) -> 'Haske':
    """
    Generate CRUD API endpoints for admin models.
    
    Args:
        models: List of model classes to generate API endpoints for
        
    Returns:
        Haske: Application instance with generated admin API routes
        
    Example:
        >>> from myapp.models import User, Post
        >>> admin_app = generate_admin_api([User, Post])
        >>> app.mount("/admin/api", admin_app)
    """
    from .app import Haske
    from .request import Request
    
    app = Haske(__name__)
    
    for model in models:
        model_name = model.__name__.lower()
        
        @app.route(f"/admin/api/{model_name}", methods=["GET"])
        async def list_entities(request: Request):
            """List all entities of this model type."""
            # Implementation for listing entities
            pass
            
        @app.route(f"/admin/api/{model_name}/:id", methods=["GET"])
        async def get_entity(request: Request):
            """Get a single entity by ID."""
            # Implementation for getting a single entity
            pass
            
        @app.route(f"/admin/api/{model_name}", methods=["POST"])
        async def create_entity(request: Request):
            """Create a new entity."""
            # Implementation for creating an entity
            pass
            
        @app.route(f"/admin/api/{model_name}/:id", methods=["PUT"])
        async def update_entity(request: Request):
            """Update an existing entity."""
            # Implementation for updating an entity
            pass
            
        @app.route(f"/admin/api/{model_name}/:id", methods=["DELETE"])
        async def delete_entity(request: Request):
            """Delete an entity."""
            # Implementation for deleting an entity
            pass
    
    return app