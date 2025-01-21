import os
import pathlib
import sys
import platform
import importlib.metadata
from enum import Enum
from typing import Optional, Dict, Any, Tuple


class VenvNotFoundError(Exception):
    """Custom exception for when virtual environment is not found"""

    pass


class VenvAnalyzer:
    """
    Analyzer for Python virtual environment metadata and information
    """

    # Common virtual environment directory names
    VENV_DIRS = ["venv", ".venv", "env", ".env"]

    def __init__(self, project_path: Optional[str] = None):
        """
        Initialize VenvAnalyzer with project path

        Args:
            project_path: Path to the project directory. If None, uses current directory
        """
        self.project_path = pathlib.Path(
            project_path or pathlib.Path.cwd()
        ).resolve()
        self.has_venv = self.check_venv_exists()

        if self.has_venv:
            self.venv_path = self._find_venv_path()
            self.site_packages = self._get_site_packages_path()
            if str(self.site_packages) not in sys.path:
                sys.path.insert(0, str(self.site_packages))
        else:
            self.venv_path = None
            self.site_packages = None

    def _find_venv_path(self) -> pathlib.Path:
        """
        Find virtual environment directory in project path

        Returns:
            Path to virtual environment directory

        Raises:
            VenvNotFoundError: If no valid virtual environment is found
        """
        for venv_name in self.VENV_DIRS:
            venv_path = self.project_path / venv_name
            if self._is_valid_venv(venv_path):
                return venv_path

        raise VenvNotFoundError(
            f"No valid virtual environment found in {self.project_path}. "
            "Expected one of these directories: " + ", ".join(self.VENV_DIRS)
        )

    def _is_valid_venv(self, path: pathlib.Path) -> bool:
        """
        Check if path contains a valid virtual environment

        Args:
            path: Path to check
        """
        if not path.exists():
            return False

        # Check for critical virtual environment components
        if sys.platform == "win32":
            required_paths = [
                path / "Scripts" / "python.exe",
                path / "Lib" / "site-packages",
            ]
        else:
            # Find python3.x directory
            lib_path = path / "lib"
            if not lib_path.exists():
                return False

            python_dirs = list(lib_path.glob("python3.*"))
            if not python_dirs:
                return False

            required_paths = [
                path / "bin" / "python",
                python_dirs[0] / "site-packages",
            ]

        return all(p.exists() for p in required_paths)

    def _get_site_packages_path(self) -> pathlib.Path:
        """
        Get site-packages path from virtual environment

        Returns:
            Path to the site-packages directory

        Raises:
            ValueError: If site-packages directory cannot be found
        """
        if sys.platform == "win32":
            python_path = "Lib/site-packages"
        else:
            lib_path = self.venv_path / "lib"
            if not lib_path.exists():
                raise ValueError(
                    f"Cannot find lib directory in {self.venv_path}"
                )

            # Find any python3.* directory
            python_dirs = []
            for version in range(0, 20):  # Support up to Python 3.19
                check_dir = lib_path / f"python3.{version}"
                if check_dir.exists():
                    python_dirs.append(check_dir)

            if not python_dirs:
                raise ValueError(
                    f"Cannot find python3.* directory in {lib_path}"
                )

            # Use the highest version available
            highest_version_dir = sorted(python_dirs)[-1]
            python_path = (
                highest_version_dir.relative_to(self.venv_path)
                / "site-packages"
            )

        site_packages = self.venv_path / python_path
        if not site_packages.exists():
            raise ValueError(f"Cannot find site-packages in {self.venv_path}")

        return site_packages

    def _get_python_version(self) -> str:
        """
        Get Python version number without prefix

        Returns:
            String of version number (e.g., "3.13")
        """
        if sys.platform == "win32":
            python_path = self.venv_path / "Scripts" / "python.exe"
        else:
            python_path = self.venv_path / "bin" / "python"

        if python_path.exists():
            if sys.platform == "win32":
                lib_path = self.venv_path / "Lib"
            else:
                lib_path = self.venv_path / "lib"

            if lib_path.exists():
                python_dirs = list(lib_path.glob("python3.*"))
                if python_dirs:
                    version_dir = python_dirs[0].name
                    return version_dir.replace("python", "")

            return f"{sys.version_info.major}.{sys.version_info.minor}"
        return "unknown"

    def _get_pip_info(self) -> Tuple[str, str]:
        """
        Get pip version and location

        Returns:
            Tuple of (version, path)
        """
        try:
            if sys.platform == "win32":
                pip_path = self.venv_path / "Scripts" / "pip.exe"
            else:
                pip_path = self.venv_path / "bin" / "pip"

            if not pip_path.exists():
                return "unknown", str(pip_path)

            # Use importlib.metadata to get pip version
            try:
                pip_version = importlib.metadata.version("pip")
            except importlib.metadata.PackageNotFoundError:
                pip_version = "unknown"

            return pip_version, str(pip_path)
        except Exception as e:
            return "unknown", "not found"

    def _get_platform_info(self) -> Dict[str, str]:
        """
        Get detailed platform information

        Returns:
            Dictionary containing platform details:
            - system: Kernel name (Darwin/Windows/Linux)
            - os: Operating system name (macOS/Windows/Linux)
            - os_version: Operating system version
            - release: Kernel release version
            - machine: Machine architecture
            - processor: Processor type
        """
        system = platform.system()

        # Initialize OS related information
        os_name = system
        os_version = ""

        # Get version information for different operating systems
        if system == "Darwin":
            os_name = "macOS"
            try:
                os_version = platform.mac_ver()[0]
            except:
                os_version = "unknown"
        elif system == "Windows":
            os_name = "Windows"
            try:
                os_version = platform.win32_ver()[0]
            except:
                os_version = "unknown"
        elif system == "Linux":
            os_name = "Linux"
            try:
                # Try to read distro information
                os_version = platform.freedesktop_os_release().get(
                    "VERSION_ID", ""
                )
            except:
                try:
                    os_version = platform.linux_distribution()[1]
                except:
                    os_version = "unknown"

        return {
            "system": system,
            "os": os_name,
            "os_version": os_version,
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor() or "unknown",
        }

    def _get_system_python_info(self) -> Dict[str, str]:
        """
        Get system Python information using environment variables and sys module

        Returns:
            Dictionary containing system Python information including:
            - executable: Path to the system Python executable
            - base_prefix: Base Python installation directory
        """
        # Check if using conda with CONDA_PYTHON_EXE environment variable
        conda_python = os.environ.get("CONDA_PYTHON_EXE")
        # Use PATH environment variable
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)

        system_python_path = None

        if conda_python and os.path.exists(conda_python):
            # If using conda environment
            system_python_path = conda_python
        else:
            # Check Python in PATH
            for path_dir in path_dirs:
                if "conda" in path_dir or "virtualenv" in path_dir:
                    continue

                python_exec = os.path.join(
                    path_dir,
                    "python.exe" if sys.platform == "win32" else "python",
                )
                if os.path.exists(python_exec):
                    system_python_path = python_exec
                    break

        return {
            "executable": system_python_path or sys.executable,
            "base_prefix": sys.base_prefix,
        }

    def _get_active_venv(self) -> Dict[str, Any]:
        """
        Get information about the currently active virtual environment
        """
        active_venv = os.environ.get("VIRTUAL_ENV")
        system_python = self._get_system_python_info()

        if active_venv:
            active_path = pathlib.Path(active_venv)
            if sys.platform == "win32":
                python_exec = active_path / "Scripts" / "python.exe"
            else:
                python_exec = active_path / "bin" / "python"

            return {
                "is_active": True,
                "name": f"{active_path.parent.name}({active_path.name})",
                "path": str(active_path),
                "python_executable": str(python_exec),
                "system_python": system_python,
            }
        else:
            return {
                "is_active": False,
                "name": None,
                "path": None,
                "python_executable": system_python["executable"],
                "system_python": system_python,
            }

    def _get_current_venv_status(self) -> Dict[str, Any]:
        """
        Get status of the virtual environment in current directory

        Returns:
            Dictionary containing current venv status
        """
        active_venv = os.environ.get("VIRTUAL_ENV", "")
        current_is_active = str(self.venv_path) == active_venv

        # Get Python executable for current directory venv
        if sys.platform == "win32":
            python_exec = self.venv_path / "Scripts" / "python.exe"
        else:
            python_exec = self.venv_path / "bin" / "python"

        return {
            "name": f"{self.project_path.name}({self.venv_path.name})",
            "path": str(self.venv_path),
            "is_active": current_is_active,
            "python_executable": str(python_exec),
        }

    def check_venv_exists(self, project_path: Optional[str] = None) -> bool:
        """
        Check if virtual environment exists in the specified path

        Args:
            project_path: Path to check for virtual environment. If None, uses instance path

        Returns:
            bool: True if valid virtual environment exists, False otherwise
        """
        check_path = pathlib.Path(project_path or self.project_path).resolve()

        for venv_name in self.VENV_DIRS:
            venv_path = check_path / venv_name
            if self._is_valid_venv(venv_path):
                return True
        return False

    def _create_environment_info(
        self, env_path: Optional[pathlib.Path] = None, is_current: bool = False
    ) -> Dict[str, Any]:
        """
        Create a standardized environment information dictionary

        Args:
            env_path: Path to the environment directory
            is_current: Whether this is the current directory's environment

        Returns:
            Dictionary containing environment information
        """
        if env_path:
            if sys.platform == "win32":
                python_exec = env_path / "Scripts" / "python.exe"
                site_packages = env_path / "Lib" / "site-packages"
            else:
                python_exec = env_path / "bin" / "python"
                # Find python3.x directory for site-packages
                lib_path = env_path / "lib"
                python_dirs = (
                    list(lib_path.glob("python3.*"))
                    if lib_path.exists()
                    else []
                )
                site_packages = (
                    python_dirs[0] / "site-packages" if python_dirs else None
                )

            project_name = (
                self.project_path.name if is_current else env_path.parent.name
            )
            env_name = env_path.name
            is_active = str(env_path) == os.environ.get("VIRTUAL_ENV", "")

            # Get Python version
            if sys.platform == "win32":
                version_dir = (env_path / "Lib").glob("python3.*")
            else:
                version_dir = (env_path / "lib").glob("python3.*")

            try:
                version = next(version_dir).name.replace("python", "")
            except (StopIteration, OSError):
                version = None

            return {
                "has_venv": True,
                "is_active": is_active,
                "name": f"{project_name}({env_name})",
                "path": str(env_path),
                "python_executable": str(python_exec),
                "version": version,
                "site_packages": str(site_packages) if site_packages else None,
            }
        else:
            project_name = self.project_path.name if is_current else None
            return {
                "has_venv": False,
                "is_active": False,
                "name": f"{project_name}(None)" if project_name else None,
                "path": None,
                "python_executable": None,
                "version": None,
                "site_packages": None,
            }

    def get_venv_info(self) -> Dict[str, Any]:
        """
        Get information about the system and virtual environment status
        """
        platform_info = self._get_platform_info()
        system_python = self._get_system_python_info()

        # Get active environment info
        active_venv = os.environ.get("VIRTUAL_ENV")
        active_env = self._create_environment_info(
            pathlib.Path(active_venv) if active_venv else None
        )

        # Get current environment info
        current_env = self._create_environment_info(
            self.venv_path if self.has_venv else None, is_current=True
        )

        # Check if active and current are the same
        is_same_env = (
            (active_env["path"] == current_env["path"])
            if active_env["path"] and current_env["path"]
            else False
        )

        return {
            "project": {
                "name": self.project_path.name,
                "path": str(self.project_path),
            },
            "system_python": {
                "executable": system_python["executable"],
                "base_prefix": system_python["base_prefix"],
            },
            "environment_status": {
                "active_environment": active_env,
                "current_environment": current_env,
                "is_same_environment": is_same_env,
            },
            "platform": platform_info,
            "pip": self._get_pip_info() if self.has_venv else None,
        }
