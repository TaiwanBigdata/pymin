"""Core functionality for virtual environment management"""

import os
import sys
import venv
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from .venv_analyzer import VenvAnalyzer
from ..ui.style import format_env_switch, StyleType
from ..ui.console import print_success, print_warning
from .package_manager import PackageManager
from .package_analyzer import PackageAnalyzer


class VenvManager:
    """Manager for virtual environment operations"""

    def __init__(self):
        """Initialize VenvManager"""
        self.from_env = self._get_current_env()
        self.package_manager = None
        if self.from_env:
            self.package_manager = PackageManager(self.from_env)
        self.analyzer = VenvAnalyzer()
        self.package_analyzer = PackageAnalyzer(self.from_env)

    def get_environment_info(self) -> Dict[str, Any]:
        """Get comprehensive environment information"""
        # Get basic environment info from analyzer
        env_info = self.analyzer.get_venv_info()
        return env_info

    def _get_shell(self) -> Tuple[str, str]:
        """Get shell executable and name"""
        shell = os.environ.get("SHELL", "/bin/sh")
        shell_name = os.path.basename(shell)
        return shell, shell_name

    def _format_env_name(self, env_path: Path) -> str:
        """Format environment name with consistent styling"""
        project_name = env_path.resolve().parent.name
        env_name = env_path.name
        return f"[{StyleType.ENV_PROJECT_NAME}]{project_name}[/{StyleType.ENV_PROJECT_NAME}][{StyleType.ENV_VENV_NAME}]({env_name})[/{StyleType.ENV_VENV_NAME}]"

    def _get_shell_commands(
        self,
        *,
        action: str,
        env_path: Path,
        shell_name: str,
    ) -> Tuple[Dict[str, str], str]:
        """Get shell-specific commands for environment operations"""
        if action == "activate":
            # Get environment name for display
            env_name = env_path.resolve().parent.name

            # Prepare environment variables
            env_vars = {
                "VIRTUAL_ENV": str(env_path.resolve()),
                "PATH": f"{env_path}/bin:{os.environ.get('PATH', '')}",
            }

            # Remove PYTHONHOME if exists
            if "PYTHONHOME" in os.environ:
                env_vars["PYTHONHOME"] = ""

            # Handle PS1 based on shell type
            if shell_name == "zsh":
                ps1_cmd = f'export PROMPT="({env_name}(env)) $PROMPT"'
            else:
                # Assume bash/sh compatible
                ps1_cmd = f'export PS1="({env_name}(env)) $PS1"'

        else:  # deactivate
            # Get original PATH (remove venv path)
            old_path = os.environ.get("PATH", "")
            venv_bin = f"{env_path}/bin:"
            new_path = old_path.replace(venv_bin, "", 1)

            # Prepare environment cleanup
            env_vars = {
                "PATH": new_path,
                "VIRTUAL_ENV": "",  # Clear VIRTUAL_ENV
            }

            # Handle PS1 based on shell type
            if shell_name == "zsh":
                ps1_cmd = (
                    'export PROMPT="${PROMPT#\\(${VIRTUAL_ENV:t:h}\\(env\\)) }"'
                )
            else:
                # Assume bash/sh compatible
                ps1_cmd = 'export PS1="${PS1#\\(${VIRTUAL_ENV##*/}\\(env\\)) }"'

        return env_vars, ps1_cmd

    def _prepare_deactivation(self) -> Tuple[str, str, str]:
        """
        Prepare environment deactivation
        Returns:
            Tuple of (shell, shell_name, shell_command)
        """
        # Check if VIRTUAL_ENV environment variable exists
        if "VIRTUAL_ENV" not in os.environ:
            print_warning("No virtual environment is currently active")
            return None, None, None

        # Proceed with deactivation even if the environment directory has been deleted
        env_path = Path(os.environ["VIRTUAL_ENV"])

        # Show environment change message
        print_success(format_env_switch(env_path, None))

        # Get shell information
        shell, shell_name = self._get_shell()

        # Get shell-specific commands
        env_vars, ps1_cmd = self._get_shell_commands(
            action="deactivate",
            env_path=env_path,
            shell_name=shell_name,
        )

        # Convert env_vars to shell export commands
        exports = " ".join(f"export {k}='{v}';" for k, v in env_vars.items())

        shell_command = (
            f"unset VIRTUAL_ENV PATH; {exports} {ps1_cmd} && exec {shell}"
        )
        return shell, shell_name, shell_command

    def _prepare_activation(
        self, venv_path: Optional[Path] = None
    ) -> Tuple[str, str, str]:
        """
        Prepare environment activation
        Returns:
            Tuple of (shell, shell_name, shell_command)
        """
        # If no path provided, try to find the default venv
        if not venv_path:
            try:
                venv_path = self.analyzer._find_venv_path()
            except Exception as e:
                raise ValueError("No virtual environment found")

        # Get the activation script path based on the platform
        if sys.platform == "win32":
            activate_script = venv_path / "Scripts" / "activate.bat"
        else:
            activate_script = venv_path / "bin" / "activate"

        if not activate_script.exists():
            raise FileNotFoundError(
                f"Activation script not found at {activate_script}"
            )

        # Check if trying to switch to the same environment
        if self.from_env and venv_path and self.from_env.samefile(venv_path):
            print_warning(format_env_switch(self.from_env, venv_path))
            return None, None, None

        # Show environment change message
        print_success(format_env_switch(self.from_env, venv_path))

        # Get shell information
        shell, shell_name = self._get_shell()

        # Get shell-specific commands
        env_vars, ps1_cmd = self._get_shell_commands(
            action="activate",
            env_path=venv_path,
            shell_name=shell_name,
        )

        # Convert env_vars to shell export commands
        exports = " ".join(f"export {k}='{v}';" for k, v in env_vars.items())

        shell_command = (
            f"unset VIRTUAL_ENV PATH; {exports} {ps1_cmd} && exec {shell}"
        )
        return shell, shell_name, shell_command

    def activate_environment(self, venv_path: Optional[Path] = None) -> None:
        """
        Activate the virtual environment

        Args:
            venv_path: Optional path to the virtual environment. If not provided,
                      will try to find and use the default 'env' directory.
        """
        try:
            shell, shell_name, shell_command = self._prepare_activation(
                venv_path
            )
            if shell_command:
                os.execl(shell, shell_name, "-c", shell_command)
        except Exception as e:
            raise RuntimeError(
                f"Failed to activate virtual environment: {str(e)}"
            ) from e

    def deactivate_environment(self) -> None:
        """
        Deactivate the current virtual environment
        """
        try:
            shell, shell_name, shell_command = self._prepare_deactivation()
            if shell_command:
                os.execl(shell, shell_name, "-c", shell_command)
        except Exception as e:
            raise RuntimeError(
                f"Failed to deactivate virtual environment: {str(e)}"
            ) from e

    def find_default_venv(self) -> Optional[Path]:
        """Find the default virtual environment in the current directory"""
        try:
            return self.analyzer._find_venv_path()
        except Exception:
            return None

    def has_venv(self, venv_path: Path) -> bool:
        """Check if a valid virtual environment exists at the given path"""
        return self.analyzer.is_valid_venv(venv_path)

    def create_environment(
        self, venv_path: Path, rebuild: bool = False
    ) -> Dict[str, Any]:
        """Create a new virtual environment

        Args:
            venv_path: Path where to create the environment
            rebuild: Whether to rebuild if environment exists

        Returns:
            Dictionary containing environment information
        """
        # Handle rebuilding
        if venv_path.exists():
            if rebuild:
                import shutil

                shutil.rmtree(venv_path)
            else:
                raise ValueError(f"Environment already exists at {venv_path}")

        # Create the environment
        venv.create(venv_path, with_pip=True)

        # Set the venv path for analyzer
        self.analyzer.venv_path = venv_path

        # Verify the environment was created successfully
        if not self.has_venv(venv_path):
            raise RuntimeError("Failed to create virtual environment")

        # Get environment information
        env_info = self.analyzer.get_venv_info()
        return env_info

    def install_requirements(self, venv_path: Path) -> None:
        """Install requirements from requirements.txt

        Args:
            venv_path: Path to the virtual environment
        """
        requirements_file = Path("requirements.txt")
        if not requirements_file.exists():
            return

        # Get pip path
        if sys.platform == "win32":
            pip_path = venv_path / "Scripts" / "pip"
        else:
            pip_path = venv_path / "bin" / "pip"

        if not pip_path.exists():
            raise FileNotFoundError(f"Pip not found at {pip_path}")

        # Install requirements
        result = subprocess.run(
            [str(pip_path), "install", "-r", str(requirements_file)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to install requirements: {result.stderr}"
            )

    def add_packages(
        self,
        packages: List[str],
        *,
        dev: bool = False,
        editable: bool = False,
        no_deps: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """Add packages to the virtual environment"""
        if not self.package_manager:
            raise ValueError("No active virtual environment")
        results = self.package_manager.add_packages(
            packages,
            dev=dev,
            editable=editable,
            no_deps=no_deps,
        )
        # Clear package analyzer cache after adding packages
        self.package_analyzer.clear_cache()
        return results

    def remove_packages(
        self,
        packages: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Remove packages from the virtual environment"""
        if not self.package_manager:
            raise ValueError("No active virtual environment")
        results = self.package_manager.remove_packages(packages)
        # Clear package analyzer cache after removing packages
        self.package_analyzer.clear_cache()
        return results

    def _get_current_env(self):
        """Get the current virtual environment"""
        if "VIRTUAL_ENV" in os.environ:
            env_path = Path(os.environ["VIRTUAL_ENV"])
            if env_path.exists() and (env_path / "bin" / "activate").exists():
                return env_path
        return None
