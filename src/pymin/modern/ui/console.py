"""Console output handling with consistent styling"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.box import DOUBLE
from typing import Dict, List, Optional, Union
from ..ui.style import STYLES, SYMBOLS, get_status_symbol, get_style

console = Console(force_terminal=True, color_system="auto")


def print_error(message: str):
    """Display error message"""
    console.print(f"{SYMBOLS['error']} {message}", style=STYLES["error"])


def print_warning(message: str):
    """Display warning message"""
    console.print(f"{SYMBOLS['warning']} {message}", style=STYLES["warning"])


def print_success(message: str):
    """Display success message"""
    console.print(f"{SYMBOLS['success']} {message}", style=STYLES["success"])


def print_info(message: str):
    """Display info message"""
    console.print(f"{SYMBOLS['info']} {message}", style=STYLES["info"])


def create_package_table(
    title: str,
    headers: List[str],
    rows: List[List[str]],
    styles: Optional[List[str]] = None,
) -> Table:
    """Create package table with consistent styling"""
    table = Table(
        title=title,
        show_header=True,
        header_style="bold magenta",
        title_justify="left",
        expand=True,
        border_style="bright_blue",
        box=None,
    )

    # Add columns
    for header in headers:
        table.add_column(header)

    # Add rows
    for row in rows:
        if styles:
            styled_row = [
                Text(cell, style=get_style(style))
                for cell, style in zip(row, styles)
            ]
            table.add_row(*styled_row)
        else:
            table.add_row(*row)

    return table


def create_dependency_tree(packages: Dict[str, Dict]) -> Table:
    """Create dependency tree table with consistent styling"""
    table = Table(
        title="Package Dependencies",
        show_header=True,
        header_style="bold magenta",
        title_justify="left",
        expand=False,
        border_style="bright_blue",
    )

    # Add columns with specific styles and alignment
    table.add_column("Package Tree", style="cyan", no_wrap=True)
    table.add_column("Required", style="blue")
    table.add_column("Installed", style="cyan")
    table.add_column("Status", justify="center")

    def format_tree_line(
        name: str,
        data: Dict,
        level: int = 0,
        is_last: bool = False,
        parent_is_last: List[bool] = None,
    ) -> List[str]:
        """Format a single line of the dependency tree"""
        if parent_is_last is None:
            parent_is_last = []

        # Build the prefix based on level and parent status
        if level == 0:
            prefix = ""
        else:
            prefix = ""
            # Add prefix for each level based on parent status
            for i in range(level - 1):
                # Check parent's status at current level
                is_parent_last_at_level = (
                    i < len(parent_is_last) and parent_is_last[i]
                )
                # If parent was last at this level, add spaces, otherwise add vertical line
                prefix += "    " if is_parent_last_at_level else "│   "

            # Add the final connector
            prefix += "└── " if is_last else "├── "

        # Get package information
        installed_version = data.get("version", "")
        required_version = data.get("required_version", "None")
        status = "△" if level == 0 else ""

        return [
            f"{prefix}{name}",
            required_version if level == 0 else "",
            installed_version,
            status,
        ]

    def add_package_to_table(
        name: str,
        data: Dict,
        level: int = 0,
        is_last: bool = False,
        parent_is_last: List[bool] = None,
    ):
        """Recursively add package and its dependencies to the table"""
        if parent_is_last is None:
            parent_is_last = []

        # Add current package
        row = format_tree_line(name, data, level, is_last, parent_is_last)
        if level > 0:
            table.add_row(*row, style="dim")
        else:
            table.add_row(*row)

        # Add dependencies
        if "dependencies" in data:
            deps = list(data["dependencies"].items())
            for i, (dep_name, dep_data) in enumerate(deps):
                is_last_dep = i == len(deps) - 1
                # For nested dependencies, we need to track the parent's status
                current_parent_is_last = parent_is_last.copy()
                if level > 0:
                    # Only add current level's status for nested dependencies
                    current_parent_is_last.append(is_last)

                add_package_to_table(
                    dep_name,
                    dep_data,
                    level + 1,
                    is_last_dep,
                    current_parent_is_last,
                )

        # Add empty line between top-level packages
        if level == 0 and not is_last:
            table.add_row("", "", "", "")

    # Add all packages to table
    packages_list = list(packages.items())
    for i, (name, data) in enumerate(packages_list):
        add_package_to_table(name, data, is_last=(i == len(packages_list) - 1))

    return table


def create_status_panel(
    title: str, content: Union[str, Text], style: str = "info"
) -> Panel:
    """Create status panel with consistent styling"""
    return Panel.fit(
        content,
        title=title,
        title_align="left",
        border_style=STYLES[style].color,
        padding=(1, 2),
    )
