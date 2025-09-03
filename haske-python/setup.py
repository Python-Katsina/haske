# haske-python/setup.py
import os
import sys
import subprocess
import platform
from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop

def check_rust_installed():
    """Check if Rust is installed on the system"""
    try:
        result = subprocess.run(["rustc", "--version"], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False

def install_rust():
    """Install Rust using rustup"""
    system = platform.system().lower()
    
    print("Installing Rust...")
    
    if system == "windows":
        # Windows installation
        try:
            subprocess.run([
                "powershell", "-Command", 
                "Invoke-WebRequest -Uri https://win.rustup.rs -OutFile rustup-init.exe; "
                ".\\rustup-init.exe -y --default-toolchain stable --profile minimal"
            ], check=True, timeout=300)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            print("Failed to install Rust on Windows automatically.")
            print("Please install Rust manually from: https://rustup.rs/")
            sys.exit(1)
            
    elif system in ["linux", "darwin"]:
        # Linux/macOS installation
        try:
            subprocess.run([
                "curl", "--proto", "=https", "--tlsv1.2", "-sSf", 
                "https://sh.rustup.rs", "|", "sh", "-s", "--", 
                "-y", "--default-toolchain", "stable", "--profile", "minimal"
            ], shell=True, check=True, timeout=300)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            print("Failed to install Rust automatically.")
            print("Please install Rust manually using: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh")
            sys.exit(1)
    else:
        print(f"Unsupported operating system: {system}")
        print("Please install Rust manually from: https://rustup.rs/")
        sys.exit(1)
    
    # Add cargo to PATH for current process
    home_dir = os.path.expanduser("~")
    if system == "windows":
        cargo_bin = os.path.join(home_dir, ".cargo", "bin")
    else:
        cargo_bin = os.path.join(home_dir, ".cargo", "bin")
    
    os.environ["PATH"] = cargo_bin + os.pathsep + os.environ.get("PATH", "")
    
    # Verify installation
    if not check_rust_installed():
        print("Rust installation failed. Please install manually from: https://rustup.rs/")
        sys.exit(1)
    
    print("Rust installed successfully!")

def install_requirements():
    """Install requirements from requirements.txt if it exists"""
    requirements_file = "requirements.txt"
    
    if os.path.exists(requirements_file):
        print(f"Installing requirements from {requirements_file}...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", requirements_file
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to install requirements: {e}")
            sys.exit(1)
    else:
        print(f"{requirements_file} not found. Using default dependencies.")

class CustomInstall(install):
    """Custom install command that handles Rust and requirements"""
    def run(self):
        # Check if Rust is installed
        if not check_rust_installed():
            install_rust()
        
        # Install requirements
        install_requirements()
        
        # Proceed with normal installation
        super().run()

class CustomDevelop(develop):
    """Custom develop command that handles Rust and requirements"""
    def run(self):
        # Check if Rust is installed
        if not check_rust_installed():
            install_rust()
        
        # Install requirements
        install_requirements()
        
        # Proceed with normal development installation
        super().run()

# Check if we can import setuptools_rust (will fail if Rust is not available)
try:
    from setuptools_rust import RustExtension, Binding
    
    rust_extensions = [
        RustExtension(
            "_haske_core",
            path="../haske-core/Cargo.toml",
            debug=False,
            binding=Binding.PyO3,
            strip=True,
        )
    ]
    
except ImportError:
    print("setuptools-rust not available. Rust extensions will be skipped.")
    rust_extensions = []

setup(
    name="haske",
    version="0.1.0",
    packages=find_packages(),
    rust_extensions=rust_extensions,
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
        "setuptools-rust>=1.8,<2.0",  # Ensure this is available
    ],
    cmdclass={
        'install': CustomInstall,
        'develop': CustomDevelop,
    },
    zip_safe=False,
    python_requires=">=3.8",
    author="Haske Team",
    author_email="haske@example.com",
    description="High-performance Python web framework with Rust extensions",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/Python-Katsina/haske",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Rust",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    entry_points={
        "console_scripts": [
            "haske=haske.cli:cli",
        ],
    },
    include_package_data=True,
)