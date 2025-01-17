# Package collection functionality
from pathlib import Path
from typing import Dict, List, Optional
import sys

from ..package import PackageManager
from ..requirements import RequirementsManager
from ..exceptions import PackageError
from rich import console


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

    def debug_info(self) -> None:
        """Print debug information about packages."""
        console.print("\n[bold cyan]===== Package Information Debug =====[/]")

        # 1. 所有已安裝的套件
        installed = self._pkg_manager.list_installed(top_level_only=False)
        console.print("\n[bold]1. All Installed Packages:[/]")
        for name, version in installed.items():
            console.print(f"  {name}: {version}")

        # 2. Requirements.txt 中的套件
        required = self._req_manager.parse()
        console.print("\n[bold]2. Requirements.txt:[/]")
        for name, version in required.items():
            console.print(f"  {name}: {version or '(no version specified)'}")

        # 3. 頂層套件（不是其他套件的依賴）
        top_level = self._pkg_manager.list_installed(top_level_only=True)
        console.print("\n[bold]3. Top-level Packages:[/]")
        for name, version in top_level.items():
            console.print(f"  {name}: {version}")

        # 4. 每個套件的依賴關係
        console.print("\n[bold]4. Package Dependencies:[/]")
        for name in installed:
            deps = self._pkg_manager._get_package_dependencies(name)
            console.print(f"\n  [cyan]{name}[/]:")
            if deps:
                for dep in deps:
                    console.print(f"    ├── {dep}")
            else:
                console.print("    └── (no dependencies)")

        # 5. 系統資訊
        console.print("\n[bold]5. System Information:[/]")
        console.print(f"  Virtual Environment: {self.venv_path or '(none)'}")
        console.print(f"  Python Path: {sys.executable}")
        console.print(
            f"  Site Packages: {[p for p in sys.path if 'site-packages' in p]}"
        )

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

    def get_packages(self) -> Dict[str, Dict[str, str]]:
        """
        Get unified package information.

        Returns:
            Dictionary mapping package names to their information:
            {
                "name": {
                    "installed": "version",
                    "required": "version_constraint",
                    "dependencies": ["dep1", "dep2"]
                }
            }
        """
        # Get all package information
        installed = self._pkg_manager.list_installed(top_level_only=False)
        required = self._req_manager.parse()

        # Build unified package info
        packages = {}
        for name in set(installed) | set(required):
            packages[name] = {
                "installed": installed.get(name),
                "required": required.get(name),
                "dependencies": list(
                    self._pkg_manager._get_package_dependencies(name)
                ),
            }

        return packages

    def get_main_packages(self) -> Dict[str, str]:
        """
        Get top-level installed packages (not dependencies).

        Returns:
            Dictionary mapping package names to versions
        """
        # Get all packages
        installed = self._pkg_manager.list_installed(top_level_only=True)

        # Return top-level packages
        return installed
