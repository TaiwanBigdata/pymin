"""Core functionality for virtual environment management"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from .venv_analyzer import VenvAnalyzer
from ..ui.style import format_env_switch, StyleType
from ..ui.console import print_success, print_warning


class VenvManager:
    """Manager for virtual environment operations"""

    def __init__(self, project_path: Optional[str] = None):
        """Initialize VenvManager with project path"""
        self.analyzer = VenvAnalyzer(project_path)
        self.from_env = (
            Path(os.environ["VIRTUAL_ENV"])
            if "VIRTUAL_ENV" in os.environ
            else None
        )

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

    def activate_environment(self, venv_path: Optional[Path] = None) -> None:
        """
        Activate the virtual environment

        Args:
            venv_path: Optional path to the virtual environment. If not provided,
                      will try to find and use the default 'env' directory.
        """
        try:
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
            if (
                self.from_env
                and venv_path
                and self.from_env.samefile(venv_path)
            ):
                print_warning(
                    f"Environment is already active: {self._format_env_name(self.from_env)}"
                )
                return

            # Show environment switch message
            print_success(
                f"Switching environment: {format_env_switch(self.from_env, venv_path)}"
            )

            # Get shell information
            shell, shell_name = self._get_shell()

            # Get shell-specific commands
            env_vars, ps1_cmd = self._get_shell_commands(
                action="activate",
                env_path=venv_path,
                shell_name=shell_name,
            )

            # Convert env_vars to shell export commands
            exports = " ".join(
                f"export {k}='{v}';" for k, v in env_vars.items()
            )

            # Execute shell with environment variables
            os.execl(
                shell,
                shell_name,
                "-c",
                f"unset VIRTUAL_ENV PATH; {exports} {ps1_cmd} && exec {shell}",
            )

        except Exception as e:
            raise RuntimeError(
                f"Failed to activate virtual environment: {str(e)}"
            )

    def deactivate_environment(self) -> None:
        """
        Deactivate the current virtual environment
        """
        try:
            # Check if we're in a virtual environment
            if "VIRTUAL_ENV" not in os.environ:
                print_warning("No active virtual environment found")
                return

            # Get current environment path
            env_path = Path(os.environ["VIRTUAL_ENV"])

            # Show environment switch message
            print_success(
                f"Switching environment: {format_env_switch(env_path, None)}"
            )

            # Get shell information
            shell, shell_name = self._get_shell()

            # Get shell-specific commands
            env_vars, ps1_cmd = self._get_shell_commands(
                action="deactivate",
                env_path=env_path,
                shell_name=shell_name,
            )

            # Convert env_vars to shell export commands
            exports = " ".join(
                f"export {k}='{v}';" for k, v in env_vars.items()
            )

            # Execute shell with clean environment
            os.execl(
                shell,
                shell_name,
                "-c",
                f"unset VIRTUAL_ENV PATH; {exports} {ps1_cmd} && exec {shell}",
            )

        except Exception as e:
            raise RuntimeError(
                f"Failed to deactivate virtual environment: {str(e)}"
            )

    def find_default_venv(self) -> Optional[Path]:
        """Find the default virtual environment in the current directory"""
        try:
            return self.analyzer._find_venv_path()
        except Exception:
            return None
