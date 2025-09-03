# haske-python/setup.py
from setuptools import setup, find_packages
from setuptools_rust import RustExtension

setup(
    name="haske",
    version="0.1.0",
    packages=find_packages(),
    rust_extensions=[
        RustExtension(
            "_haske_core",
            path="../haske-core/Cargo.toml",
            debug=False,
        )
    ],
    install_requires=[
        "starlette>=0.27.0",
        "uvicorn>=0.20.0",
        "jinja2>=3.0.0",
        "sqlalchemy>=1.4.0",
        "typer>=0.9.0",
        "python-multipart>=0.0.5",
        "httpx>=0.24.0",
        "maturin>=0.12.0",
        "itsdangerous>=2.1.0",
    ],
    zip_safe=False,
)