"""Package management commands implementation"""

import click
from pathlib import Path
from typing import List, Optional
from rich.panel import Panel
from rich.text import Text
from ..core.venv_manager import VenvManager
from ..ui.console import (
    print_success,
    print_error,
    print_warning,
    progress_status,
    console,
)
from ..ui.style import StyleType, SymbolType


@click.command()
@click.argument("packages", nargs=-1, required=True)
@click.option(
    "-d",
    "--dev",
    is_flag=True,
    help="Add packages as development dependencies",
)
@click.option(
    "-e",
    "--editable",
    is_flag=True,
    help="Install a project in editable mode",
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
    """Add packages to requirements.txt and install them

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

        with progress_status("Adding packages..."):
            # Add packages to requirements.txt and install them
            results = manager.add_packages(
                packages,
                dev=dev,
                editable=editable,
                no_deps=no_deps,
            )

        # Display results
        text = Text()
        for pkg, info in results.items():
            text.append(f"{pkg}: ", style=StyleType.PACKAGE_NAME)
            if info["status"] == "installed":
                text.append(
                    f"{SymbolType.SUCCESS} Installed ",
                    style=StyleType.SUCCESS,
                )
                text.append(
                    f"({info['version']})",
                    style=StyleType.PACKAGE_VERSION,
                )
            elif info["status"] == "updated":
                text.append(
                    f"{SymbolType.SUCCESS} Updated ",
                    style=StyleType.SUCCESS,
                )
                text.append(
                    f"({info['old_version']} → {info['version']})",
                    style=StyleType.PACKAGE_VERSION,
                )
            elif info["status"] == "already_installed":
                text.append(
                    f"{SymbolType.INFO} Already installed ",
                    style=StyleType.INFO,
                )
                text.append(
                    f"({info['version']})",
                    style=StyleType.PACKAGE_VERSION,
                )
            text.append("\n")

        console.print(
            Panel(
                text,
                title="Package Installation Results",
                title_align="left",
                border_style=StyleType.SUCCESS,
                padding=(1, 2),
            )
        )

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
    """Remove packages from requirements.txt and uninstall them

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
        text = Text()
        for pkg, info in results.items():
            text.append(f"{pkg}: ", style=StyleType.PACKAGE_NAME)
            if info["status"] == "removed":
                text.append(
                    f"{SymbolType.SUCCESS} Removed",
                    style=StyleType.SUCCESS,
                )
            elif info["status"] == "not_found":
                text.append(
                    f"{SymbolType.WARNING} Not found",
                    style=StyleType.WARNING,
                )
            elif info["status"] == "error":
                text.append(
                    f"{SymbolType.ERROR} {info['message']}",
                    style=StyleType.ERROR,
                )
            text.append("\n")

        console.print(
            Panel(
                text,
                title="Package Removal Results",
                title_align="left",
                border_style=StyleType.SUCCESS,
                padding=(1, 2),
            )
        )

    except Exception as e:
        print_error(f"Failed to remove packages: {str(e)}")


# Alias for remove command
rm = remove
