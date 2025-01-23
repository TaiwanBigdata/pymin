"""Console output handling with consistent styling"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.box import DOUBLE
from typing import Dict, List, Optional, Union, Literal
from ..ui.style import (
    StyleType,
    SymbolType,
    get_status_symbol,
    get_style,
    DEFAULT_PANEL,
    DEFAULT_TABLE,
    Style,
)

console = Console(force_terminal=True, color_system="auto")


def print_error(message: str):
    """Display error message"""
    console.print(f"{SymbolType.ERROR} {message}", style=StyleType.ERROR())


def print_warning(message: str):
    """Display warning message"""
    console.print(f"{SymbolType.WARNING} {message}", style=StyleType.WARNING())


def print_success(message: str):
    """Display success message"""
    console.print(f"{SymbolType.SUCCESS} {message}", style=StyleType.SUCCESS())


def print_info(message: str):
    """Display info message"""
    console.print(f"{SymbolType.INFO} {message}", style=StyleType.INFO())


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
    table.add_column("Package", style=StyleType.PACKAGE_NAME())
    table.add_column("Required", style=StyleType.PACKAGE_VERSION())
    table.add_column("Installed", style=StyleType.PACKAGE_VERSION())
    table.add_column("Status", justify="center")

    # Add rows with consistent styling
    for row in rows:
        if not row:  # Skip empty rows
            continue

        package_data = row[0]  # Get the package data from the row
        styled_row = []

        # Handle package name with consistent styling
        name = package_data.get("name", "")
        if package_data.get("redundant"):
            name_text = Text()
            name_text.append(name, style=StyleType.PACKAGE_NAME())
            name_text.append(" ", style=StyleType.WARNING())
            name_text.append("(redundant)", style=StyleType.WARNING())
        else:
            name_text = Text(name, style=StyleType.PACKAGE_NAME())
        styled_row.append(name_text)

        # Handle required version
        required_version = package_data.get("required_version", "")
        if required_version:
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
        status = package_data.get("status", "")
        status_style = get_style(status)

        if installed_version:
            installed_text = Text(installed_version, style=Style(color="cyan"))
        else:
            installed_text = Text("None", style=Style(color="yellow"))
        styled_row.append(installed_text)

        # Handle status
        status_symbol = get_status_symbol(status)
        if status in ["missing", "version_mismatch"]:
            status_text = Text(status_symbol, style=StyleType.ERROR())
        else:
            status_text = Text(status_symbol, style=status_style)
        styled_row.append(status_text)

        # Add the row to the table with appropriate styling
        if package_data.get("is_dependency"):
            table.add_row(*styled_row, style=StyleType.PACKAGE_DEPENDENCY())
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
    table.add_column("Package Tree", style=StyleType.PACKAGE_NAME())
    table.add_column("Required", style=StyleType.PACKAGE_VERSION())
    table.add_column("Installed", style=StyleType.PACKAGE_VERSION())
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

        # Format version displays
        if required_version:
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
    }

    status_styles = {
        "normal": "green",
        "outdated": "red",
        "missing": "red",
        "redundant": "yellow",
        "version_mismatch": "red",
        "not_in_requirements": "yellow",
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

        if not is_dependency:
            top_level_packages.append(pkg_data)
            status = pkg_data.get("status", "")
            # Handle missing packages (required but not installed)
            if pkg_data.get("required_version") and not pkg_data.get(
                "installed_version"
            ):
                status = "missing"
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


def create_fix_tip() -> None:
    """Display tip message for package issues"""
    tip = Text(style=StyleType.DIM())
    tip.append("Tip: Run ")
    tip.append("pm fix", style=StyleType.COMMAND())
    tip.append(" to resolve package inconsistencies")
    console.print(tip)


def print_table(table: Table) -> None:
    """Print table with consistent padding"""
    console.print("\n")
    console.print(table)
    console.print("\n")
