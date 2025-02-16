"""Console output handling with consistent styling"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.status import Status
from rich.box import DOUBLE
from typing import Dict, List, Optional, Union, Literal
from contextlib import contextmanager

from pymin.core.package_analyzer import PackageStatus
from ..ui.style import (
    StyleType,
    SymbolType,
    get_status_symbol,
    DEFAULT_PANEL,
    DEFAULT_TABLE,
    Style,
    format_status_message,
)

console = Console(force_terminal=True, color_system="auto")
_current_status: Optional[Status] = None


@contextmanager
def progress_status(message: str):
    """Display a progress status message with consistent styling.

    Args:
        message: The message to display

    Example:
        with progress_status("Getting environment information..."):
            # Do some work here
            result = some_long_running_operation()
    """
    with Status(
        f"[{StyleType.LOADING}]{message}[/{StyleType.LOADING}]",
        console=console,
        spinner="dots",
        spinner_style=f"{StyleType.LOADING}",
    ) as status:
        try:
            yield status
        finally:
            pass  # Status will be automatically cleared


def start_status(message: str) -> None:
    """Start displaying a status message"""
    global _current_status
    if _current_status is not None:
        _current_status.stop()

    _current_status = Status(
        f"[blue]{message}[/blue]",
        console=console,
        spinner="dots",
    )
    _current_status.start()


def stop_status() -> None:
    """Stop displaying the current status message"""
    global _current_status
    if _current_status is not None:
        _current_status.stop()
        _current_status = None


def print_error(message: str):
    """Display error message"""
    stop_status()  # Ensure any status message is cleared
    console.print(format_status_message(message, "error"))


def print_warning(message: str):
    """Display warning message"""
    stop_status()  # Ensure any status message is cleared
    console.print(format_status_message(message, "warning"))


def print_success(message: str):
    """Display success message"""
    stop_status()  # Ensure any status message is cleared
    console.print(format_status_message(message, "success"))


def print_info(message: str):
    """Display info message"""
    stop_status()  # Ensure any status message is cleared
    console.print(format_status_message(message, "info"))


def create_package_table(
    title: str,
    headers: List[str],
    rows: List[List[Dict]],
    styles: Optional[List[str]] = None,
) -> Table:
    """Create package table with consistent styling"""
    table = Table(
        title=title,
        show_header=DEFAULT_TABLE.show_header,
        header_style=DEFAULT_TABLE.header_style,
        title_justify=DEFAULT_TABLE.title_justify,
        expand=DEFAULT_TABLE.expand,
        padding=DEFAULT_TABLE.padding,
    )

    # Add columns with specific styles and alignment
    table.add_column("Package", style=StyleType.PACKAGE_NAME)
    table.add_column("Required", style=StyleType.PACKAGE_VERSION)
    table.add_column("Installed", style=StyleType.PACKAGE_VERSION)
    table.add_column("Status", justify="center")

    # Add rows with consistent styling
    for row in rows:
        if not row:  # Skip empty rows
            continue

        package_data = row[0]  # Get the package data from the row
        styled_row = []

        # Handle package name with consistent styling
        name = package_data.get("name", "")
        extras = package_data.get("extras")  # Get extras information

        # Create package name text
        name_text = Text()

        # Add package name with extras if available
        if extras:
            name_text.append(name, style=StyleType.PACKAGE_NAME)
            extras_str = f"[{','.join(sorted(extras))}]"
            name_text.append(extras_str, style=StyleType.PACKAGE_EXTRAS)
        else:
            name_text.append(name, style=StyleType.PACKAGE_NAME)

        # Add redundant marker if needed
        if package_data.get("status") == PackageStatus.REDUNDANT:
            name_text.append(" ", style=StyleType.WARNING)
            name_text.append("(redundant)", style=StyleType.WARNING)

        styled_row.append(name_text)

        # Handle required version
        required_version = package_data.get("required_version", "")
        if required_version:
            # Handle both string and Text objects
            if isinstance(required_version, Text):
                required_text = required_version
            else:
                required_text = Text(
                    required_version.lstrip("="), style=Style(color="blue")
                )
        elif not package_data.get("is_dependency"):
            required_text = Text("None", style=Style(color="yellow"))
        else:
            required_text = Text("")
        styled_row.append(required_text)

        # Handle installed version
        installed_version = package_data.get("installed_version", "")
        if installed_version:
            installed_text = Text(installed_version, style=Style(color="cyan"))
        else:
            installed_text = Text("None", style=Style(color="yellow"))
        styled_row.append(installed_text)

        # Handle status
        status = package_data.get("status", "")
        styled_row.append(get_status_symbol(status))

        # Add the row to the table with appropriate styling
        if package_data.get("is_dependency"):
            table.add_row(*styled_row, style=StyleType.PACKAGE_DEPENDENCY)
        else:
            table.add_row(*styled_row)

    return table


def create_dependency_tree(packages: Dict[str, Dict]) -> Table:
    """Create dependency tree table with consistent styling"""
    table = Table(
        title="Package Dependencies",
        show_header=DEFAULT_TABLE.show_header,
        header_style=DEFAULT_TABLE.header_style,
        title_justify=DEFAULT_TABLE.title_justify,
        expand=DEFAULT_TABLE.expand,
        padding=DEFAULT_TABLE.padding,
    )

    # Add columns with specific styles and alignment
    table.add_column("Package Tree", style=StyleType.PACKAGE_NAME)
    table.add_column("Required", style=StyleType.PACKAGE_VERSION)
    table.add_column("Installed", style=StyleType.PACKAGE_VERSION)
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
        extras = data.get("extras")  # 獲取 extras 資訊

        # Format version displays
        if required_version:
            if isinstance(required_version, Text):
                required_text = required_version
            else:
                required_text = Text(
                    required_version.lstrip("="), style=Style(color="blue")
                )
        elif level == 0 and not data.get("is_dependency"):
            required_text = Text("None", style=Style(color="yellow"))
        else:
            required_text = Text("")

        if installed_version:
            installed_text = Text(installed_version, style=Style(color="cyan"))
        else:
            installed_text = Text("None", style=Style(color="yellow"))

        # For non-top-level packages, add dim effect
        if level > 0:
            if required_version:
                required_text.style = Style(color="blue", dim=True)
            installed_text.style = Style(
                color="cyan" if installed_version else "yellow", dim=True
            )

        # Get status and format package name
        status = data.get("status", "")
        status_symbol = get_status_symbol(status)

        # Create display name with styled extras and redundant suffix
        display_text = Text()
        display_text.append(display_name)

        # Add extras if available
        if extras:
            extras_str = f"[{','.join(sorted(extras))}]"
            display_text.append(extras_str, style=StyleType.PACKAGE_EXTRAS)

        # Add redundant suffix if needed
        if level == 0 and status == "redundant":
            display_text.append(" ", style="yellow")
            display_text.append("(redundant)", style="yellow")

        # Add prefix to the display name
        display_name = Text.assemble(prefix, display_text)

        return [
            display_name,
            required_text,
            installed_text,
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


def create_summary_panel(title: str, content: Union[str, Text]) -> Panel:
    """Create summary panel with consistent styling"""
    return Panel.fit(
        content,
        title=title,
        title_align=DEFAULT_PANEL.title_align,
        border_style=DEFAULT_PANEL.border_style,
        padding=DEFAULT_PANEL.padding,
    )


def display_panel(title: str, content: Union[str, Text]) -> None:
    """Display a panel with consistent styling and spacing.

    This is the main abstraction for displaying panels in the application.
    It handles the panel creation, outer spacing, and display in a consistent way.

    Args:
        title: Panel title
        content: Panel content (can be a string or Text object)
    """
    console.print()  # Single line before panel
    console.print(create_summary_panel(title, content))
    console.print()  # Single line after panel


def create_package_summary(
    packages: Union[List[Dict], Dict[str, Dict]],
    mode: Literal[
        "top_level", "all_installed", "dependency_tree"
    ] = "top_level",
) -> Text:
    """Create package summary with consistent styling

    Args:
        packages: Package data in either list or dictionary format
        mode: Display mode
            - top_level: Show only top-level packages (default)
            - all_installed: Show all installed packages
            - dependency_tree: Show package dependency tree
    """
    # Define status display names and styles
    status_names = {
        "normal": "Normal",
        "outdated": "Outdated",
        "missing": "Missing",
        "redundant": "Redundant",
        "version_mismatch": "Version Mismatch",
        "not_in_requirements": "Not in Requirements",
        "duplicate": "Duplicate",
    }

    status_styles = {
        "normal": "green",
        "outdated": "red",
        "missing": "red",
        "redundant": "yellow",
        "version_mismatch": "red",
        "not_in_requirements": "yellow",
        "duplicate": "yellow",
    }

    content = Text()

    # Count all possible package statuses
    status_counts = {
        "normal": 0,  # ✓ 正常
        "outdated": 0,  # ≠ 版本過期
        "missing": 0,  # ✗ 在 requirements.txt 但未安裝
        "redundant": 0,  # ⚠ 在 requirements.txt 且是依賴
        "version_mismatch": 0,  # ≠ 版本不符
        "not_in_requirements": 0,  # ! 已安裝但不在 requirements.txt
        "duplicate": 0,
    }

    # Convert list format to dictionary if needed
    if isinstance(packages, list):
        pkg_dict = {}
        for pkg in packages:
            pkg_name = pkg.get("name", "")
            if pkg_name:
                pkg_dict[pkg_name] = pkg
        packages = pkg_dict

    # Count packages by type
    top_level_packages = []
    dependency_packages = set()
    direct_dependencies = set()

    for pkg_name, pkg_data in packages.items():
        is_dependency = pkg_data.get("is_dependency", False)
        is_redundant = pkg_data.get("status") == "redundant"
        is_duplicate = pkg_data.get("status") == "duplicate"

        if not is_dependency:
            top_level_packages.append(pkg_data)
            status = pkg_data.get("status", "")
            # Handle missing packages (required but not installed)
            if pkg_data.get("required_version") and not pkg_data.get(
                "installed_version"
            ):
                status = "missing"
            # Handle duplicate packages
            elif is_duplicate:
                status = "duplicate"
            # Handle other statuses
            if status in status_counts:
                status_counts[status] += 1
            elif pkg_data.get("installed_version") and not pkg_data.get(
                "required_version"
            ):
                status_counts["not_in_requirements"] += 1

        # Collect dependencies only if we're showing the tree
        if mode == "dependency_tree" and "dependencies" in pkg_data:
            for dep_name, dep_data in pkg_data["dependencies"].items():
                direct_dependencies.add(dep_name)
                dependency_packages.add(dep_name)

                # Add nested dependencies
                def collect_deps(deps_dict):
                    if not deps_dict:
                        return
                    for name, data in deps_dict.items():
                        dependency_packages.add(name)
                        if "dependencies" in data:
                            collect_deps(data["dependencies"])

                if "dependencies" in dep_data:
                    collect_deps(dep_data["dependencies"])

    # Calculate total packages
    if mode == "dependency_tree":
        non_redundant_top_level = [
            pkg
            for pkg in top_level_packages
            if pkg.get("status") != "redundant"
        ]
        total_packages = len(non_redundant_top_level) + len(dependency_packages)
    elif mode == "all_installed":
        # For all_installed mode, include all packages
        total_packages = len(packages)
    else:
        # For top_level mode, include all top-level packages
        total_packages = len(top_level_packages)

    # Show different title based on mode
    if mode == "all_installed":
        content.append("Total Installed Packages: ")
    else:
        content.append("Total Packages: ")
    content.append(str(total_packages), style="cyan")
    content.append("\n\n")

    # Display top-level package statistics
    content.append("Top-level Packages:\n")

    # Show total count only for all_installed and dependency_tree modes
    if mode != "top_level":
        content.append("• Total: ")
        content.append(str(len(top_level_packages)), style="cyan")
        content.append("\n")

    # Only show non-zero status counts in a consistent order
    status_order = [
        "normal",
        "missing",
        "redundant",
        "version_mismatch",
        "not_in_requirements",
        "duplicate",
    ]
    for status in status_order:
        if status_counts[status] > 0:
            content.append(f"• {status_names[status]}: ")
            content.append(
                str(status_counts[status]), style=status_styles[status]
            )
            content.append("\n")

    # Display dependency statistics only for tree view
    if mode == "dependency_tree":
        content.append("\nDependencies:\n")
        content.append("• Total: ")
        content.append(str(len(dependency_packages)), style="cyan")
        content.append("\n")
        content.append("• Direct: ")
        content.append(str(len(direct_dependencies)), style="cyan")

    # Remove trailing newline
    if content.plain.endswith("\n"):
        content.remove_suffix("\n")

    return content


def print_tips(
    tips: Union[str, List[str]], *, dim: bool = True, indent: int = 2
) -> None:
    """Print tips with consistent styling.

    Args:
        tips: A single tip string or a list of tip strings
        dim: Whether to dim the output
        indent: Number of spaces to indent for bullet points (only used for multiple tips)
    """
    if not tips:
        return

    style = "[dim]" if dim else ""
    end_style = "[/dim]" if dim else ""

    if isinstance(tips, str):
        # Single tip
        console.print(f"{style}Tip: {tips}{end_style}")
    else:
        # Multiple tips
        if len(tips) == 1:
            # If only one tip in list, display as single tip
            console.print(f"{style}Tip: {tips[0]}{end_style}")
        else:
            # Multiple tips with bullet points
            console.print(f"{style}Tips:{end_style}")
            for tip in tips:
                console.print(f"{style}{' ' * indent}• {tip}{end_style}")


def print_table(table: Table) -> None:
    """Print table with consistent padding"""
    console.print("\n")
    console.print(table)
    console.print("\n")
