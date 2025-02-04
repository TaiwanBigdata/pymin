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
                if info.get("dependencies"):
                    console.print()  # Add a blank line
                    console.print("[dim]Installed dependencies:[/dim]")
                    for dep in sorted(info["dependencies"]):
                        console.print(f"[dim]  • {dep}[/dim]")
            else:
                console.print(
                    f"[red]{SymbolType.ERROR}[/red] Failed to add [cyan]{pkg}[/cyan]: {info.get('message', 'Unknown error')}"
                )
            console.print()

    except Exception as e:
        print_error(f"Failed to add packages: {str(e)}")


@click.command()
@click.argument("packages", nargs=-1, required=True)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
def remove(packages: List[str], yes: bool = False):
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

        # Confirm removal if not using --yes
        if not yes:
            package_list = ", ".join(packages)
            if not click.confirm(
                f"Remove {package_list} and their dependencies?",
                default=False,
            ):
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
                # Show removed dependencies if any
                if info.get("dependencies"):
                    console.print("[dim]Removed dependencies:[/dim]")
                    for dep in sorted(info["dependencies"]):
                        console.print(f"[dim]  • {dep}[/dim]")
            else:
                console.print(
                    f"[red]{SymbolType.ERROR}[/red] Failed to remove [cyan]{pkg}[/cyan]: {info.get('message', 'Unknown error')}"
                )
            console.print()

    except Exception as e:
        print_error(f"Failed to remove packages: {str(e)}")
