"""Package management commands"""

import click
from typing import List
from ..core.venv_manager import VenvManager
from ..ui.console import print_error, progress_status, console
from ..ui.style import StyleType, SymbolType
from ..ui.formatting import Text


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
