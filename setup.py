from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop
import os
import subprocess
from pathlib import Path


def run_shell_install():
    """Run shell installer"""
    try:
        # Get package directory
        package_dir = Path(__file__).parent / "src" / "pymin"

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


class PostInstallCommand(install):
    """Post-installation for installation mode"""

    def run(self):
        install.run(self)
        run_shell_install()


class PostDevelopCommand(develop):
    """Post-installation for development mode"""

    def run(self):
        develop.run(self)
        run_shell_install()


setup(
    cmdclass={
        "install": PostInstallCommand,
        "develop": PostDevelopCommand,
    }
)
