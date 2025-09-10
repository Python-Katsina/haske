import os
import sys
import platform
import subprocess
import site
from pathlib import Path
from setuptools import setup, find_packages

class WheelInstaller:
    """Handles installation of haske and haske_core wheels with OS/platform checks."""

    # Platform tags to detect
    PLATFORM_TAGS = {
        "windows": "win",
        "linux": "linux",
        "darwin": "macosx",
    }

    @staticmethod
    def get_current_platform_tag():
        system = platform.system().lower()
        return WheelInstaller.PLATFORM_TAGS.get(system, None)

    @staticmethod
    def find_wheels(directory, platform_tag):
        wheel_dir = Path(directory)
        if not wheel_dir.exists():
            return None, None

        haske_wheel, haske_core_wheel = None, None

        for wheel_file in wheel_dir.glob("*.whl"):
            name = wheel_file.name.lower()
            if platform_tag in name or "any.whl" in name:
                if name.startswith("haske-") and not name.startswith("haske_core-"):
                    haske_wheel = wheel_file
                elif name.startswith("haske_core-"):
                    haske_core_wheel = wheel_file

        return haske_wheel, haske_core_wheel

    @staticmethod
    def install_wheel(wheel_path):
        wheel_path = Path(wheel_path)
        if not wheel_path.exists() or not wheel_path.suffix == ".whl":
            print(f"❌ Not a valid wheel file: {wheel_path}")
            return False
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "--force-reinstall", "--no-deps", str(wheel_path.resolve())
            ])
            print(f"✅ Installed wheel: {wheel_path.name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {wheel_path.name}: {e}")
            return False

    @staticmethod
    def configure_paths(current_dir):
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))

        try:
            site_packages = site.getsitepackages()
            if site_packages:
                pth_file = Path(site_packages[0]) / "haske.pth"
                with open(pth_file, "w") as f:
                    f.write(str(current_dir) + "\n")
                print(f"✅ Created .pth file: {pth_file}")
        except Exception as e:
            print(f"⚠ Could not create .pth file: {e}")

    @staticmethod
    def install_requirements():
        """Install requirements.txt if it exists in the current directory."""
        req_file = Path("requirements.txt")
        if req_file.exists():
            print("📋 Installing dependencies from requirements.txt...")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "-r", str(req_file)
                ])
                print("✅ requirements.txt installed successfully")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install requirements: {e}")
                return False
        else:
            print("ℹ️ No requirements.txt found, skipping dependency install")
        return False


def auto_install():
    print("🚀 Installing Haske with platform-aware wheel detection...")
    print("="*60)

    platform_tag = WheelInstaller.get_current_platform_tag()
    if not platform_tag:
        print("⚠ Could not detect platform, defaulting to universal wheels (any.whl)")
        platform_tag = "any.whl"

    print(f"🔎 Looking for wheels matching platform: {platform_tag}")

    wheel_locations = [
        "dist",
        "target/wheels",
        "haske-core/target/wheels",
        "haske-python/target/wheels",
        os.getcwd(),
    ]

    installed = False
    for location in wheel_locations:
        haske_wheel, haske_core_wheel = WheelInstaller.find_wheels(location, platform_tag)
        if haske_wheel and haske_core_wheel:
            print(f"📦 Found wheels in {location}")
            WheelInstaller.install_wheel(haske_core_wheel)
            WheelInstaller.install_wheel(haske_wheel)
            installed = True
            break

    if not installed:
        print("⚠ No matching wheels found. Installing Python sources only...")
        setup(
            name="haske",
            version="0.2.3",
            description="High-performance Python web framework with Rust extensions",
            author="Haske Team",
            packages=find_packages(include=['haske', 'haske.*']),
            install_requires=[],
            zip_safe=False,
            entry_points={
        "console_scripts": [
            "haske=haske.cli:cli",  
        ],
    },
        )

    # Install requirements.txt if available
    WheelInstaller.install_requirements()

    # Configure paths
    WheelInstaller.configure_paths(Path(__file__).parent.absolute())

    # Verify import
    try:
        import haske
        print(f"✅ Import success! Version: {getattr(haske, '__version__', 'unknown')}")
    except Exception as e:
        print(f"❌ Import failed: {e}")

    print("="*60)
    print("🎉 Setup finished!")


if __name__ == "__main__":
    auto_install()
