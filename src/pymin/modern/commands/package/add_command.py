"""Add packages command"""

import click
from typing import List, Dict
from ...core.venv_manager import VenvManager
from ...core.package_analyzer import PackageAnalyzer
from ...ui.console import (
    print_error,
    print_warning,
    print_success,
    console,
    progress_status,
)
from ...ui.style import SymbolType

# Create package analyzer instance
pkg_analyzer = PackageAnalyzer()


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

        # 儲存所有需要顯示的 tips
        installation_tips = []

        # 按照安裝順序顯示結果
        for pkg, info in results.items():
            if info["status"] == "installed":
                console.print(
                    f"[bold][green]{SymbolType.SUCCESS}[/green] Added [cyan]{pkg}=={info['version']}[/cyan][/bold]"
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
            else:
                error_msg = info.get("message", "Unknown error")
                version_info = info.get("version_info", {})

                # Check if it's a version-related error
                if "Version not found" in error_msg and version_info:
                    console.print(
                        f"[red]{SymbolType.ERROR}[/red] Failed to add [cyan]{pkg}[/cyan]"
                    )
                    console.print(
                        f"[dim][yellow]Latest versions:[/yellow] {version_info['latest_versions']}[/dim]"
                    )
                    console.print(
                        f"[dim][yellow]Similar versions:[/yellow] {version_info['similar_versions']}[/dim]"
                    )

                    # Store installation tip for later
                    latest_version = (
                        version_info["latest_versions"]
                        .split(",")[0]
                        .strip()
                        .replace("[cyan]", "")
                        .replace("[/cyan]", "")
                        .replace(" (latest)", "")
                    )
                    installation_tips.append(
                        f"• [cyan]pmm add {pkg}=={latest_version}[/cyan]"
                    )
                else:
                    console.print(
                        f"[red]{SymbolType.ERROR}[/red] Failed to add [cyan]{pkg}[/cyan]: {error_msg}"
                    )
            console.print()  # Add a blank line between packages

        # 最後顯示所有安裝建議
        if installation_tips:
            console.print()  # Add an extra blank line before tips
            console.print(
                "[dim]Tips: Try these commands to install the latest versions:[/dim]"
            )
            for tip in installation_tips:
                console.print(f"[dim]  {tip}[/dim]")

    except Exception as e:
        print_error(f"Failed to add packages: {str(e)}")
        return
