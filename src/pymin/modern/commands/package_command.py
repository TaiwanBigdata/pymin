"""Package management commands"""

import click
from typing import List
from ..core.venv_manager import VenvManager
from ..ui.console import display_panel, print_error, progress_status
from ..ui.style import StyleType
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
        text = Text()
        for i, (pkg, info) in enumerate(results.items()):
            text.append_field(
                pkg,
                info.get("version", ""),
                label_style=StyleType.PACKAGE_NAME,
                value_style=(
                    StyleType.SUCCESS
                    if info["status"] == "installed"
                    else StyleType.ERROR
                ),
                note=info.get("message"),
                note_style=(
                    StyleType.SUCCESS
                    if info["status"] == "installed"
                    else StyleType.ERROR
                ),
                add_line_after=(i < len(results) - 1),
            )

        display_panel("Package Installation Results", text)

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
        text = Text()
        for i, (pkg, info) in enumerate(results.items()):
            text.append_field(
                pkg,
                info.get("version", ""),
                label_style=StyleType.PACKAGE_NAME,
                value_style=(
                    StyleType.SUCCESS
                    if info["status"] == "removed"
                    else StyleType.ERROR
                ),
                note=info.get("message"),
                note_style=(
                    StyleType.SUCCESS
                    if info["status"] == "removed"
                    else StyleType.ERROR
                ),
                add_line_after=(i < len(results) - 1),
            )

        display_panel("Package Removal Results", text)

    except Exception as e:
        print_error(f"Failed to remove packages: {str(e)}")
