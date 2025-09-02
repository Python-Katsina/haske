from setuptools import setup
from setuptools_rust import RustExtension

setup(
    name="haske",
    version="0.1.0",
    rust_extensions=[RustExtension("_haske_core", "Cargo.toml")],
    packages=["haske"],
    zip_safe=False,
)