# haske/cli.py
"""
Command-line interface for Haske framework.

This module provides a comprehensive CLI for development, testing, and
deployment of Haske applications.
"""

import typer
import uvicorn
from pathlib import Path
import shutil
import subprocess
import sys

cli = typer.Typer()


@cli.command()
def dev(
    module: str = typer.Option(
        ..., help="module:app path e.g. examples.blog_app.backend.app:app"
    ),
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = True,
    workers: int = 1,
):
    """
    Start development server.
    """
    uvicorn.run(module, host=host, port=port, reload=reload, workers=workers)


@cli.command()
def new(name: str):
    """
    Create a new Haske project.
    """

    use_template = typer.confirm("Do you want to use HTML templates?", default=True)
    project_path = Path(name)
    if project_path.exists():
        typer.echo(f"Error: Directory '{name}' already exists")
        raise typer.Exit(1)

    # create project folder
    project_path.mkdir()

    # sample index.html
    sample_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Hello from Haske</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f9fafb;
            display: flex;
            height: 100vh;
            margin: 0;
            align-items: center;
            justify-content: center;
            color: #111827;
        }
        h1 {
            font-size: 2.5rem;
            background: linear-gradient(90deg, #6366f1, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
    </style>
</head>
<body>
    <h1>Hello from Haske 🚀</h1>
</body>
</html>
"""

    # create static and template folders if requested
    if use_template:
        (project_path / "static").mkdir()
        (project_path / "templates").mkdir()
        (project_path / "templates" / "index.html").write_text(
            sample_html, encoding="utf-8"
        )

    # always create app.py
    if not use_template:
        app_content = """from haske import Haske, Request, Response

app = Haske(__name__)

@app.route("/")
async def homepage(request: Request):
    return {"message": "Hello, Haske!"}

if __name__ == "__main__":
    app.run()
"""
    else:
        app_content = """from haske import Haske, Request, Response
from haske.templates import render_template_async

app = Haske(__name__)

@app.route("/")
async def apiHome(request: Request):
    return {"message": "Hello, Haske!"}

@app.route("/index")
async def homePage(request: Request):
    return await render_template_async("index.html")

if __name__ == "__main__":
    app.run()
"""

    orm_content = """from haske.orm import Base, Column, Integer, String

class User(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)

# Create
new_user = User(name="Alice")
db.add(new_user)
db.commit()

# Query
user = db.filter(User, name="Alice")
"""

    (project_path / "app.py").write_text(app_content, encoding="utf-8")
    (project_path / "models.py").write_text(orm_content, encoding="utf-8")

    # requirements.txt
    requirements = """haske>=0.2.13
uvicorn[standard]
"""
    (project_path / "requirements.txt").write_text(requirements, encoding="utf-8")

    # .env
    env_content = """HASKE_DEBUG=True
DATABASE_URL=sqlite+aiosqlite:///./app.db
"""
    (project_path / ".env").write_text(env_content, encoding="utf-8")

    typer.echo(f"✅ Created new Haske project: {name}")


@cli.command()
def build():
    """
    Build the application for production.
    """
    typer.echo("Building Haske application...")

    try:
        from _haske_core import HaskeApp

        typer.echo("✓ Rust extensions available")
    except ImportError:
        typer.echo("⚠ Rust extensions not available - using Python fallback")

    typer.echo("✓ Build complete")


@cli.command()
def test():
    """
    Run tests with pytest.
    """
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/"])
    raise typer.Exit(result.returncode)


@cli.command()
def routes():
    """
    Show all registered routes.
    """
    typer.echo("Registered routes:")
    # TODO: list routes when app context available


@cli.command()
def check():
    """
    Check application for common issues.
    """
    typer.echo("Checking application...")

    if Path("templates").exists():
        typer.echo("✓ Templates directory exists")
    else:
        typer.echo("⚠ Templates directory missing")

    if Path("static").exists():
        typer.echo("✓ Static directory exists")
    else:
        typer.echo("⚠ Static directory missing")

    typer.echo("✓ Check complete")


@cli.command()
def setup_frontend():
    """
    Interactive frontend setup.
    """
    typer.echo("\n🎨 Frontend Setup")

    framework = typer.prompt(
        "Which frontend framework do you want to use? (next, vite, angular)", type=str
    ).strip().lower()

    framework_commands = {
        "next": ["create-next-app@latest"],
        "vite": ["create", "vite@latest"],
        "angular": ["@angular/cli", "new"],
    }

    if framework not in framework_commands:
        typer.echo(f"❌ Unsupported framework: {framework}")
        raise typer.Exit(1)

    project_name = typer.prompt("Enter the frontend project name").strip()
    project_path = Path.cwd() / project_name

    if project_path.exists():
        typer.echo(f"⚠️ Project directory {project_path} already exists!")
        overwrite = typer.confirm("Do you want to overwrite it?", default=False)
        if not overwrite:
            raise typer.Exit(1)

    npx_cmd = shutil.which("npx")
    npm_cmd = shutil.which("npm")

    if sys.platform.startswith("win"):
        npx_cmd = shutil.which("npx.cmd") or npx_cmd
        npm_cmd = shutil.which("npm.cmd") or npm_cmd

    if not npx_cmd or not npm_cmd:
        typer.echo("❌ Node.js not found! Please install Node.js from https://nodejs.org/")
        raise typer.Exit(1)

    typer.echo(f"\n🔍 Using npx: {npx_cmd}")
    typer.echo(f"🔍 Using npm: {npm_cmd}")

    typer.echo(f"\n🚀 Creating {framework} project in {project_path} ...")
    typer.echo("👉 You will now interact directly with the framework’s CLI.\n")

    cmd = [npx_cmd] + framework_commands[framework] + [project_name]

    try:
        subprocess.run(cmd, cwd=Path.cwd(), check=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Error creating {framework} project (exit {e.returncode})")
        raise typer.Exit(1)

    typer.echo("\n📦 Installing dependencies ...")
    try:
        subprocess.run([npm_cmd, "install"], cwd=project_path, check=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to install dependencies (exit {e.returncode})")
        raise typer.Exit(1)

    typer.echo(f"\n✅ Frontend setup complete at {project_path}")
    if framework in ("next", "vite"):
        typer.echo(f"   cd {project_name} && {npm_cmd} run dev")
    elif framework == "angular":
        typer.echo(f"   cd {project_name} && ng serve")


@cli.command()
def build_frontend(
    framework: str = typer.Option("react", help="Frontend framework"),
    output_dir: str = typer.Option(None, help="Output directory"),
):
    """
    Build frontend for production (if build commands are available).
    """
    build_commands = {
        "react": "npm run build",
        "vue": "npm run build",
        "nextjs": "npm run build",
        "angular": "ng build --prod",
        "svelte": "npm run build",
    }

    if framework not in build_commands:
        typer.echo(f"Unknown framework: {framework}")
        raise typer.Exit(1)

    command = build_commands[framework]
    if output_dir:
        command += f" --output-path {output_dir}"

    typer.echo(f"Building {framework} frontend...")
    typer.echo(f"Command: {command}")
    typer.echo("✓ Frontend build completed (simulated)")


if __name__ == "__main__":
    cli()
