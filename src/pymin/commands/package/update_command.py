"""Update packages command"""

import click
import subprocess
from typing import List
from packaging.version import parse as parse_version
from ...core.venv_manager import VenvManager
from ...core.package_analyzer import PackageAnalyzer
from ...ui.console import (
    print_error,
    print_warning,
    print_success,
    console,
    progress_status,
)

# Create package analyzer instance
pkg_analyzer = PackageAnalyzer()


@click.command()
@click.argument("packages", nargs=-1)
@click.option(
    "-a",
    "--all",
    "update_all",
    is_flag=True,
    help="Update all installed packages",
)
@click.option(
    "--check",
    is_flag=True,
    help="Only check for updates without installing them",
)
def update(packages: List[str], update_all: bool = False, check: bool = False):
    """Update packages to their latest versions

    PACKAGES: Package names to update (optional)
    If no packages are specified and --all is not used, only packages in requirements.txt will be updated.
    """
    try:
        manager = VenvManager()

        # Check if we're in a virtual environment
        if not manager.from_env:
            print_error(
                "No virtual environment is active. Use 'pmm on' to activate one."
            )
            return

        # Get all installed packages
        installed_packages = pkg_analyzer.get_installed_packages()
        if not installed_packages:
            print_warning("No installed packages found")
            return

        # Get packages from requirements.txt
        requirements = pkg_analyzer._parse_requirements()

        # Determine which packages to update
        packages_to_check = []
        if update_all:
            packages_to_check = list(installed_packages.keys())
        elif packages:
            # Verify specified packages exist
            for pkg in packages:
                if pkg not in installed_packages:
                    print_error(f"Package {pkg} is not installed")
                    return
            packages_to_check = list(packages)
        else:
            # Only check packages in requirements.txt
            packages_to_check = list(requirements.keys())

        if not packages_to_check:
            print_warning("No packages to update")
            return

        # Get package information from PyPI
        updates_available = []
        with progress_status("Checking for updates..."):
            for pkg_name in packages_to_check:
                if pkg_name not in installed_packages:
                    continue

                current_version = installed_packages[pkg_name][
                    "installed_version"
                ]

                # Get latest version from PyPI
                try:
                    process = subprocess.run(
                        ["pip", "index", "versions", pkg_name],
                        capture_output=True,
                        text=True,
                    )

                    if process.returncode == 0:
                        # Parse output to get latest version
                        lines = process.stdout.splitlines()
                        for line in lines:
                            if "Available versions:" in line:
                                versions = (
                                    line.split(":", 1)[1].strip().split(", ")
                                )
                                if versions:
                                    latest_version = versions[
                                        0
                                    ]  # First version is the latest
                                    if parse_version(
                                        latest_version
                                    ) > parse_version(current_version):
                                        updates_available.append(
                                            {
                                                "name": pkg_name,
                                                "current_version": current_version,
                                                "latest_version": latest_version,
                                                "in_requirements": pkg_name
                                                in requirements,
                                            }
                                        )
                except Exception as e:
                    print_warning(
                        f"Failed to check updates for {pkg_name}: {str(e)}"
                    )
                    continue

        # Display results
        if not updates_available:
            print_success("All packages are up to date!")
            return

        # Show available updates
        console.print("\n[cyan]Available Updates:[/cyan]")
        for pkg in updates_available:
            status = (
                "[dim](in requirements.txt)[/dim]"
                if pkg["in_requirements"]
                else ""
            )
            console.print(
                f"  [cyan]{pkg['name']}[/cyan]: "
                f"[yellow]{pkg['current_version']}[/yellow] → "
                f"[green]{pkg['latest_version']}[/green] {status}"
            )

        if check:
            return

        # Confirm updates
        if not click.confirm(
            "\nDo you want to update these packages?", default=True
        ):
            return

        # Update packages
        success_count = 0
        error_count = 0
        with progress_status("Updating packages..."):
            for pkg in updates_available:
                try:
                    # Update the package
                    process = subprocess.run(
                        [
                            str(manager.package_manager._pip_path),
                            "install",
                            "-U",
                            f"{pkg['name']}=={pkg['latest_version']}",
                        ],
                        capture_output=True,
                        text=True,
                    )

                    if process.returncode == 0:
                        # Only update requirements.txt if the package was already in it
                        if pkg["in_requirements"]:
                            manager.package_manager._update_requirements(
                                added=[
                                    f"{pkg['name']}=={pkg['latest_version']}"
                                ]
                            )
                        success_count += 1
                    else:
                        print_error(
                            f"Failed to update {pkg['name']}: {process.stderr}"
                        )
                        error_count += 1
                except Exception as e:
                    print_error(f"Failed to update {pkg['name']}: {str(e)}")
                    error_count += 1

        # Show summary
        console.print()
        if success_count > 0:
            print_success(f"Successfully updated {success_count} package(s)")
        if error_count > 0:
            print_error(f"Failed to update {error_count} package(s)")

    except Exception as e:
        print_error(f"Failed to update packages: {str(e)}")
        return
