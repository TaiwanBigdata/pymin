# Display functionality for package management
from typing import Dict, List
from rich.table import Table
from rich.text import Text
from rich.box import HEAVY_HEAD
from rich.console import Console
from rich.style import Style

console = Console()

# Define styles
BORDER_STYLE = Style(color="bright_blue")
TREE_STYLE = Style(color="bright_blue")


def format_dependency_tree(tree: Dict, requirements: Dict[str, str]) -> Table:
    """Format dependency tree as a table.

    Args:
        tree: Dependency tree dictionary
        requirements: Requirements from requirements.txt

    Returns:
        Rich Table object
    """
    table = Table(
        title="Package Dependencies",
        box=HEAVY_HEAD,
        header_style="bold white",
        show_header=True,
        padding=(0, 1),
        expand=False,
        title_justify="left",
        title_style="white",
        border_style=BORDER_STYLE,
    )

    # Add columns with specific widths
    table.add_column("Package Tree", style="white")
    table.add_column("Required", style="white")
    table.add_column("Installed", style="white")
    table.add_column("Status", style="white", justify="center")

    # Track processed dependencies to avoid duplicates
    processed_deps = set()

    def _add_package_to_table(
        pkg_info: Dict, prefix: str = "", is_last: bool = True
    ) -> int:
        name = pkg_info["name"]
        if name == "pip":  # Skip pip package
            return 0

        installed = pkg_info["installed_version"]
        required = requirements.get(name)
        deps_count = 0

        # Format the display prefix with colored tree symbols
        if prefix:
            tree_part = "└── " if is_last else "├── "
            display_prefix = Text()
            display_prefix.append(prefix.replace("│", "┃"), style=TREE_STYLE)
            display_prefix.append(tree_part, style=TREE_STYLE)
        else:
            display_prefix = Text("")

        # Add the package row
        status = Text("△" if name not in requirements else "✓", style="white")
        pkg_name = Text()
        pkg_name.append(display_prefix)
        pkg_name.append(name, style="white")

        if name in processed_deps:
            # Handle repeated dependencies
            table.add_row(
                pkg_name,
                "",
                Text(installed or "", style="white"),
                status,
            )
            return 0
        else:
            # Add new package
            table.add_row(
                pkg_name,
                Text(
                    required or "None" if not prefix else "",
                    style="dim" if not prefix else "white",
                ),
                Text(installed or "", style="white"),
                status,
            )
            processed_deps.add(name)

        # Process dependencies
        if pkg_info["dependencies"]:
            new_prefix = prefix + ("     " if is_last else "┃    ")
            for i, dep in enumerate(pkg_info["dependencies"]):
                is_last_dep = i == len(pkg_info["dependencies"]) - 1
                deps_count += _add_package_to_table(
                    dep, new_prefix, is_last_dep
                )
                deps_count += 1

        # Add empty line after root packages
        if not prefix:
            table.add_row("", "", "", "")

        return deps_count

    # Process each top-level package
    total_deps = 0
    for pkg_info in tree:
        if pkg_info["name"] != "pip":  # Skip pip package
            total_deps += _add_package_to_table(pkg_info)

    return table, total_deps


def format_summary(
    tree: List[Dict], requirements: Dict[str, str], total_deps: int
) -> None:
    """Format and print summary information.

    Args:
        tree: List of top-level package trees
        requirements: Requirements from requirements.txt
        total_deps: Total number of dependencies
    """
    # Count packages (excluding pip)
    total_pkgs = sum(1 for pkg in tree if pkg["name"] != "pip")
    not_in_reqs = sum(
        1
        for pkg in tree
        if pkg["name"] not in requirements and pkg["name"] != "pip"
    )
    in_reqs = sum(
        1
        for pkg in tree
        if pkg["name"] in requirements and pkg["name"] != "pip"
    )

    console.print("\nSummary:", style="white")
    console.print(f"  • Total Packages: {total_pkgs}", style="white")
    console.print(f"  • In requirements.txt (✓): {in_reqs}", style="white")
    console.print(
        f"  • Not in requirements.txt (△): {not_in_reqs}", style="white"
    )
    console.print(
        f"  • Total Dependencies: {total_deps} (Direct: {total_pkgs})",
        style="white",
    )

    if not_in_reqs > 0:
        console.print(
            "\nTip: Run pm fix to resolve package inconsistencies", style="dim"
        )
