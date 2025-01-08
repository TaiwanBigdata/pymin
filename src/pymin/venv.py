# Environment management service providing virtual environment handling and status tracking
import os
import subprocess
import sys
import venv
import tomllib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
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


class VenvManager:
    """Manages virtual environment operations and status"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.venv_path = self.project_root / "env"
        self._status = VenvStatus()
        self._check_updates = False  # Add flag for pip updates check
        self._initialize_status()

    def _initialize_status(self) -> None:
        """Initialize the virtual environment status"""
        self._status.venv_path = self.venv_path
        self._status.is_active = bool(os.environ.get("VIRTUAL_ENV"))

        if self.venv_path.exists():
            try:
                # Get Python version
                python_path = self.venv_path / "bin" / "python"
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
        python_path = self.venv_path / "bin" / "python"
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
        status.venv_path = self.venv_path
        status.is_active = bool(os.environ.get("VIRTUAL_ENV"))

        # Check if virtual environment exists
        if not self.venv_path.exists():
            status.add_error("Virtual environment not found")
            return status

        # Check Python interpreter
        python_path = self.venv_path / "bin" / "python"
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

    def create(self, name: str = "env") -> Tuple[bool, str]:
        """Create a new virtual environment"""
        venv_path = self.project_root / name

        try:
            # Check if directory already exists
            if venv_path.exists():
                return False, f"Directory '{name}' already exists"

            # Create virtual environment
            venv.create(venv_path, with_pip=True)

            # Update status
            self.venv_path = venv_path
            self._initialize_status()

            return True, f"Virtual environment created at {venv_path}"
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

    def get_environment_info(self, check_updates: bool = False) -> Dict:
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

    def display_info(self) -> None:
        """Display formatted environment information"""
        info = self.get_environment_info()
        status = info["status"]

        text = Text()
        text.append("\nEnvironment Status\n", style="bold white")

        # Virtual Environment Status
        text.append("Status: ", style="dim")
        if status["is_active"]:
            text.append("✓ Active\n", style="green")
        else:
            text.append("Not Active\n", style="yellow")

        # Path Information
        text.append("Location: ", style="dim")
        text.append(
            f"{status['venv_path']}\n",
            style="dim white",
        )

        # Python Information
        text.append("Python Version: ", style="dim")
        text.append(f"{info['python_version']}\n", style="cyan")

        # Platform Information
        text.append("Platform: ", style="dim")
        text.append(f"{info['platform']}\n", style="cyan")

        # Pip Information
        text.append("Pip: ", style="dim")
        if info["pip_version"]:
            text.append(f"{info['pip_version']}", style="cyan")
            if info["pip_update"]:
                text.append(
                    f" (update available: {info['pip_update']})", style="yellow"
                )
        text.append("\n")

        # Warnings and Errors
        if status["warnings"]:
            text.append("\nWarnings:\n", style="yellow")
            for warning in status["warnings"]:
                text.append(f"  • {warning}\n", style="yellow")

        if status["errors"]:
            text.append("\nErrors:\n", style="red")
            for error in status["errors"]:
                text.append(f"  • {error}\n", style="red")

        panel = Panel(
            text, title="Virtual Environment Status", border_style="bright_blue"
        )
        console.print(panel)


class EnvTransitionDisplay:
    """Handles all environment transition related displays"""

    @staticmethod
    def format_env_name(project_name: str) -> str:
        """Format environment name with consistent style"""
        return f"[cyan]{project_name}[/cyan][dim white](env)[/dim white]"

    @staticmethod
    def format_transition(
        from_env: Optional[Path], to_env: Optional[Path]
    ) -> str:
        """Format environment transition with consistent style"""
        if from_env is None:
            from_display = "[dim white]none[/dim white]"
        else:
            from_name = from_env.parent.absolute().name
            from_display = EnvTransitionDisplay.format_env_name(from_name)

        if to_env is None:
            to_display = "[dim white]none[/dim white]"
        else:
            to_name = to_env.parent.absolute().name
            to_display = EnvTransitionDisplay.format_env_name(to_name)

        return f"{from_display} → {to_display}"

    @staticmethod
    def show_warning(
        from_env: Optional[Path],
        to_env: Optional[Path],
        action: str = "Switching",
    ) -> None:
        """Display warning about environment transition"""
        console.print(f"\n[yellow]⚠ Virtual Environment {action}:[/yellow]")
        console.print(
            f"  {EnvTransitionDisplay.format_transition(from_env, to_env)}"
        )

    @staticmethod
    def show_confirmation_prompt(cmd: str) -> bool:
        """Display environment transition confirmation prompt"""
        return Confirm.ask(
            f"\n[yellow]Do you want to switch environment{' and run ' + cmd if cmd else ''}?[/yellow]"
        )

    @staticmethod
    def show_success(
        from_env: Optional[Path],
        to_env: Optional[Path],
        action: str = "Switching",
    ) -> None:
        """Display success message for environment transition"""
        console.print(
            f"\n[green]✓ {action} environment: {EnvTransitionDisplay.format_transition(from_env, to_env)}[/green]"
        )

    @staticmethod
    def show_error(message: str) -> None:
        """Display error message for environment transition"""
        console.print(f"\n[red]✗ {message}[/red]")


def display_env_transition(
    from_env: Path, to_env: Path, action: str = "Switching"
) -> None:
    """Display environment transition with consistent style

    Args:
        from_env: Source environment path
        to_env: Target environment path
        action: Action being performed ("Switching" or "Activating")
    """
    EnvTransitionDisplay.show_warning(from_env, to_env, action)


# Remove old standalone functions that are now part of EnvTransitionDisplay
def get_environment_display_name(venv_path: Path) -> str:
    """Get formatted display name for virtual environment

    Returns:
        A string in format: ⚡ project_name(env_name) path/to/env
    """
    try:
        # Get project directory name (parent of venv directory)
        project_name = venv_path.parent.name
        env_name = venv_path.name
        # For environment switching display (not dimmed)
        if getattr(get_environment_display_name, "switching_display", False):
            return f"⚡ [cyan]{project_name}[/cyan]({env_name}) [dim]{venv_path.absolute()}[/dim]"
        # For normal display (all dimmed except project name)
        return f"[dim]⚡ [cyan]{project_name}[/cyan]({env_name}) [white]{venv_path.absolute()}[/white][/dim]"
    except:
        return "[dim]⚡ (env) unknown[/dim]"


def get_current_venv_display() -> str:
    """Get current virtual environment display string

    Returns:
        A string showing current venv status, or empty if no venv is active
    """
    if venv_path := os.environ.get("VIRTUAL_ENV"):
        return get_environment_display_name(Path(venv_path))
    return ""


class EnvTransitionManager:
    """Manages environment transitions including switching and activation"""

    def __init__(self, from_env: Optional[Path], to_env: Optional[Path]):
        self.from_env = from_env
        self.to_env = to_env
        self.display = EnvTransitionDisplay()

    def switch(self, cmd: str = "", action: str = "Switching") -> bool:
        """Handle environment switching process

        Args:
            cmd: Command to run after switching
            action: Action being performed ("Switching" or "Activating" or "Deactivating")

        Returns:
            bool: True if switch was successful, False otherwise
        """
        try:
            # Show warning and get confirmation
            self.display.show_warning(self.from_env, self.to_env, action)

            if not cmd or self.display.show_confirmation_prompt(cmd):
                # Prepare shell command
                from .utils import get_current_shell

                shell, shell_name = get_current_shell()

                if action == "Deactivating":
                    if not self.from_env or not self.from_env.exists():
                        # If virtual environment folder doesn't exist, directly unset environment variables
                        shell_cmd = f"unset VIRTUAL_ENV && unset PYTHONHOME && export PATH=$(echo $PATH | tr ':' '\n' | grep -v {self.from_env}/bin | tr '\n' ':' | sed 's/:$//') && exec {shell_name}"
                    else:
                        # If virtual environment folder exists, use the original method
                        activate_script = self.from_env / "bin" / "activate"
                        shell_cmd = f"source {activate_script} && deactivate && exec {shell_name}"
                else:
                    # For activation and switching
                    if self.to_env is None:
                        self.display.show_error(
                            "Target environment is not specified"
                        )
                        return False

                    activate_script = self.to_env / "bin" / "activate"
                    if not activate_script.exists():
                        self.display.show_error(
                            f"Activation script not found at {activate_script}"
                        )
                        return False

                    shell_cmd = (
                        f"source {activate_script} && {cmd} && exec {shell_name}"
                        if cmd
                        else f"source {activate_script} && exec {shell_name}"
                    )

                # Show success message
                self.display.show_success(self.from_env, self.to_env, action)

                # Execute shell command
                os.execl(shell, shell_name, "-c", shell_cmd)
                return True

        except Exception as e:
            self.display.show_error(
                f"Failed to {action.lower()} environment: {str(e)}"
            )
            return False

        return False
