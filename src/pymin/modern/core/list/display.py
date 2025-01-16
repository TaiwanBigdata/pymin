# Package display functionality
from pathlib import Path
from typing import Dict, List, Optional

from ...ui import console
from .collector import PackageCollector
from .formatter import PackageFormatter


class ListDisplay:
    """Displays package information in various formats."""

    def __init__(self, venv_path: Optional[Path] = None):
        """
        Initialize list display.

        Args:
            venv_path: Optional virtual environment path
        """
        self.venv_path = venv_path
        self._collector = PackageCollector(venv_path)
        self._formatter = PackageFormatter(venv_path)

    def create_table(
        self,
        title: str,
        columns: List[str],
        show_header: bool = True,
    ):
        """
        Create display table.

        Args:
            title: Table title
            columns: Column names
            show_header: Whether to show column headers

        Returns:
            Table object
        """
        table = console.create_table(title, show_header=show_header)
        for col in columns:
            table.add_column(col)
        return table

    def show_packages(
        self,
        packages: Dict[str, str],
        title: str = "Installed Packages",
        show_versions: bool = True,
    ) -> None:
        """
        Show package list.

        Args:
            packages: Dictionary mapping package names to versions
            title: Table title
            show_versions: Whether to show version information
        """
        if not packages:
            console.info("No packages found")
            return

        # Format packages
        formatted = self._formatter.format_package_list(
            packages,
            show_versions=show_versions,
        )

        # Create and populate table
        columns = ["Package"]
        if show_versions:
            columns.append("Version")

        table = self.create_table(title, columns)
        for pkg in formatted:
            row = [pkg["name"]]
            if show_versions:
                row.append(pkg["version"])
            table.add_row(*row)

        console.print(table)

    def show_tree(
        self,
        package: str,
        max_depth: Optional[int] = None,
        show_versions: bool = True,
    ) -> None:
        """
        Show dependency tree.

        Args:
            package: Package name
            max_depth: Maximum depth to show
            show_versions: Whether to show version constraints
        """
        # Format tree
        tree = self._formatter.format_dependency_tree(
            package,
            max_depth=max_depth,
            show_versions=show_versions,
        )

        # Create title
        title = f"Dependency Tree for {package}"
        if max_depth is not None:
            title += f" (max depth: {max_depth})"

        # Display tree
        panel = console.create_panel(tree, title=title)
        console.print(panel)
