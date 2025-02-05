"""Package management commands"""

import click
from typing import List, Dict, Union
from ..core.venv_manager import VenvManager
from ..ui.console import (
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
    progress_status,
)
from ..ui.style import StyleType, SymbolType
from ..ui.formatting import Text
from ..core.package_analyzer import PackageAnalyzer

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
@click.argument("packages", nargs=-1, required=True)
@click.option(
    "--dev",
    is_flag=True,
    help="Install as development dependency",
)
@click.option(
    "-e",
    "--editable",
    is_flag=True,
    help="Install in editable mode",
)
@click.option(
    "--no-deps",
    is_flag=True,
    help="Don't install package dependencies",
)
def add(
    packages: List[str],
    dev: bool = False,
    editable: bool = False,
    no_deps: bool = False,
):
    """Add packages to the virtual environment

    PACKAGES: One or more package names to add
    """
    try:
        manager = VenvManager()

        # Check if we're in a virtual environment
        if not manager.from_env:
            print_error(
                "No virtual environment is active. Use 'pmm on' to activate one."
            )
            return

        with progress_status("Installing packages..."):
            # Install packages and update requirements.txt
            results = manager.add_packages(
                packages,
                dev=dev,
                editable=editable,
                no_deps=no_deps,
            )

        # Display results
        console.print()
        for pkg, info in results.items():
            # Show main package result
            if info["status"] == "installed":
                console.print(
                    f"[green]{SymbolType.SUCCESS}[/green] Added [cyan]{pkg}=={info['version']}[/cyan]"
                )
                # Show dependencies if any
                if info.get("new_dependencies") or info.get(
                    "existing_dependencies"
                ):
                    # Get versions for all dependencies
                    dep_versions = {}
                    for dep in info.get("new_dependencies", []) + info.get(
                        "existing_dependencies", []
                    ):
                        dep_version = (
                            manager.package_manager._get_installed_version(dep)
                        )
                        if dep_version:
                            dep_versions[dep] = dep_version

                    # Format dependencies with versions
                    if dep_versions:
                        deps_str = ", ".join(
                            f"[cyan]{dep}=={version}[/cyan]"
                            for dep, version in sorted(dep_versions.items())
                        )
                        console.print(
                            f"[dim]Installed dependencies:  {deps_str}[/dim]"
                        )
                console.print()  # Add a blank line between packages
            else:
                error_msg = info.get("message", "Unknown error")

                # Check if it's a version-related error
                if "Version not found" in error_msg:
                    console.print(
                        f"[red]{SymbolType.ERROR}[/red] Failed to add [cyan]{pkg}[/cyan]"
                    )
                    # Split the message to show versions in a better format
                    if "Latest version:" in error_msg:
                        latest_ver = (
                            error_msg.split("Latest version:")[1]
                            .split("\n")[0]
                            .strip()
                        )
                        console.print(
                            f"Latest version: [green]{latest_ver}[/green]"
                        )
                        if "Recent versions:" in error_msg:
                            versions = error_msg.split("Recent versions:")[
                                1
                            ].strip()
                            console.print(
                                f"Recent versions: [cyan]{versions}[/cyan]"
                            )
                    else:
                        console.print(error_msg)
                else:
                    console.print(
                        f"[red]{SymbolType.ERROR}[/red] Failed to add [cyan]{pkg}[/cyan]: {error_msg}"
                    )
                console.print()

    except Exception as e:
        print_error(f"Failed to add packages: {str(e)}")
        return


@click.command()
@click.argument("packages", nargs=-1, required=True)
def remove(packages: List[str]):
    """Remove packages from the virtual environment

    PACKAGES: One or more package names to remove
    """
    try:
        manager = VenvManager()

        # Check if we're in a virtual environment
        if not manager.from_env:
            print_error(
                "No virtual environment is active. Use 'pmm on' to activate one."
            )
            return

        with progress_status("Removing packages..."):
            # Remove packages from requirements.txt and uninstall them
            results = manager.remove_packages(packages)

        # Display results
        console.print()

        # Track dependencies that have been shown
        shown_deps = set()

        for pkg in packages:  # 只顯示主要請求移除的套件
            if pkg not in results:
                continue

            info = results[pkg]
            if info["status"] == "removed":
                console.print(
                    f"[green]{SymbolType.SUCCESS}[/green] Removed [cyan]{pkg}=={info['version']}[/cyan]"
                )

                # Show dependency information
                dep_info = info.get("dependency_info", {})

                # 已移除的依賴
                if "removable_deps" in dep_info:
                    removable_deps = sorted(dep_info["removable_deps"])
                    if removable_deps:
                        # 取得被移除依賴的版本
                        deps_with_versions = []
                        for dep in removable_deps:
                            version = (
                                manager.package_manager._get_installed_version(
                                    dep
                                )
                            )
                            deps_with_versions.append(
                                f"[cyan]{dep}=={version}[/cyan]"
                            )
                        console.print(
                            f"[dim]Removed dependencies:  {', '.join(deps_with_versions)}[/dim]"
                        )

                # 被保留的依賴
                if "kept_deps" in dep_info:
                    kept_deps = sorted(dep_info["kept_deps"])
                    if kept_deps:
                        deps_with_versions = []
                        for dep in kept_deps:
                            version = (
                                manager.package_manager._get_installed_version(
                                    dep
                                )
                            )
                            # 從 dep_info 中取得 kept_for 資訊
                            kept_for = dep_info.get(dep, {}).get("kept_for", [])
                            if kept_for:
                                dependents = sorted(kept_for)
                                deps_with_versions.append(
                                    f"[cyan]{dep}=={version}[/cyan] (required by: {', '.join(dependents)})"
                                )
                            else:
                                # 如果沒有 kept_for 資訊，可能需要重新檢查依賴關係
                                all_deps = (
                                    manager.package_manager._get_all_dependencies()
                                )
                                other_dependents = sorted(
                                    all_deps.get(dep, set())
                                )
                                if other_dependents:
                                    deps_with_versions.append(
                                        f"[cyan]{dep}=={version}[/cyan] (required by: {', '.join(other_dependents)})"
                                    )
                                else:
                                    deps_with_versions.append(
                                        f"[cyan]{dep}=={version}[/cyan]"
                                    )
                        if deps_with_versions:
                            console.print(
                                f"[dim]Kept dependencies:  {', '.join(deps_with_versions)}[/dim]"
                            )

                console.print()  # Add a blank line after each main package

            elif info["status"] == "not_found":
                console.print(
                    f"[yellow]{SymbolType.WARNING}[/yellow] [cyan]{pkg}[/cyan]: {info['message']}"
                )
                console.print()
            else:
                console.print(
                    f"[red]{SymbolType.ERROR}[/red] Failed to remove [cyan]{pkg}[/cyan]: {info.get('message', 'Unknown error')}"
                )
                console.print()

    except Exception as e:
        print_error(f"Failed to remove packages: {str(e)}")
        return


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
