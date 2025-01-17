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

    def show_tree(self) -> None:
        """Show packages in tree format."""
        # Get top-level packages
        packages = self._collector.get_main_packages()

        if not packages:
            console.info("No packages found")
            return

        console.print("\n[bold cyan]Package Dependency Tree[/]\n")

        for name, version in packages.items():
            try:
                # Get package tree using PackageManager's method
                tree = self._collector._pkg_manager.get_package_tree(name)

                # Print package name with version
                console.print(f" {name} ({version})")

                # Print dependencies
                if tree[name]:  # If has dependencies
                    for i, dep in enumerate(tree[name]):
                        is_last = i == len(tree[name]) - 1
                        prefix = " └── " if is_last else " ├── "
                        console.print(f"{prefix}{dep}")

                        # Print sub-dependencies
                        if dep in tree:
                            sub_prefix = "     " if is_last else " │   "
                            for j, sub_dep in enumerate(tree[dep]):
                                is_last_sub = j == len(tree[dep]) - 1
                                sub_marker = "└── " if is_last_sub else "├── "
                                console.print(
                                    f"{sub_prefix}{sub_marker}{sub_dep}"
                                )
                else:
                    console.print(" └── (no dependencies)")

                console.print("")  # Add blank line between packages

            except Exception as e:
                console.warning(f"Failed to get dependencies for {name}")
                console.print(f" └── {name} (error)")
                console.print("")
