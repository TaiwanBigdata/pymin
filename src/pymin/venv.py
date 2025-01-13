# Environment management service providing virtual environment handling and status tracking
import os
import subprocess
import sys
import venv
import tomllib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Literal, Union, Callable
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


class VenvDetector:
    """Virtual environment detector for finding and validating virtual environments"""

    class VenvPattern:
        """Virtual environment naming patterns and configurations"""

        # Default name recommended by PEP 405
        DEFAULT = ".venv"

        # Standard patterns in order of preference
        STANDARD_PATTERNS = [
            ".venv",  # PEP 405 recommendation
            "venv",  # Python venv default
            ".env",  # Legacy pattern
            "env",  # Legacy pattern
        ]

        # Common prefixes and suffixes for custom environments
        CUSTOM_PREFIXES = [".", ""]
        CUSTOM_SUFFIXES = ["venv", "env"]

        @classmethod
        def get_custom_patterns(cls) -> list[str]:
            """Generate patterns for custom virtual environment names

            Returns:
                List of glob patterns for finding custom virtual environments
            """
            patterns = []
            # Add exact matches first
            patterns.extend(cls.STANDARD_PATTERNS)
            # Add custom combinations
            for prefix in cls.CUSTOM_PREFIXES:
                for suffix in cls.CUSTOM_SUFFIXES:
                    pattern = f"*{prefix}{suffix}"
                    if pattern not in patterns:
                        patterns.append(pattern)
            return patterns

    @classmethod
    def is_venv_dir(cls, path: Path) -> bool:
        """Check if a directory is a valid virtual environment

        Args:
            path: Directory path to check

        Returns:
            bool: True if directory is a valid virtual environment
        """
        return (path / "bin" / "python").exists() and (
            path / "bin" / "activate"
        ).exists()

    @classmethod
    def find_in_directory(cls, directory: Path) -> Optional[Path]:
        """Find virtual environment in the specified directory

        This method will:
        1. Check if the directory itself is a virtual environment
        2. Look for standard virtual environment names
        3. Look for custom virtual environment patterns
        4. Return None if no valid environment is found

        Args:
            directory: Directory to search in

        Returns:
            Path to virtual environment if found, None otherwise
        """
        # Resolve to absolute path
        directory = directory.absolute()

        # Case 1: Check if the directory itself is a virtual environment
        if cls.is_venv_dir(directory):
            return directory

        # Case 2: Check standard patterns in order of preference
        for name in cls.VenvPattern.STANDARD_PATTERNS:
            venv_path = directory / name
            if cls.is_venv_dir(venv_path):
                return venv_path

        # Case 3: Look for custom patterns
        for pattern in cls.VenvPattern.get_custom_patterns():
            # Skip patterns we've already checked
            if pattern in cls.VenvPattern.STANDARD_PATTERNS:
                continue
            for venv_path in directory.glob(pattern):
                if cls.is_venv_dir(venv_path):
                    return venv_path

        return None

    @classmethod
    def get_env_info(cls, path: Path) -> dict:
        """Get information about a virtual environment

        Args:
            path: Path to virtual environment

        Returns:
            Dictionary containing:
            - project_name: Name of the project (parent directory)
            - env_name: Name of the virtual environment directory
            - exists: Whether the environment exists and is valid
            - is_standard: Whether the environment uses a standard name
        """
        return {
            "project_name": path.parent.absolute().name,
            "env_name": path.name,
            "exists": cls.is_venv_dir(path),
            "is_standard": path.name in cls.VenvPattern.STANDARD_PATTERNS,
        }


class EnvDisplay:
    """Handles all environment display related functionality"""

    @staticmethod
    def format_env_name(path: Union[str, Path, None] = None) -> str:
        """Format environment name with consistent style

        This method can handle different types of input:
        1. None: Will look for virtual environment in current directory
        2. Path object: Can be either:
           - Path to the virtual environment directory
           - Path to the project directory (will auto-detect venv)
        3. String: Will be converted to Path and handled as above

        Args:
            path: Path to either:
                 - Virtual environment directory
                 - Project directory (will auto-detect venv)
                 If None, uses current directory

        Returns:
            Formatted environment name string with Rich markup
        """
        # Convert to Path if string
        if isinstance(path, str):
            path = Path(path)

        # Default to current directory if None
        if path is None:
            path = Path.cwd()

        # Try to find virtual environment
        venv_path = VenvDetector.find_in_directory(path)
        if venv_path is None:
            # If no environment found, use the path itself
            env_info = VenvDetector.get_env_info(path)
            return f"[cyan]{env_info['project_name']}[/cyan][dim](no env)[/dim]"

        # Get environment info
        env_info = VenvDetector.get_env_info(venv_path)
        return f"[cyan]{env_info['project_name']}[/cyan][dim]({env_info['env_name']})[/dim]"

    @staticmethod
    def format_env_status(path: Union[str, Path, None] = None) -> str:
        """Format environment status with lightning bolt, name and full path

        Args:
            path: Path to either:
                 - Virtual environment directory
                 - Project directory (will auto-detect venv)
                 If None, uses current directory

        Returns:
            Formatted status string with Rich markup including lightning bolt,
            environment name and full path
        """
        # Convert to Path if string
        if isinstance(path, str):
            path = Path(path)

        # Default to current directory if None
        if path is None:
            path = Path.cwd()

        # Try to find virtual environment
        venv_path = VenvDetector.find_in_directory(path)
        if venv_path is None:
            # If no environment found, use the path itself
            env_info = VenvDetector.get_env_info(path)
            return f"[bright_blue]⚡[/bright_blue] [cyan]{env_info['project_name']}[/cyan][dim](no env)[/dim] [dim white]{path.absolute()}[/dim white]"

        # Get environment info
        env_info = VenvDetector.get_env_info(venv_path)
        return f"[bright_blue]⚡[/bright_blue] [cyan]{env_info['project_name']}[/cyan][dim]({env_info['env_name']})[/dim] [dim white]{path.absolute()}[/dim white]"

    @staticmethod
    def format_env_switch(
        from_env: Optional[Path], to_env: Optional[Path]
    ) -> str:
        """Format environment switch with consistent style"""
        if from_env is None:
            from_display = "[dim]none[/dim]"
        else:
            from_display = EnvDisplay.format_env_name(from_env)

        if to_env is None:
            to_display = "[dim]none[/dim]"
        else:
            to_display = EnvDisplay.format_env_name(to_env)

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
            f"[green]✓ {action} environment: {EnvDisplay.format_env_switch(from_env, to_env)}[/green]"
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
            console.print(f"[yellow]⚠ {formatted_message}[/yellow]")
        else:
            console.print(f"[yellow]⚠ {message}[/yellow]")


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

    @classmethod
    def create(
        cls,
        env_path: Optional[Path] = None,
        *,
        rebuild: bool = False,
    ) -> Tuple[bool, str]:
        """Create a new virtual environment

        Args:
            env_path: Path to environment, defaults to current directory's env
            rebuild: Whether to rebuild if environment exists

        Returns:
            Tuple of (success, message)
        """
        import shutil

        manager = cls(env_path or Path("env"))

        # Check if environment exists
        if manager.to_env.exists():
            if not rebuild:
                return False, "Environment already exists"

            # Check if environment is active
            current_env = cls.get_current_env()
            if current_env and current_env.samefile(manager.to_env):
                console.print("\n[yellow]Active environment detected[/yellow]")

                # Deactivate the environment
                console.print("\n[blue]Deactivating environment...[/blue]")
                if not cls.deactivate(execute_shell=False):
                    return False, "Failed to deactivate environment"

            # Remove existing environment
            try:
                shutil.rmtree(manager.to_env)
                console.print(
                    "[green]✓ Removing existing environment...[/green]"
                )
            except Exception as e:
                return False, f"Failed to remove existing environment: {str(e)}"

        # Create new environment
        try:
            venv.create(manager.to_env, with_pip=True)

            # Get environment info using VenvDetector
            env_info = VenvDetector.get_env_info(manager.to_env)

            # Get Python and pip versions
            python_path = manager.to_env / "bin" / "python"
            python_version = None
            pip_version = None

            if python_path.exists():
                # Get Python version
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

            # Display environment info
            text = Text.assemble(
                ("Virtual Environment: ", "dim"),
                (env_info["project_name"], "cyan"),
                (f"({env_info['env_name']})", "dim"),
                "\n",
                ("Python Version: ", "dim"),
                (python_version or "Unknown", "cyan"),
                "\n",
                ("Pip Version: ", "dim"),
                (pip_version or "Unknown", "cyan"),
                "\n",
                ("Location: ", "dim"),
                (str(manager.to_env.absolute()), "cyan"),
                "\n",
                ("Status: ", "dim"),
                ("✓", "green bold"),
                (" Created", "green bold"),
            )
            panel = Panel.fit(
                text,
                title="Virtual Environment Status",
                title_align="left",
                border_style="bright_blue",
            )
            console.print(panel)

            return True, "Environment created successfully"
        except Exception as e:
            return False, f"Failed to create environment: {str(e)}"

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

    def get_env_info(self, *, check_updates: bool = False) -> Dict[str, str]:
        """Get information about the virtual environment

        Args:
            check_updates: Whether to check for pip updates

        Returns:
            Dictionary containing environment information
        """
        python_path = self.to_env / "bin" / "python"
        if not python_path.exists():
            raise VenvError("Python interpreter not found")

        try:
            # Get Python version
            result = subprocess.run(
                [str(python_path), "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            python_version = result.stdout.strip().replace("Python ", "")

            # Get pip version and info
            result = subprocess.run(
                [str(python_path), "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            pip_version = result.stdout.split()[1]
            pip_location = result.stdout.split()[3]

            # Get project name from parent directory
            project_name = self.to_env.parent.absolute().name

            # Get platform info
            import platform

            platform_info = f"{platform.system()} {platform.release()}"

            # Get user scripts directory
            user_scripts = str(self.to_env / "bin")

            info = {
                "project_name": project_name,
                "python_version": python_version,
                "pip_version": pip_version,
                "pip_location": pip_location,
                "platform": platform_info,
                "working_dir": str(self.to_env.absolute()),
                "user_scripts": user_scripts,
                "virtual_env": os.environ.get("VIRTUAL_ENV"),
            }

            # Check for pip updates if requested
            if check_updates:
                try:
                    result = subprocess.run(
                        [
                            str(python_path),
                            "-m",
                            "pip",
                            "list",
                            "--outdated",
                            "--format=json",
                        ],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        import json

                        outdated = json.loads(result.stdout)
                        for pkg in outdated:
                            if pkg["name"] == "pip":
                                info["pip_update"] = pkg["latest_version"]
                                break
                except Exception:
                    pass

            return info

        except subprocess.CalledProcessError as e:
            raise VenvError(f"Failed to get environment info: {e.stderr}")
        except Exception as e:
            raise VenvError(f"Failed to get environment info: {str(e)}")

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
        """Activate the specified virtual environment"""
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
                    manager.from_env,
                    manager.to_env,
                    "Setting up",
                )
            else:
                # For shell replacement, directly set environment variables
                manager.display.show_success(
                    manager.from_env,
                    manager.to_env,
                    "Activating shell with",
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
                    f"unset VIRTUAL_ENV PATH; {exports} {ps1_cmd} && exec {shell}",
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
    def deactivate(cls, *, execute_shell: bool = True) -> bool:
        """Deactivate the current virtual environment"""
        manager = cls()

        # Check if any environment is active
        if not manager.from_env:
            manager.display.show_error("No active environment to deactivate")
            return False

        try:
            if not execute_shell:
                # Clean environment variables
                manager._unset_env_vars(manager.from_env)
                manager.display.show_success(
                    manager.from_env,
                    None,
                    "Setting up",
                )
            else:
                # For shell replacement, directly unset environment variables
                manager.display.show_success(
                    manager.from_env,
                    None,
                    "Deactivating shell with",
                )
                shell, shell_name = manager._get_shell()

                # Execute shell with clean environment
                os.execl(
                    shell,
                    shell_name,
                    "-c",
                    f"unset VIRTUAL_ENV PATH; exec {shell}",
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

    @staticmethod
    def execute_steps(
        env_path: Path,
        steps: list[Union[str, Callable]],
        *,
        activate_message: str = "Activating shell with",
        on_interrupt: Optional[Callable] = None,
        force: bool = False,
    ) -> None:
        """Execute multiple steps in the same shell with environment activated"""
        manager = EnvManager(env_path)

        # Basic environment validation
        if not manager._validate():
            return

        # Additional Python executable validation
        if not manager._check_python_executable():
            return

        try:
            # Only check active environment if not forcing
            if not force and manager.from_env and manager.to_env:
                if manager.from_env.samefile(manager.to_env):
                    manager.display.show_error(
                        f"Environment is already active: {manager.from_env.parent.name}(env)"
                    )
                    return

            # First set environment variables
            manager._set_env_vars(manager.to_env)

            # Get shell information
            shell, shell_name = manager._get_shell()

            # Get shell-specific commands
            env_vars, ps1_cmd = manager._get_shell_commands(
                action="activate",
                env_path=manager.to_env,
                shell_name=shell_name,
            )

            # Execute Python callable steps first
            for step in steps:
                if callable(step):
                    try:
                        step()
                    except Exception as e:
                        raise Exception(f"Step execution failed: {str(e)}")

            # Prepare shell commands
            shell_commands = [cmd for cmd in steps if isinstance(cmd, str)]

            # Convert env_vars to shell export commands
            exports = []
            for k, v in env_vars.items():
                exports.append(f"export {k}='{v}'")

            # Combine all commands
            all_commands = [
                *exports,  # Environment variables
                ps1_cmd,  # Shell prompt
                *shell_commands,  # Additional shell commands
                f"exec {shell_name}",  # Replace shell
            ]

            # Execute all commands in sequence
            manager.display.show_success(
                None if not manager.from_env else manager.from_env,
                manager.to_env,
                activate_message,
            )
            os.execl(shell, shell_name, "-c", "; ".join(all_commands))

        except KeyboardInterrupt:
            # Handle interrupt
            manager._unset_env_vars(manager.to_env)
            manager.display.show_error("Operation interrupted by user")
            if on_interrupt:
                on_interrupt()
            return

        except Exception as e:
            # Clean up on failure
            manager._unset_env_vars(manager.to_env)
            manager.display.show_error(f"Failed to execute steps: {str(e)}")
            if on_interrupt:
                on_interrupt()
            return
