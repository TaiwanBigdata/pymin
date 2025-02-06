"""List installed packages command"""

import click
from typing import List, Dict, Union
from ...core.venv_manager import VenvManager
from ...core.package_analyzer import PackageAnalyzer
from ...ui.console import (
    print_error,
    print_warning,
    print_success,
    console,
    create_package_table,
    create_dependency_tree,
    print_table,
    create_package_summary,
    create_summary_panel,
    create_fix_tip,
)

# Create package analyzer instance
pkg_analyzer = PackageAnalyzer()


def should_show_fix_tip(packages: Union[List[Dict], Dict[str, Dict]]) -> bool:
    """Check if there are any non-normal package statuses in top-level packages"""
    if isinstance(packages, dict):
        return any(
            pkg.get("status") not in [None, "normal"]
            for pkg in packages.values()
            if not pkg.get("is_dependency")
        )
    return any(
        pkg.get("status") not in [None, "normal"]
        for pkg in packages
        if not pkg.get("is_dependency")
    )


@click.command()
@click.option(
    "-a", "--all", "show_all", is_flag=True, help="Show all installed packages"
)
@click.option(
    "-t", "--tree", "show_tree", is_flag=True, help="Show dependency tree"
)
def list(show_all: bool, show_tree: bool):
    """List installed packages"""
    try:
        if show_tree:
            # Get dependency tree
            packages = pkg_analyzer.get_dependency_tree()
            if not packages:
                print_warning("No installed packages found")
                return

            # Create and display dependency tree
            tree_table = create_dependency_tree(packages)
            print_table(tree_table)

            # Display summary
            summary_content = create_package_summary(
                packages, mode="dependency_tree"
            )
            console.print(
                create_summary_panel("Package Summary", summary_content)
            )

            # Show fix tip if needed
            if should_show_fix_tip(packages):
                console.print()
                create_fix_tip()

        else:
            # Get package data
            if show_all:
                packages = pkg_analyzer.get_installed_packages()
                title = "All Installed Packages"
                mode = "all_installed"
                # Get top level packages for dimming check
                top_level_packages = pkg_analyzer.get_top_level_packages()
            else:
                packages = pkg_analyzer.get_top_level_packages()
                title = "Top Level Packages"
                mode = "top_level"

            if not packages:
                print_warning("No installed packages found")
                return

            # Get all dependencies for redundancy check
            all_packages = pkg_analyzer.get_installed_packages()
            all_dependencies = set()
            requirements = pkg_analyzer._parse_requirements()
            for pkg_info in all_packages.values():
                deps = pkg_info.get("dependencies", [])
                all_dependencies.update(deps)

            # Convert package data to table rows
            rows = []
            for name, data in sorted(packages.items()):
                # Handle both dictionary and string (version) formats
                if isinstance(data, dict):
                    package_data = data
                else:
                    package_data = {
                        "name": name,
                        "installed_version": data,
                        "required_version": "",
                    }

                # Check if package is redundant (in requirements.txt and is a dependency)
                if name in requirements and name in all_dependencies:
                    package_data["redundant"] = True
                    package_data["status"] = "redundant"
                # Check if package is missing (in requirements.txt but not installed)
                elif name in requirements and not package_data.get(
                    "installed_version"
                ):
                    package_data["status"] = "missing"

                # Mark if package is not top-level (for dimming in display)
                if show_all and name not in top_level_packages:
                    package_data["is_dependency"] = True

                rows.append([package_data])

            # Create and display table
            table = create_package_table(
                title,
                ["Package Name", "Required", "Installed", "Status"],
                rows,
            )
            print_table(table)

            # Display summary
            summary_content = create_package_summary(packages, mode=mode)
            console.print(
                create_summary_panel("Package Summary", summary_content)
            )
            console.print("\n")

            # Show fix tip if needed
            if should_show_fix_tip(packages):
                create_fix_tip()

    except Exception as e:
        print_error(f"Error: {str(e)}")
        return
