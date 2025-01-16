# Package management functionality
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

from .exceptions import PackageError
from .utils import normalize_package_name, get_canonical_name, format_version
from .pip import PipWrapper
from ..ui import console


class PackageManager:
    """Manages Python package operations."""

    def __init__(self, venv_path: Optional[Path] = None):
        """
        Initialize package manager.

        Args:
            venv_path: Optional virtual environment path
        """
        self.venv_path = venv_path
        python_path = str(venv_path / "bin" / "python") if venv_path else None
        self._pip = PipWrapper(python_path)

    def install(
        self,
        package: str,
        version: Optional[str] = None,
        upgrade: bool = False,
    ) -> None:
        """
        Install a package.

        Args:
            package: Package name
            version: Optional version constraint
            upgrade: Whether to upgrade existing package

        Raises:
            PackageError: If installation fails
        """
        try:
            pkg_spec = f"{package}=={version}" if version else package
            console.start_status(f"Installing {pkg_spec}...")
            self._pip.install(package, version=version, upgrade=upgrade)
            console.success(f"Successfully installed {pkg_spec}")
        except Exception as e:
            raise PackageError(
                f"Failed to install {package}",
                details=str(e),
            )
        finally:
            console.stop_status()

    def uninstall(self, package: str) -> None:
        """
        Uninstall a package.

        Args:
            package: Package name

        Raises:
            PackageError: If uninstallation fails
        """
        try:
            console.start_status(f"Uninstalling {package}...")
            self._pip.uninstall(package)
            console.success(f"Successfully uninstalled {package}")
        except Exception as e:
            raise PackageError(
                f"Failed to uninstall {package}",
                details=str(e),
            )
        finally:
            console.stop_status()

    def upgrade(self, package: str) -> None:
        """
        Upgrade a package to latest version.

        Args:
            package: Package name

        Raises:
            PackageError: If upgrade fails
        """
        self.install(package, upgrade=True)

    def list_installed(self) -> Dict[str, str]:
        """
        Get dictionary of installed packages and versions.

        Returns:
            Dictionary mapping package names to versions

        Raises:
            PackageError: If listing packages fails
        """
        try:
            packages = {}
            for pkg in self._pip.list_packages():
                name = pkg["name"]
                version = pkg["version"]
                packages[normalize_package_name(name)] = version
            return packages
        except Exception as e:
            raise PackageError(
                "Failed to list installed packages",
                details=str(e),
            )

    def get_package_info(self, package: str) -> Dict:
        """
        Get package information from PyPI.

        Args:
            package: Package name

        Returns:
            Dictionary containing package information

        Raises:
            PackageError: If getting package info fails
        """
        try:
            return self._pip.show(package)
        except Exception as e:
            raise PackageError(
                f"Failed to get info for {package}",
                details=str(e),
            )

    def check_updates(self) -> Dict[str, Tuple[str, str]]:
        """
        Check for available package updates.

        Returns:
            Dictionary mapping package names to tuples of (current_version, latest_version)

        Raises:
            PackageError: If checking updates fails
        """
        try:
            updates = {}
            for pkg in self._pip.list_packages(outdated=True):
                name = pkg["name"]
                current = pkg["version"]
                latest = pkg["latest_version"]
                updates[normalize_package_name(name)] = (current, latest)
            return updates
        except Exception as e:
            raise PackageError(
                "Failed to check for updates",
                details=str(e),
            )

    def get_dependencies(self, package: str) -> List[str]:
        """
        Get list of package dependencies.

        Args:
            package: Package name

        Returns:
            List of dependency package names

        Raises:
            PackageError: If getting dependencies fails
        """
        try:
            info = self.get_package_info(package)
            requires = info.get("requires", "")

            if not requires:
                return []

            return [dep.split(";")[0].strip() for dep in requires.split(",")]
        except Exception as e:
            raise PackageError(
                f"Failed to get dependencies for {package}",
                details=str(e),
            )
