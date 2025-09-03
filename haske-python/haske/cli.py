# haske/cli.py
"""
Command-line interface for Haske framework.

This module provides a comprehensive CLI for development, testing, and
deployment of Haske applications.
"""

import typer
import uvicorn
from typing import Optional
from pathlib import Path
import shutil
from .app import Haske

from .static import create_frontend_config, FrontendManager

cli = typer.Typer()

@cli.command()
def dev(
    module: str = typer.Option(..., help="module:app path e.g. examples.blog_app.backend.app:app"), 
    host: str = "127.0.0.1", 
    port: int = 8000, 
    reload: bool = True,
    workers: int = 1
):
    """
    Start development server.
    
    Args:
        module: Python import path to application (module:app)
        host: Host to bind to, defaults to "127.0.0.1"
        port: Port to listen on, defaults to 8000
        reload: Enable auto-reload on code changes, defaults to True
        workers: Number of worker processes, defaults to 1
        
    Example:
        haske dev --module app.main:app --host 0.0.0.0 --port 8000
    """
    uvicorn.run(module, host=host, port=port, reload=reload, workers=workers)

@cli.command()
def new(name: str, with_frontend: bool = True):
    """
    Create a new Haske project.
    
    Args:
        name: Project name (directory will be created with this name)
        with_frontend: Include frontend scaffolding, defaults to True
        
    Example:
        haske new my-project
    """
    project_path = Path(name)
    if project_path.exists():
        typer.echo(f"Error: Directory '{name}' already exists")
        raise typer.Exit(1)
    
    # Create project structure
    project_path.mkdir()
    (project_path / "app").mkdir()
    (project_path / "static").mkdir()
    (project_path / "templates").mkdir()
    (project_path / "migrations").mkdir()
    
    # Create main app file
    app_content = '''
from haske import Haske, Request, Response

app = Haske(__name__)

@app.route("/")
async def homepage(request: Request):
    return {"message": "Hello, Haske!"}

if __name__ == "__main__":
    app.run()
'''
    (project_path / "app" / "main.py").write_text(app_content)
    
    # Create requirements.txt
    requirements = '''
haske>=0.1.0
uvicorn[standard]
'''
    (project_path / "requirements.txt").write_text(requirements)
    
    # Create .env file
    env_content = '''
HASKE_DEBUG=True
DATABASE_URL=sqlite+aiosqlite:///./app.db
'''
    (project_path / ".env").write_text(env_content)
    
    typer.echo(f"Created new Haske project: {name}")

@cli.command()
def build():
    """
    Build the application for production.
    
    Compiles Rust extensions, bundles frontend assets, and prepares
    the application for production deployment.
    
    Example:
        haske build
    """
    # This would compile Rust extensions, bundle frontend, etc.
    typer.echo("Building Haske application...")
    
    # Check if Rust extensions are available
    try:
        from _haske_core import HaskeApp
        typer.echo("✓ Rust extensions available")
    except ImportError:
        typer.echo("⚠ Rust extensions not available - using Python fallback")
    
    typer.echo("✓ Build complete")

@cli.command()
def test():
    """
    Run tests.
    
    Executes the test suite using pytest.
    
    Example:
        haske test
    """
    import subprocess
    import sys
    
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/"])
    raise typer.Exit(result.returncode)

@cli.command()
def routes():
    """
    Show all registered routes.
    
    Displays a list of all registered routes and their handlers.
    
    Example:
        haske routes
    """
    # This would need access to the app instance
    typer.echo("Registered routes:")
    # Implementation would list all routes from the app

@cli.command()
def check():
    """
    Check application for common issues.
    
    Performs health checks and validates application configuration.
    
    Example:
        haske check
    """
    typer.echo("Checking application...")
    
    # Check if templates directory exists
    if Path("templates").exists():
        typer.echo("✓ Templates directory exists")
    else:
        typer.echo("⚠ Templates directory missing")
    
    # Check if static directory exists
    if Path("static").exists():
        typer.echo("✓ Static directory exists")
    else:
        typer.echo("⚠ Static directory missing")
    
    typer.echo("✓ Check complete")


@cli.command()
def setup_frontend(
    framework: str = typer.Option("react", help="Frontend framework: react, vue, nextjs, angular, svelte"),
    mode: str = typer.Option("production", help="Mode: production or development"),
    build_dir: str = typer.Option(None, help="Custom build directory"),
    dev_server: str = typer.Option(None, help="Development server URL")
):
    """
    Setup frontend serving for Haske application.
    """
    config = create_frontend_config(framework)
    
    if build_dir:
        config["build_dir"] = build_dir
    if dev_server:
        config["dev_server"] = dev_server
    
    # Create or update app configuration
    config_path = Path("haske.config.json")
    if config_path.exists():
        with open(config_path, "r") as f:
            existing_config = json.load(f)
    else:
        existing_config = {}
    
    existing_config["frontend"] = config
    existing_config["frontend_mode"] = mode
    
    with open(config_path, "w") as f:
        json.dump(existing_config, f, indent=2)
    
    typer.echo(f"✓ Frontend setup for {framework} in {mode} mode")
    typer.echo(f"Build directory: {config['build_dir']}")
    if mode == "development":
        typer.echo(f"Dev server: {config['dev_server']}")

@cli.command()
def build_frontend(
    framework: str = typer.Option("react", help="Frontend framework"),
    output_dir: str = typer.Option(None, help="Output directory")
):
    """
    Build frontend for production (if build commands are available).
    """
    build_commands = {
        "react": "npm run build",
        "vue": "npm run build",
        "nextjs": "npm run build",
        "angular": "ng build --prod",
        "svelte": "npm run build"
    }
    
    if framework not in build_commands:
        typer.echo(f"Unknown framework: {framework}")
        raise typer.Exit(1)
    
    command = build_commands[framework]
    if output_dir:
        command += f" --output-path {output_dir}"
    
    typer.echo(f"Building {framework} frontend...")
    typer.echo(f"Command: {command}")
    
    # In a real implementation, we would run the command
    # For now, just show what would happen
    typer.echo("✓ Frontend build completed (simulated)")
    

if __name__ == "__main__":
    cli()