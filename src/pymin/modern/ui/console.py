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
    rows: List[List[Dict]],
    styles: Optional[List[str]] = None,
) -> Table:
    """Create package table with consistent styling"""
    table = Table(
        title=title,
        show_header=True,
        header_style="bold magenta",
        title_justify="left",
        expand=False,
    )

    # Add columns with specific styles and alignment
    table.add_column("Package Name", style="cyan", no_wrap=True)
    table.add_column("Required", style="blue")
    table.add_column("Installed", style="cyan")
    table.add_column("Status", justify="center")

    # Add rows
    for row in rows:
        if not row:  # Skip empty rows
            continue

        package_data = row[0]  # Get the package data from the row
        styled_row = []

        # Handle package name
        name = package_data.get("name", "")
        if package_data.get("redundant"):
            name_text = Text()
            name_text.append(name)
            name_text.append(" ", style="yellow")
            name_text.append("(redundant)", style="yellow")
        else:
            name_text = Text(name, style="cyan")
        styled_row.append(name_text)

        # Handle required version
        required_version = package_data.get("required_version", "")
        if required_version:
            required_text = Text(required_version.lstrip("="), style="blue")
        else:
            required_text = Text("None", style="yellow")
        styled_row.append(required_text)

        # Handle installed version
        installed_version = package_data.get("installed_version", "")
        if installed_version:
            installed_text = Text(installed_version, style="cyan")
        else:
            installed_text = Text("None", style="yellow")
        styled_row.append(installed_text)

        # Handle status
        status = package_data.get("status", "")
        status_text = Text(get_status_symbol(status), style=get_style(status))
        styled_row.append(status_text)

        # Add the row to the table
        table.add_row(*styled_row)

    return table


def create_dependency_tree(packages: Dict[str, Dict]) -> Table:
    """Create dependency tree table with consistent styling"""
    table = Table(
        title="Package Dependencies",
        show_header=True,
        header_style="bold magenta",
        title_justify="left",
        expand=False,
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
            for i in range(level - 1):
                is_parent_last_at_level = (
                    i < len(parent_is_last) and parent_is_last[i]
                )
                prefix += "    " if is_parent_last_at_level else "│   "
            prefix += "└── " if is_last else "├── "

        # Get package information
        installed_version = data.get("installed_version", "")
        required_version = data.get("required_version", "")
        display_name = data.get("name", name)  # Use name from data if available

        # Format version displays for top-level packages
        if level == 0:
            required_version = (
                required_version.lstrip("=")
                if required_version
                else "[yellow]None[/yellow]"
            )
            installed_version = (
                installed_version
                if installed_version
                else "[yellow]None[/yellow]"
            )

        # Get status and format package name
        status = data.get("status", "")
        status_style = get_style(status)
        status_symbol = Text(get_status_symbol(status), style=status_style)

        # Create display name with styled redundant suffix
        if level == 0 and status == "redundant":
            display_text = Text()
            display_text.append(display_name)
            display_text.append(" ", style="yellow")
            display_text.append("(redundant)", style="yellow")
            display_name = Text.assemble(prefix, display_text)
        else:
            display_name = f"{prefix}{display_name}"

        return [
            display_name,
            required_version if level == 0 else "",
            installed_version,
            status_symbol,
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
            # Top level packages don't need a row style
            table.add_row(*row)

        # Add dependencies
        if "dependencies" in data:
            deps = list(data["dependencies"].items())
            for i, (dep_name, dep_data) in enumerate(deps):
                is_last_dep = i == len(deps) - 1
                current_parent_is_last = parent_is_last.copy()
                if level > 0:
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
