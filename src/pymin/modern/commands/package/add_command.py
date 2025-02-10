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
    print_tips,
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

        # Store tips and auto-fixed packages
        installation_tips = []
        auto_fixed_packages = []

        # Display results in installation order
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
                    # Try to install the latest version
                    latest_version = (
                        version_info["latest_versions"]
                        .split(",")[0]
                        .strip()
                        .replace("[cyan]", "")
                        .replace("[/cyan]", "")
                        .replace(" (latest)", "")
                    )

                    # Get original version from package spec
                    original_version = None
                    for pkg_spec in packages:
                        if pkg_spec.startswith(f"{pkg}=="):
                            original_version = pkg_spec.split("==")[1]
                            break

                    # Analyze update reason
                    update_reason = ""
                    if (
                        "Python version" in error_msg
                        or "requires Python" in error_msg
                    ):
                        update_reason = "Python compatibility issue"
                    elif "dependency conflict" in error_msg:
                        update_reason = "Dependency conflict"
                    elif "not found" in error_msg:
                        update_reason = "Version not found"
                    else:
                        update_reason = "Installation failed"

                    # Record package with original and new version
                    auto_fixed_packages.append(
                        (
                            pkg,
                            original_version or "unknown",
                            latest_version,
                            update_reason,
                        )
                    )

                    # Retry with latest version
                    with progress_status(
                        f"Trying latest version {latest_version}..."
                    ):
                        retry_results = manager.add_packages(
                            [f"{pkg}=={latest_version}"],
                            dev=dev,
                            editable=editable,
                            no_deps=no_deps,
                        )

                    # Check retry results
                    retry_info = retry_results.get(pkg, {})
                    if retry_info.get("status") == "installed":
                        console.print(
                            f"[bold][yellow]{SymbolType.WARNING}[/yellow] Auto-fixed [cyan]{pkg}[/cyan] to version [cyan]{latest_version}[/cyan][/bold]"
                        )
                        if retry_info.get("new_dependencies") or retry_info.get(
                            "existing_dependencies"
                        ):
                            dep_versions = {}
                            for dep in retry_info.get(
                                "new_dependencies", []
                            ) + retry_info.get("existing_dependencies", []):
                                dep_version = manager.package_manager._get_installed_version(
                                    dep
                                )
                                if dep_version:
                                    dep_versions[dep] = dep_version

                            if dep_versions:
                                deps_str = ", ".join(
                                    f"[cyan]{dep}=={version}[/cyan]"
                                    for dep, version in sorted(
                                        dep_versions.items()
                                    )
                                )
                                console.print(
                                    f"[dim]Installed dependencies:  {deps_str}[/dim]"
                                )
                    else:
                        console.print(
                            f"[red]{SymbolType.ERROR}[/red] Failed to add [cyan]{pkg}[/cyan]"
                        )
                        console.print(
                            f"[dim][yellow]Latest versions:[/yellow] {version_info['latest_versions']}[/dim]"
                        )
                        console.print(
                            f"[dim][yellow]Similar versions:[/yellow] {version_info['similar_versions']}[/dim]"
                        )
                        installation_tips.append(
                            f"[cyan]pmm add {pkg}=={latest_version}[/cyan] to install the latest version"
                        )
                else:
                    console.print(
                        f"[red]{SymbolType.ERROR}[/red] Failed to add [cyan]{pkg}[/cyan]: {error_msg}"
                    )
            console.print()  # Add a blank line between packages

        # Display auto-fixed packages summary
        if auto_fixed_packages:
            console.print()
            print_warning(
                "Some packages were automatically updated to their latest compatible versions:"
            )
            for (
                pkg,
                original_version,
                latest_version,
                reason,
            ) in auto_fixed_packages:
                console.print(
                    f"[dim]• [cyan]{pkg}[/cyan] {original_version} ([yellow]{reason}[/yellow]) -> [cyan]{latest_version}[/cyan][/dim]"
                )
            console.print()

        # Display installation tips if any
        if installation_tips:
            console.print()  # Add an extra blank line before tips
            print_tips(installation_tips)

    except Exception as e:
        print_error(f"Failed to add packages: {str(e)}")
        return
