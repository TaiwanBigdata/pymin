# Package collection functionality
from pathlib import Path
from typing import Dict, List, Optional

from ..package import PackageManager
from ..requirements import RequirementsManager
from ..exceptions import PackageError


class PackageCollector:
    """Collects package information from various sources."""

    def __init__(self, venv_path: Optional[Path] = None):
        """
        Initialize package collector.

        Args:
            venv_path: Optional virtual environment path
        """
        self.venv_path = venv_path
        self._pkg_manager = PackageManager(venv_path)
        self._req_manager = RequirementsManager()

    def get_installed_packages(self) -> Dict[str, str]:
        """
        Get installed packages.

        Returns:
            Dictionary mapping package names to versions
        """
        return self._pkg_manager.list_installed()

    def get_requirements_packages(self) -> Dict[str, str]:
        """
        Get packages from requirements.txt.

        Returns:
            Dictionary mapping package names to version constraints
        """
        return self._req_manager.parse()

    def get_main_packages(self) -> Dict[str, str]:
        """
        Get top-level installed packages (not dependencies).

        Returns:
            Dictionary mapping package names to versions
        """
        installed = self.get_installed_packages()
        all_deps = set()

        # Collect all dependencies
        for pkg in installed:
            try:
                deps = self._pkg_manager.get_dependencies(pkg)
                all_deps.update(deps)
            except PackageError:
                continue

        # Filter out dependencies
        return {
            name: version
            for name, version in installed.items()
            if name not in all_deps
        }
