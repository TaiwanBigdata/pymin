# Package formatting functionality
from typing import Dict, List, Optional

from ..dependency import DependencyAnalyzer


class PackageFormatter:
    """Formats package information for display."""

    def __init__(self, venv_path: Optional[str] = None):
        """
        Initialize package formatter.

        Args:
            venv_path: Optional virtual environment path
        """
        self._dep_analyzer = DependencyAnalyzer(venv_path)

    def format_package_list(
        self,
        packages: Dict[str, str],
        show_versions: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Format package list for display.

        Args:
            packages: Dictionary mapping package names to versions
            show_versions: Whether to include version information

        Returns:
            List of dictionaries with package information
        """
        formatted = []
        for name, version in sorted(packages.items()):
            pkg_info = {"name": name}
            if show_versions:
                pkg_info["version"] = version or "-"
            formatted.append(pkg_info)
        return formatted

    def format_dependency_tree(
        self,
        package: str,
        max_depth: Optional[int] = None,
        show_versions: bool = True,
    ) -> str:
        """
        Format package dependency tree.

        Args:
            package: Package name
            max_depth: Maximum depth to show
            show_versions: Whether to show version constraints

        Returns:
            Formatted tree string
        """
        tree = self._dep_analyzer.build_dependency_tree(
            package,
            max_depth=max_depth,
            include_versions=show_versions,
        )
        return self._dep_analyzer.format_tree(tree)
