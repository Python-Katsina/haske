# from setuptools import setup
# from setuptools_rust import RustExtension

# setup(
#     name="haske",
#     version="0.1.0",
#     rust_extensions=[RustExtension("_haske_core", "Cargo.toml")],
#     packages=["haske"],
#     zip_safe=False,
# )
from setuptools import setup, find_packages
import os

setup(
    name="haske",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "starlette>=0.27.0",
        "uvicorn>=0.20.0",
        "jinja2>=3.0.0",
        "sqlalchemy>=1.4.0",
        "typer>=0.9.0",
        "python-multipart>=0.0.5",
        "httpx>=0.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "black>=22.0.0",
            "mypy>=0.991",
            "ruff>=0.0.260",
        ],
        "rust": [
            "maturin>=0.14,<0.15",
        ],
    },
    python_requires=">=3.8",
)