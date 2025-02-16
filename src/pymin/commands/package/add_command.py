"""Add packages command"""

import click
from typing import List, Dict, Tuple
from ...core.venv_manager import VenvManager
from ...core.package_analyzer import PackageAnalyzer
from ...ui.console import (
    print_error,
    print_warning,
    print_success,
    console,
    progress_status,
    print_tips,
    print_info,
)
from ...ui.style import SymbolType
from pathlib import Path

# Create package analyzer instance
pkg_analyzer = PackageAnalyzer()


@click.command()
@click.argument("packages", nargs=-1)
@click.option(
    "-e",
    "--editable",
    is_flag=True,
    help="Install the package in editable mode",
)
@click.option(
    "-d",
    "--dev",
    is_flag=True,
    help="Add as development dependency",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Skip confirmation",
)
def add(
    packages: Tuple[str, ...],
    editable: bool = False,
    dev: bool = False,
    yes: bool = False,
):
    """Add packages to the project"""
    try:
        manager = VenvManager()

        # Check if we're in a virtual environment
        if not manager.from_env:
            print_error(
                "No virtual environment is active. Use 'pmm on' to activate one."
            )
            return

        # Determine which configuration file to use
        use_pyproject, reason = pkg_analyzer.determine_config_source()
        print_info(reason)

        # Handle editable installs
        args = list(packages)
        if editable:
            args = ["-e"] + args

        # Filter out other options
        filtered_packages = [p for p in args if not p.startswith("-")]

        with progress_status("Installing packages..."):
            # Install packages without updating requirements.txt if using pyproject.toml
            if use_pyproject:
                # Temporarily disable requirements.txt updates
                original_update_requirements = (
                    manager.package_manager._update_requirements
                )
                manager.package_manager._update_requirements = (
                    lambda *args, **kwargs: None
                )

                try:
                    results = manager.add_packages(
                        filtered_packages,
                        dev=dev,
                        editable=editable,
                    )
                finally:
                    # Restore original update function
                    manager.package_manager._update_requirements = (
                        original_update_requirements
                    )
            else:
                # Normal installation with requirements.txt update
                results = manager.add_packages(
                    filtered_packages,
                    dev=dev,
                    editable=editable,
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
                if version_info and (
                    "Version not found" in error_msg
                    or "No matching distribution" in error_msg
                    or "Could not find a version that satisfies the requirement"
                    in error_msg
                ):
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
                    for pkg_spec in filtered_packages:
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
                    elif (
                        "not found" in error_msg
                        or "No matching distribution" in error_msg
                    ):
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
                        if use_pyproject:
                            # Temporarily disable requirements.txt updates
                            original_update_requirements = (
                                manager.package_manager._update_requirements
                            )
                            manager.package_manager._update_requirements = (
                                lambda *args, **kwargs: None
                            )

                            try:
                                retry_results = manager.add_packages(
                                    [f"{pkg}=={latest_version}"],
                                    dev=dev,
                                    editable=editable,
                                )
                            finally:
                                # Restore original update function
                                manager.package_manager._update_requirements = (
                                    original_update_requirements
                                )

                            # If installation is successful, update pyproject.toml
                            retry_info = retry_results.get(pkg, {})
                            if retry_info.get("status") == "installed":
                                version = retry_info["version"]
                                # Initialize PyProjectManager
                                from ...core.pyproject_manager import (
                                    PyProjectManager,
                                )

                                proj_manager = PyProjectManager(
                                    Path("pyproject.toml")
                                )
                                proj_manager.add_dependency(pkg, version, ">=")
                        else:
                            retry_results = manager.add_packages(
                                [f"{pkg}=={latest_version}"],
                                dev=dev,
                                editable=editable,
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
                            f"[red]{SymbolType.ERROR}[/red] Failed to add [cyan]{pkg}[/cyan]: {error_msg}"
                        )
                        if version_info:
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

        # Display installation tips if any
        if installation_tips:
            print_tips(installation_tips)

        console.print()
    except Exception as e:
        print_error(f"Failed to add packages: {str(e)}")
        return
