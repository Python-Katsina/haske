import typer
import uvicorn
from typing import Optional
from pathlib import Path
import shutil
from .app import Haske

cli = typer.Typer()

@cli.command()
def dev(
    module: str = typer.Option(..., help="module:app path e.g. examples.blog_app.backend.app:app"), 
    host: str = "127.0.0.1", 
    port: int = 8000, 
    reload: bool = True,
    workers: int = 1
):
    """Start development server"""
    uvicorn.run(module, host=host, port=port, reload=reload, workers=workers)

@cli.command()
def new(name: str, with_frontend: bool = True):
    """Create a new Haske project"""
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
    """Build the application for production"""
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
    """Run tests"""
    import subprocess
    import sys
    
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/"])
    raise typer.Exit(result.returncode)

@cli.command()
def routes():
    """Show all registered routes"""
    # This would need access to the app instance
    typer.echo("Registered routes:")
    # Implementation would list all routes from the app

@cli.command()
def check():
    """Check application for common issues"""
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

if __name__ == "__main__":
    cli()