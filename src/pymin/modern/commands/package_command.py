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
                            (
                                f"{dep}=={version}"  # 新安裝的套件保持原色
                                if dep in info.get("new_dependencies", [])
                                else f"[white dim]{dep}=={version}[/white dim]"  # 已安裝的套件使用白色 dim
                            )
                            for dep, version in sorted(dep_versions.items())
                        )
                        console.print(f"Dependencies:  {deps_str}")
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
        for pkg, info in results.items():
            # Show main package result
            if info["status"] == "removed":
                console.print(
                    f"[green]{SymbolType.SUCCESS}[/green] Removed [cyan]{pkg}=={info['version']}[/cyan]"
                )

                # Show dependency information
                dep_info = info.get("dependency_info", {})

                # Show removed dependencies
                if "removable_deps" in dep_info:
                    console.print("[yellow]Removed dependencies:[/yellow]")
                    for dep in sorted(dep_info["removable_deps"]):
                        console.print(f"[dim]  • {dep}[/dim]")

                # Show kept dependencies
                if "kept_for" in dep_info:
                    console.print(
                        "[yellow]Dependencies kept (used by other packages):[/yellow]"
                    )
                    for pkg in sorted(dep_info["kept_for"]):
                        console.print(f"[dim]  • Required by: {pkg}[/dim]")

            elif info["status"] == "not_found":
                console.print(
                    f"[yellow]{SymbolType.WARNING}[/yellow] [cyan]{pkg}[/cyan]: {info['message']}"
                )
            else:
                console.print(
                    f"[red]{SymbolType.ERROR}[/red] Failed to remove [cyan]{pkg}[/cyan]: {info.get('message', 'Unknown error')}"
                )
            console.print()

    except Exception as e:
        print_error(f"Failed to remove packages: {str(e)}")
        return
