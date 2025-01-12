# Environment management service providing virtual environment handling and status tracking
import os
import subprocess
import sys
import venv
import tomllib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Literal
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.table import Table
from rich.prompt import Confirm

console = Console()


class VenvError(Exception):
    """Base class for virtual environment related errors"""

    pass


class VenvNotFoundError(VenvError):
    """Raised when virtual environment is not found"""

    pass


class VenvActivationError(VenvError):
    """Raised when virtual environment activation fails"""

    pass


class VenvValidationError(VenvError):
    """Raised when virtual environment validation fails"""

    pass


class VenvStatus:
    """Tracks the status and health of a virtual environment"""

    def __init__(self):
        self.is_active: bool = False
        self.venv_path: Optional[Path] = None
        self.python_version: Optional[str] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.site_packages: Optional[Path] = None

    def add_warning(self, msg: str) -> None:
        """Add a warning message to the status"""
        self.warnings.append(msg)

    def add_error(self, msg: str) -> None:
        """Add an error message to the status"""
        self.errors.append(msg)

    def is_healthy(self) -> bool:
        """Check if the environment is healthy (no errors)"""
        return not self.errors

    def to_dict(self) -> Dict:
        """Convert status to dictionary format"""
        return {
            "is_active": self.is_active,
            "venv_path": str(self.venv_path) if self.venv_path else None,
            "python_version": self.python_version,
            "errors": self.errors,
            "warnings": self.warnings,
            "site_packages": (
                str(self.site_packages) if self.site_packages else None
            ),
        }


class EnvDisplay:
    """Handles all environment display related functionality"""

    @staticmethod
    def format_env_name(project_name: str) -> str:
        """Format environment name with consistent style"""
        return f"[cyan]{project_name}[/cyan][dim](env)[/dim]"

    @staticmethod
    def format_env_switch(
        from_env: Optional[Path], to_env: Optional[Path]
    ) -> str:
        """Format environment switch with consistent style"""
        if from_env is None:
            from_display = "[dim]none[/dim]"
        else:
            from_name = from_env.parent.absolute().name
            from_display = EnvDisplay.format_env_name(from_name)

        if to_env is None:
            to_display = "[dim]none[/dim]"
        else:
            to_name = to_env.parent.absolute().name
            to_display = EnvDisplay.format_env_name(to_name)

        return f"{from_display} → {to_display}"

    @staticmethod
    def show_confirmation_prompt(cmd: str) -> bool:
        """Display environment change confirmation prompt"""
        return Confirm.ask(
            f"\n[yellow]Do you want to switch environment{' and run ' + cmd if cmd else ''}?[/yellow]"
        )

    @staticmethod
    def show_success(
        from_env: Optional[Path],
        to_env: Optional[Path],
        action: str = "Switching",
    ) -> None:
        """Display success message for environment change"""
        console.print(
            f"\n[green]✓ {action} environment: {EnvDisplay.format_env_switch(from_env, to_env)}[/green]"
        )

    @staticmethod
    def show_error(message: str) -> None:
        """Display error message for environment operation"""
        # Extract environment name for special formatting if present
        import re

        match = re.search(r"(.*?): (.+?)\(env\)(.*)", message)
        if match:
            prefix, env_name, suffix = match.groups()
            formatted_message = (
                f"{prefix}: [cyan]{env_name}[/cyan][dim](env)[/dim]{suffix}"
            )
            console.print(f"\n[yellow]⚠ {formatted_message}[/yellow]")
        else:
            console.print(f"\n[yellow]⚠ {message}[/yellow]")


def display_env_switch(
    from_env: Path, to_env: Path, action: str = "Switching"
) -> None:
    """Display environment switch with consistent style

    Args:
        from_env: Source environment path
        to_env: Target environment path
        action: Action being performed ("Switching" or "Activating")
    """
    EnvDisplay.show_warning(from_env, to_env, action)


def get_current_venv_display() -> str:
    """Get current virtual environment display string

    Returns:
        A string showing current venv status, or empty if no venv is active
    """
    if venv_path := os.environ.get("VIRTUAL_ENV"):
        display = EnvDisplay()
        return display.format_env_name(Path(venv_path).parent.name)
    return ""


class EnvManager:
    """Manages virtual environment operations including creation, activation, deactivation, and information retrieval"""

    def __init__(
        self, to_env: Optional[Path] = None, project_root: Optional[Path] = None
    ):
        self.project_root = project_root or Path.cwd()
        self.from_env = (
            Path(os.environ["VIRTUAL_ENV"])
            if "VIRTUAL_ENV" in os.environ
            else None
        )
        self.to_env = to_env or Path("env")
        self.display = EnvDisplay()
        self._status = VenvStatus()
        self._check_updates = False
        self._initialize_status()

    def _initialize_status(self) -> None:
        """Initialize the virtual environment status"""
        self._status.venv_path = self.to_env
        self._status.is_active = bool(os.environ.get("VIRTUAL_ENV"))

        if self.to_env.exists():
            try:
                # Get Python version
                python_path = self.to_env / "bin" / "python"
                if python_path.exists():
                    result = subprocess.run(
                        [str(python_path), "--version"],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        self._status.python_version = (
                            result.stdout.strip().replace("Python ", "")
                        )

                # Get site-packages
                self._status.site_packages = self._get_site_packages()
            except Exception as e:
                self._status.add_error(
                    f"Failed to initialize environment status: {str(e)}"
                )

    def _get_site_packages(self) -> Optional[Path]:
        """Get the site-packages directory path"""
        python_path = self.to_env / "bin" / "python"
        if not python_path.exists():
            return None

        try:
            result = subprocess.run(
                [
                    str(python_path),
                    "-c",
                    "import site; print(site.getsitepackages()[0])",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            return None

    def check_health(self) -> VenvStatus:
        """Perform a comprehensive health check of the virtual environment"""
        status = VenvStatus()
        status.venv_path = self.to_env
        status.is_active = bool(os.environ.get("VIRTUAL_ENV"))

        # Check if virtual environment exists
        if not self.to_env.exists():
            status.add_error("Virtual environment not found")
            return status

        # Check Python interpreter
        python_path = self.to_env / "bin" / "python"
        if not python_path.exists():
            status.add_error("Python interpreter not found")
        else:
            # Get Python version
            try:
                result = subprocess.run(
                    [str(python_path), "--version"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    status.python_version = result.stdout.strip().replace(
                        "Python ", ""
                    )
                else:
                    status.add_warning("Could not determine Python version")
            except Exception:
                status.add_warning("Failed to get Python version")

        # Check site-packages
        site_packages = self._get_site_packages()
        if site_packages:
            status.site_packages = site_packages
            if not site_packages.exists():
                status.add_warning("site-packages directory not found")
        else:
            status.add_warning("Could not determine site-packages location")

        # Check core packages
        if site_packages and site_packages.exists():
            for pkg in ["pip", "setuptools", "wheel"]:
                pkg_path = site_packages / f"{pkg}.dist-info"
                if not pkg_path.exists():
                    status.add_warning(f"Core package {pkg} is missing")

        return status

    def create(self) -> Tuple[bool, str]:
        """Create a new virtual environment"""
        try:
            # Check if directory already exists
            if self.to_env.exists():
                return False, f"Directory '{self.to_env}' already exists"

            # Create virtual environment
            venv.create(self.to_env, with_pip=True)

            # Update status
            self._initialize_status()

            return True, f"Virtual environment created at {self.to_env}"
        except Exception as e:
            return False, f"Failed to create virtual environment: {str(e)}"

    def _get_pip_info(self) -> Dict:
        """Get pip version and update information"""
        info = {"version": None, "location": None, "update_available": None}

        try:
            # Get pip version
            result = subprocess.run(
                ["pip", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                version_output = result.stdout.split()
                info["version"] = version_output[1]
                info["location"] = version_output[3]

            # Check for updates (only if explicitly requested)
            if self._check_updates:
                result = subprocess.run(
                    ["pip", "list", "--outdated", "--format=json"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    import json

                    outdated = json.loads(result.stdout)
                    for pkg in outdated:
                        if pkg["name"] == "pip":
                            info["update_available"] = pkg["latest_version"]
                            break
        except Exception:
            pass

        return info

    def get_env_info(self, check_updates: bool = False) -> Dict:
        """Get comprehensive environment information

        Args:
            check_updates: Whether to check for pip updates (slower)
        """
        # Set update check flag
        self._check_updates = check_updates

        status = self.check_health()

        # Get platform information
        platform_name = {
            "darwin": "macOS",
            "linux": "Linux",
            "win32": "Windows",
        }.get(sys.platform, sys.platform)

        # Get CPU architecture (cache it)
        if not hasattr(self, "_arch"):
            try:
                self._arch = subprocess.check_output(
                    ["uname", "-m"], text=True
                ).strip()
            except:
                self._arch = "unknown"

        # Get pip information
        pip_info = self._get_pip_info()

        return {
            "python_version": status.python_version,
            "platform": f"{platform_name} ({self._arch})",
            "virtual_env": os.environ.get("VIRTUAL_ENV"),
            "working_dir": str(self.project_root),
            "pip_version": pip_info.get("version"),
            "pip_location": pip_info.get("location"),
            "pip_update": pip_info.get("update_available"),
            "user_scripts": Path.home() / ".local/bin",
            "status": status.to_dict(),
        }

    @classmethod
    def get_current_env(cls) -> Optional[Path]:
        """Get current virtual environment if any"""
        return (
            Path(os.environ["VIRTUAL_ENV"])
            if "VIRTUAL_ENV" in os.environ
            else None
        )

    @classmethod
    def get_env_meta(cls, path: Optional[Path] = None) -> dict:
        """Get environment metadata

        Args:
            path: Path to environment, defaults to current directory's env

        Returns:
            Dictionary containing:
            - name: Full display name (e.g. "test2(env)")
            - env_name: Environment name (e.g. "env")
            - project_name: Project name (e.g. "test2")
            - path: Full path to environment
            - exists: Whether environment exists
            - is_active: Whether this environment is currently active
            - python_version: Python version in this environment
            - pip_version: Pip version in this environment
        """
        # Default to current directory's env
        env_path = path or Path("env")

        # Get project and environment names
        project_name = env_path.parent.absolute().name
        env_name = env_path.name

        # Check if environment exists
        if not env_path.exists():
            return {
                "name": f"{project_name}({env_name})",
                "env_name": env_name,
                "project_name": project_name,
                "path": str(env_path.absolute()),
                "exists": False,
                "is_active": False,
                "python_version": None,
                "pip_version": None,
            }

        # Get current active environment
        current_env = cls.get_current_env()
        is_active = current_env and current_env.samefile(env_path)

        # Get Python and pip versions
        python_version = None
        pip_version = None
        try:
            python_path = env_path / "bin" / "python"
            if python_path.exists():
                result = subprocess.run(
                    [str(python_path), "--version"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    python_version = result.stdout.strip().replace(
                        "Python ", ""
                    )

                # Get pip version
                result = subprocess.run(
                    [str(python_path), "-m", "pip", "--version"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    pip_version = result.stdout.split()[1]
        except Exception:
            pass

        return {
            "name": f"{project_name}({env_name})",
            "env_name": env_name,
            "project_name": project_name,
            "path": str(env_path.absolute()),
            "exists": True,
            "is_active": is_active,
            "python_version": python_version,
            "pip_version": pip_version,
        }

    def _set_env_vars(self, env_path: Path) -> None:
        """Set environment variables for virtual environment activation

        Args:
            env_path: Path to the virtual environment
        """
        os.environ["VIRTUAL_ENV"] = str(env_path.absolute())
        os.environ["PATH"] = f"{env_path}/bin:{os.environ['PATH']}"
        if "PYTHONHOME" in os.environ:
            del os.environ["PYTHONHOME"]

    def _unset_env_vars(self, env_path: Path) -> None:
        """Unset environment variables for virtual environment deactivation

        Args:
            env_path: Path to the virtual environment
        """
        if "VIRTUAL_ENV" in os.environ:
            del os.environ["VIRTUAL_ENV"]
        if "PYTHONHOME" in os.environ:
            del os.environ["PYTHONHOME"]
        # Update PATH
        paths = os.environ["PATH"].split(":")
        paths = [p for p in paths if str(env_path) not in p]
        os.environ["PATH"] = ":".join(paths)

    def _check_python_executable(self) -> bool:
        """Check if Python executable exists and is valid

        Returns:
            bool: True if Python executable is valid
        """
        if self.to_env is None:
            return False

        python_path = self.to_env / "bin" / "python"
        if not python_path.exists():
            self.display.show_error(
                f"Python executable not found in environment: {self.to_env}"
            )
            return False

        try:
            result = subprocess.run(
                [str(python_path), "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.display.show_error(
                    f"Python executable validation failed: {result.stderr}"
                )
                return False
        except Exception as e:
            self.display.show_error(
                f"Failed to validate Python executable: {str(e)}"
            )
            return False

        return True

    @staticmethod
    def _get_shell() -> Tuple[str, str]:
        """Get the current shell executable path and name"""
        shell = os.environ.get("SHELL", "/bin/sh")
        shell_name = Path(shell).name
        return shell, shell_name

    def _get_shell_commands(
        self,
        *,
        action: Literal["activate", "deactivate"],
        env_path: Path,
        shell_name: str,
    ) -> Tuple[dict[str, str], str]:
        """Get shell-specific commands for environment operations

        Args:
            action: The action to perform ("activate" or "deactivate")
            env_path: Path to the environment
            shell_name: Name of the shell (e.g. "zsh", "bash")

        Returns:
            Tuple containing:
            - Dictionary of environment variables to set
            - Shell-specific PS1/PROMPT command
        """
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

    @classmethod
    def activate(
        cls, env_path: Optional[Path] = None, *, execute_shell: bool = True
    ) -> bool:
        """Activate the specified virtual environment

        This method handles the activation of a virtual environment by:
        1. Validating the environment and its Python executable
        2. Setting up environment variables (PATH, VIRTUAL_ENV)
        3. Optionally executing the shell activation script

        Args:
            env_path: Path to environment, defaults to current directory's env
            execute_shell: Whether to execute shell command and replace current process

        Returns:
            bool: True if activation was successful, False otherwise

        Note:
            When execute_shell is True, this method will replace the current process
            with a new shell process that has the virtual environment activated.
            When False, it will only set environment variables without process replacement.
        """
        manager = cls(env_path or Path("env"))

        # Basic environment validation
        if not manager._validate():
            return False

        # Additional Python executable validation
        if not manager._check_python_executable():
            return False

        try:
            # Check if trying to switch to the same environment
            if (
                manager.from_env
                and manager.to_env
                and manager.from_env.samefile(manager.to_env)
            ):
                manager.display.show_error(
                    f"Environment is already active: {manager.from_env.parent.name}(env)"
                )
                return False

            if not execute_shell:
                # Set environment variables
                manager._set_env_vars(manager.to_env)
                manager.display.show_success(
                    manager.from_env, manager.to_env, "Setting up"
                )
            else:
                # For shell replacement, directly set environment variables
                manager.display.show_success(
                    manager.from_env, manager.to_env, "Activating shell with"
                )
                shell, shell_name = manager._get_shell()

                # Get shell-specific commands
                env_vars, ps1_cmd = manager._get_shell_commands(
                    action="activate",
                    env_path=manager.to_env,
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
                    f"{exports} {ps1_cmd} && exec {shell_name}",
                )
            return True

        except Exception as e:
            # Clean up on failure
            if not execute_shell and manager.to_env:
                manager._unset_env_vars(manager.to_env)
            manager.display.show_error(
                f"Failed to activate environment: {str(e)}"
            )

        return False

    @classmethod
    def deactivate(
        cls, env_path: Optional[Path] = None, *, execute_shell: bool = True
    ) -> bool:
        """Deactivate the current virtual environment

        Args:
            env_path: Path to environment, defaults to current directory's env
            execute_shell: Whether to execute shell command and replace current process
        """
        manager = cls(env_path or Path("env"))

        if not manager.from_env:
            manager.display.show_error("No active virtual environment")
            return False

        try:
            if not execute_shell:
                # Just unset environment variables
                manager._unset_env_vars(manager.from_env)
                manager.display.show_success(
                    manager.from_env, None, "Cleaning up"
                )
            else:
                # For shell replacement
                manager.display.show_success(
                    manager.from_env, None, "Deactivating shell with"
                )
                shell, shell_name = manager._get_shell()

                # Get shell-specific commands
                env_vars, ps1_cmd = manager._get_shell_commands(
                    action="deactivate",
                    env_path=manager.from_env,
                    shell_name=shell_name,
                )

                # Convert env_vars to shell export commands
                exports = " ".join(
                    f"export {k}='{v}';" for k, v in env_vars.items()
                )

                # Execute shell with cleaned environment
                os.execl(
                    shell,
                    shell_name,
                    "-c",
                    f"{exports} {ps1_cmd} && exec {shell_name}",
                )
            return True

        except Exception as e:
            manager.display.show_error(
                f"Failed to deactivate environment: {str(e)}"
            )
            return False

    @classmethod
    def exists(cls, env_path: Optional[Path] = None) -> bool:
        """Check if environment exists and is valid

        Args:
            env_path: Path to environment, defaults to current directory's env
        """
        env = cls(env_path or Path("env"))
        return env._validate()

    def _validate(self) -> bool:
        """Internal method to validate environment configuration"""
        if self.to_env is None:
            return True

        if not self.to_env.exists():
            self.display.show_error(
                f"Environment does not exist: {self.to_env}"
            )
            return False

        activate_script = self.to_env / "bin" / "activate"
        if not activate_script.exists():
            self.display.show_error(
                f"Activation script not found at {activate_script}"
            )
            return False

        return True

    def _prepare_shell_command(self, cmd: str, action: str) -> Optional[str]:
        """Prepare shell command for environment operation"""
        shell, shell_name = self._get_shell()

        if action == "Deactivating":
            if not self.from_env or not self.from_env.exists():
                return f"unset VIRTUAL_ENV && unset PYTHONHOME && export PATH=$(echo $PATH | tr ':' '\n' | grep -v {self.from_env}/bin | tr '\n' ':' | sed 's/:$//') && exec {shell_name}"
            else:
                activate_script = self.from_env / "bin" / "activate"
                return f"source {activate_script} && deactivate && exec {shell_name}"
        else:
            if self.to_env is None:
                return None

            activate_script = self.to_env / "bin" / "activate"
            return (
                f"source {activate_script} && {cmd} && exec {shell_name}"
                if cmd
                else f"source {activate_script} && exec {shell_name}"
            )

    def _execute_shell_command(self, shell_cmd: str) -> None:
        """Execute shell command for environment operation"""
        shell, shell_name = self._get_shell()
        os.execl(shell, shell_name, "-c", shell_cmd)

    def switch(self, cmd: str = "", action: str = "Switching") -> bool:
        """Handle environment switching process"""
        try:
            if not self._validate():
                return False

            # Check if trying to switch to the same environment
            if (
                self.from_env
                and self.to_env
                and self.from_env.samefile(self.to_env)
            ):
                if action == "Deactivating":
                    # For deactivation, set to_env to None to show proper transition
                    self.to_env = None
                else:
                    self.display.show_error(
                        f"Environment is already active: {self.from_env.parent.name}(env)"
                    )
                    return False

            if not cmd or self.display.show_confirmation_prompt(cmd):
                shell_cmd = self._prepare_shell_command(cmd, action)
                if shell_cmd:
                    self.display.show_success(
                        self.from_env, self.to_env, action
                    )
                    self._execute_shell_command(shell_cmd)
                    return True

        except Exception as e:
            self.display.show_error(
                f"Failed to {action.lower()} environment: {str(e)}"
            )

        return False

    def install_requirements(self) -> Tuple[bool, str]:
        """Install packages from requirements.txt

        Returns:
            Tuple of (success, message)
        """
        if not Path("requirements.txt").exists():
            return False, "No requirements.txt found"

        try:
            # Get Python path from virtual environment
            python_path = self.to_env / "bin" / "python"
            if not python_path.exists():
                return False, "Python interpreter not found"

            # Upgrade pip first
            result = subprocess.run(
                [str(python_path), "-m", "pip", "install", "--upgrade", "pip"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return False, f"Failed to upgrade pip: {result.stderr}"

            # Read packages from requirements.txt
            with open("requirements.txt") as f:
                packages = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]

            # Install packages using the activated environment
            from .package import PackageManager

            package_manager = PackageManager()
            console.print("")  # Add empty line for better formatting

            for package in packages:
                with console.status(
                    f"[yellow]Installing {package}...[/yellow]", spinner="dots"
                ):
                    if "==" in package:
                        name, version = package.split("==")
                        success, error = package_manager.add(name, version)
                    else:
                        success, error = package_manager.add(package)

                    if not success:
                        return False, f"Failed to install {package}: {error}"

            return True, "Successfully installed all packages"
        except Exception as e:
            return False, f"Failed to install packages: {str(e)}"
