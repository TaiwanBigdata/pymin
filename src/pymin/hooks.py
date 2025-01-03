# Pip install/uninstall hooks for PyMin
import os
import subprocess
from pathlib import Path


def post_install(install_dir=None):
    """Run shell installer after package is installed"""
    try:
        # Get package directory
        package_dir = Path(__file__).parent

        # Get install script
        install_script = package_dir / "shell" / "install.sh"

        if install_script.exists():
            # Run installer
            subprocess.run(
                ["bash", str(install_script)],
                check=True,
                env={**os.environ, "SHELL": "/bin/bash"},
            )
    except Exception as e:
        print(f"Warning: Failed to install shell integration: {str(e)}")
        print("You can manually install it later by running: pm shell install")


def pre_uninstall(install_dir=None):
    """Run shell uninstaller before package is uninstalled"""
    try:
        # Get package directory
        package_dir = Path(__file__).parent

        # Get uninstall script
        uninstall_script = package_dir / "shell" / "uninstall.sh"

        if uninstall_script.exists():
            # Run uninstaller
            subprocess.run(
                ["bash", str(uninstall_script)],
                check=True,
                env={**os.environ, "SHELL": "/bin/bash"},
            )
    except Exception as e:
        print(f"Warning: Failed to uninstall shell integration: {str(e)}")
        print(
            "You may need to manually remove PyMin configuration from your shell RC file"
        )
