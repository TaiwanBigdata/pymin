# Virtual environment management functionality
from pathlib import Path
from typing import Optional, Dict, List
import subprocess
import sys
import venv
import os
import platform

from .exceptions import EnvironmentError
from .utils import get_venv_site_packages
from ..ui import console


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


class VenvManager:
    """Manages Python virtual environments."""

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize virtual environment manager.

        Args:
            base_path: Base directory for virtual environments
        """
        self.base_path = base_path or Path.cwd()

    def create(
        self,
        name: str,
        python: Optional[str] = None,
        system_site_packages: bool = False,
        clear: bool = False,
        upgrade_deps: bool = True,
    ) -> Path:
        """
        Create a new virtual environment.

        Args:
            name: Environment name
            python: Optional Python executable path
            system_site_packages: Whether to give access to system packages
            clear: Whether to delete environment if it exists
            upgrade_deps: Whether to upgrade base packages

        Returns:
            Path to created environment

        Raises:
            EnvironmentError: If creation fails
        """
        try:
            venv_path = self.base_path / name

            if venv_path.exists():
                if clear:
                    self.remove(name)
                else:
                    raise EnvironmentError(
                        f"Environment {name} already exists",
                        details=f"Path: {venv_path}",
                    )

            console.start_status(f"Creating virtual environment {name}...")

            # Create the virtual environment
            builder = venv.EnvBuilder(
                system_site_packages=system_site_packages,
                clear=clear,
                upgrade_deps=upgrade_deps,
            )
            builder.create(venv_path)

            console.success(f"Created virtual environment {name}")
            return venv_path

        except Exception as e:
            raise EnvironmentError(
                f"Failed to create environment {name}",
                details=str(e),
            )
        finally:
            console.stop_status()

    def remove(self, name: str) -> None:
        """
        Remove a virtual environment.

        Args:
            name: Environment name

        Raises:
            EnvironmentError: If removal fails
        """
        try:
            venv_path = self.base_path / name

            if not venv_path.exists():
                raise EnvironmentError(
                    f"Environment {name} does not exist",
                    details=f"Path: {venv_path}",
                )

            console.start_status(f"Removing virtual environment {name}...")

            # Remove the directory
            import shutil

            shutil.rmtree(venv_path)

            console.success(f"Removed virtual environment {name}")

        except Exception as e:
            raise EnvironmentError(
                f"Failed to remove environment {name}",
                details=str(e),
            )
        finally:
            console.stop_status()

    def list_environments(self) -> Dict[str, Path]:
        """
        List available virtual environments.

        Returns:
            Dictionary mapping environment names to paths

        Raises:
            EnvironmentError: If listing fails
        """
        try:
            environments = {}

            for path in self.base_path.iterdir():
                if not path.is_dir():
                    continue

                # Check for key virtual environment markers
                python_exe = path / "bin" / "python"
                if platform.system() == "Windows":
                    python_exe = path / "Scripts" / "python.exe"

                if python_exe.exists():
                    environments[path.name] = path

            return environments

        except Exception as e:
            raise EnvironmentError(
                "Failed to list environments",
                details=str(e),
            )

    def is_venv(self, path: Path) -> bool:
        """
        Check if path is a virtual environment.

        Args:
            path: Path to check

        Returns:
            True if path is a virtual environment
        """
        if not path.is_dir():
            return False

        # Check for key virtual environment markers
        python_exe = path / "bin" / "python"
        if platform.system() == "Windows":
            python_exe = path / "Scripts" / "python.exe"

        return python_exe.exists()

    def get_python_path(self, name: str) -> Optional[Path]:
        """
        Get Python executable path for environment.

        Args:
            name: Environment name

        Returns:
            Path to Python executable if found

        Raises:
            EnvironmentError: If environment not found
        """
        try:
            venv_path = self.base_path / name

            if not self.is_venv(venv_path):
                raise EnvironmentError(
                    f"Environment {name} not found",
                    details=f"Path: {venv_path}",
                )

            # Get Python executable path
            python_exe = venv_path / "bin" / "python"
            if platform.system() == "Windows":
                python_exe = venv_path / "Scripts" / "python.exe"

            if not python_exe.exists():
                raise EnvironmentError(
                    f"Python executable not found in {name}",
                    details=f"Path: {python_exe}",
                )

            return python_exe

        except Exception as e:
            if isinstance(e, EnvironmentError):
                raise
            raise EnvironmentError(
                f"Failed to get Python path for {name}",
                details=str(e),
            )

    def get_site_packages(self, name: str) -> Optional[Path]:
        """
        Get site-packages directory for environment.

        Args:
            name: Environment name

        Returns:
            Path to site-packages if found

        Raises:
            EnvironmentError: If environment not found
        """
        try:
            venv_path = self.base_path / name
            python_path = self.get_python_path(name)

            if not python_path:
                return None

            return get_venv_site_packages(venv_path)

        except Exception as e:
            raise EnvironmentError(
                f"Failed to get site-packages for {name}",
                details=str(e),
            )

    def run(self, name: str, command: List[str]) -> None:
        """
        Run command in virtual environment.

        Args:
            name: Environment name
            command: Command to run

        Raises:
            EnvironmentError: If command fails
        """
        try:
            python_path = self.get_python_path(name)
            if not python_path:
                raise EnvironmentError(
                    f"Environment {name} not found",
                    details="Cannot run command",
                )

            # Prepare environment variables
            env = os.environ.copy()
            env["VIRTUAL_ENV"] = str(python_path.parent.parent)
            env["PATH"] = f"{python_path.parent}{os.pathsep}{env['PATH']}"

            # Run command
            process = subprocess.Popen(
                command,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise EnvironmentError(
                    f"Command failed: {' '.join(command)}",
                    details=stderr.strip(),
                )

        except Exception as e:
            if isinstance(e, EnvironmentError):
                raise
            raise EnvironmentError(
                f"Failed to run command in {name}",
                details=str(e),
            )
