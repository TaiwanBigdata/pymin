# Package management functionality providing dependency handling and requirements.txt management
from pathlib import Path
import subprocess
import os
from typing import Dict, Optional
from rich.console import Console
from rich.table import Table
from rich.text import Text
import pkg_resources
from rich.prompt import Confirm
import sys
import time
import importlib

console = Console()


class PackageManager:
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.requirements_file = self.project_root / "requirements.txt"

    def _parse_requirements(self) -> Dict[str, str]:
        """Parse requirements.txt into a dictionary of package names and versions"""
        if not self.requirements_file.exists():
            return {}

        packages = {}
        with open(self.requirements_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Handle different requirement formats
                    if "==" in line:
                        name, version = line.split("==")
                        packages[name] = f"=={version}"
                    elif ">=" in line:
                        name, version = line.split(">=")
                        packages[name] = f">={version}"
                    elif "<=" in line:
                        name, version = line.split("<=")
                        packages[name] = f"<={version}"
                    else:
                        packages[line] = ""
        return packages

    def _write_requirements(self, packages: Dict[str, str]):
        """Write packages to requirements.txt"""
        with open(self.requirements_file, "w") as f:
            for name, version in sorted(packages.items()):
                f.write(f"{name}{version}\n")

    def _get_installed_version(self, package: str) -> Optional[str]:
        """Get installed version of a package using pip list"""
        try:
            result = subprocess.run(
                ["pip", "list", "--format=json"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                import json

                for pkg in json.loads(result.stdout):
                    if pkg["name"].lower() == package.lower():
                        return pkg["version"]
            return None
        except Exception:
            # Fallback to pkg_resources
            try:
                return pkg_resources.get_distribution(package).version
            except pkg_resources.DistributionNotFound:
                return None

    def _check_pip_upgrade(self, stderr: str):
        """Check if pip needs upgrade and handle it"""
        if "new release of pip is available" in stderr:
            if Confirm.ask(
                "[yellow]A new version of pip is available. Do you want to upgrade?[/yellow]"
            ):
                console.print("[yellow]Upgrading pip...[/yellow]")
                result = subprocess.run(
                    ["pip", "install", "--upgrade", "pip"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    console.print("[green]✓ Pip has been upgraded[/green]")
                else:
                    console.print(
                        f"[red]Failed to upgrade pip:[/red]\n{result.stderr}"
                    )

    def _check_package_exists(self, package: str) -> bool:
        """Check if package exists on PyPI"""
        try:
            result = subprocess.run(
                (
                    ["pip", "search", package]
                    if sys.version_info < (3, 7)
                    else ["pip", "index", "versions", package]
                ),
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _parse_version_from_pip_output(
        self, output: str, package: str
    ) -> Optional[str]:
        """Parse version from pip output"""
        for line in output.split("\n"):
            if f"Requirement already satisfied: {package}" in line:
                parts = line.split()
                if (
                    len(parts) >= 6
                ):  # Format: "Requirement already satisfied: package in path (version)"
                    version = parts[-1].strip("()")
                    return version
        return None

    def add(self, package: str, version: Optional[str] = None) -> bool:
        """Add a package to requirements.txt and install it"""
        if not Path(os.environ.get("VIRTUAL_ENV", "")).exists():
            console.print(
                "[red bold]No active virtual environment found.[/red bold]"
            )
            return False

        # Create requirements.txt if it doesn't exist
        if not self.requirements_file.exists():
            self.requirements_file.touch()
            console.print("[blue]Created requirements.txt[/blue]")

        packages = self._parse_requirements()

        try:
            # First check if pip needs upgrade
            result = subprocess.run(
                ["pip", "--version"], capture_output=True, text=True
            )
            if result.stderr:
                self._check_pip_upgrade(result.stderr)

            # Check if package is already installed
            pre_installed_version = self._get_installed_version(package)
            if pre_installed_version:
                # If version is specified and different from installed
                if version and version != pre_installed_version:
                    console.print(
                        f"[yellow]Updating [cyan]{package}[/cyan] to version [cyan]{version}[/cyan]...[/yellow]"
                    )
                    cmd = ["pip", "install", f"{package}=={version}"]
                    result = subprocess.run(cmd, capture_output=True, text=True)

                    if result.returncode != 0:
                        console.print(
                            f"[red bold]Failed to update [cyan]{package}[/cyan]:[/red bold]\n{result.stderr}"
                        )
                        return False

                    installed_version = version
                else:
                    installed_version = pre_installed_version
                    console.print(
                        f"[green]✓[/green] Package [cyan]{package}=={installed_version}[/cyan] is already installed"
                    )
            else:
                # Install new package
                console.print(
                    f"[yellow]Installing [cyan]{package}[/cyan]...[/yellow]"
                )
                cmd = ["pip", "install"]
                if version:
                    cmd.append(f"{package}=={version}")
                else:
                    cmd.append(package)

                result = subprocess.run(cmd, capture_output=True, text=True)

                if "already satisfied" in result.stdout:
                    # Try to get version from pip output first
                    installed_version = self._parse_version_from_pip_output(
                        result.stdout, package
                    )
                    if not installed_version:
                        installed_version = self._get_installed_version(package)

                    if not installed_version:
                        console.print(
                            f"[red bold]Failed to determine version for [cyan]{package}[/cyan][/red bold]"
                        )
                        return False

                    console.print(
                        f"[green]✓[/green] Package [cyan]{package}=={installed_version}[/cyan] is already installed"
                    )
                else:
                    if result.returncode != 0:
                        console.print(
                            f"[red bold]Failed to install [cyan]{package}[/cyan]:[/red bold]\n{result.stderr}"
                        )
                        return False

                    installed_version = self._get_installed_version(package)
                    if not installed_version:
                        console.print(
                            f"[red bold]Package [cyan]{package}[/cyan] was not installed correctly.[/red bold]"
                        )
                        return False
                    console.print(
                        f"[green]✓[/green] Added [cyan]{package}=={installed_version}[/cyan]"
                    )

            # Only update requirements.txt if we have a valid version
            if installed_version:
                packages[package] = f"=={installed_version}"
                self._write_requirements(packages)
                console.print("[blue]✓ Updated requirements.txt[/blue]")
                return True
            return False

        except Exception as e:
            console.print(
                f"[red bold]Error installing [cyan]{package}[/cyan]:[/red bold]\n{str(e)}"
            )
            return False

    def remove(self, package: str) -> bool:
        """Remove a package from requirements.txt and uninstall it"""
        if not Path(os.environ.get("VIRTUAL_ENV", "")).exists():
            console.print("[red]No active virtual environment found.[/red]")
            return False

        packages = self._parse_requirements()
        if package not in packages:
            console.print(
                f"[yellow]Package {package} not found in requirements.txt[/yellow]"
            )
            return False

        try:
            result = subprocess.run(
                ["pip", "uninstall", "-y", package],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                console.print(
                    f"[red]Failed to uninstall {package}:[/red]\n{result.stderr}"
                )
                return False

            del packages[package]
            self._write_requirements(packages)
            console.print(f"[green]✓ Removed {package}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error removing {package}:[/red]\n{str(e)}")
            return False

    def _get_all_installed_packages(self) -> Dict[str, str]:
        """Get all installed packages and their versions"""
        packages = {}
        try:
            result = subprocess.run(
                ["pip", "list", "--format=json"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                import json

                for pkg in json.loads(result.stdout):
                    packages[pkg["name"]] = pkg["version"]
        except Exception:
            # Fallback to pkg_resources if pip list fails
            for pkg in pkg_resources.working_set:
                packages[pkg.key] = pkg.version
        return packages

    def _get_package_dependencies(self, package: str) -> Dict[str, list]:
        """Get package dependencies using pip show"""
        try:
            result = subprocess.run(
                ["pip", "show", package],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                deps = {"requires": [], "required_by": []}
                for line in result.stdout.split("\n"):
                    if line.startswith("Requires: "):
                        deps["requires"] = [
                            d.strip() for d in line[9:].split(",") if d.strip()
                        ]
                    elif line.startswith("Required-by: "):
                        deps["required_by"] = [
                            d.strip() for d in line[12:].split(",") if d.strip()
                        ]
                return deps
            return {"requires": [], "required_by": []}  # Command failed
        except Exception:
            return {"requires": [], "required_by": []}

    def _build_dependency_tree(self, package: str, seen=None) -> dict:
        """Build a dependency tree for a package"""
        if seen is None:
            seen = set()

        if package in seen:
            return {}  # Prevent circular dependencies

        seen.add(package)
        deps = self._get_package_dependencies(package)
        tree = {}
        installed_packages = self._get_all_installed_packages()

        for dep in deps.get("requires", []):
            if dep and dep.lower() != "none" and dep in installed_packages:
                tree[dep] = self._build_dependency_tree(dep, seen)

        return tree

    def _get_all_main_packages(self) -> Dict[str, str]:
        """Get all installed main packages (not dependencies) and their versions"""
        installed = self._get_all_installed_packages()
        main_packages = {}

        # First, add all packages from requirements.txt (even if not installed)
        req_packages = self._parse_requirements()
        for pkg in req_packages:
            main_packages[pkg] = installed.get(pkg, "")

        # Then add packages that are not dependencies of any other package
        for pkg in installed:
            # Skip system packages
            if pkg.lower() in ("pip", "setuptools", "wheel") or pkg.startswith(
                ("pip-", "setuptools-", "wheel-")
            ):
                continue

            # Skip if already added from requirements.txt
            if pkg in main_packages:
                continue

            deps = self._get_package_dependencies(pkg)
            if not deps.get("required_by") or all(
                req.strip() == "none" for req in deps.get("required_by", [])
            ):
                main_packages[pkg] = installed[pkg]

        return main_packages

    def _get_package_status(
        self, name: str, required_version: str, installed_version: str
    ) -> str:
        """Get package status with consistent logic across all views"""
        if required_version:
            if not installed_version:
                return "[red]✗[/red]"  # Most severe: Not installed
            elif required_version.startswith(
                "=="
            ) and installed_version != required_version.lstrip("=="):
                return "[yellow]≠[/yellow]"  # Version mismatch
            return "[green]✓[/green]"  # Installed and matches requirements
        elif installed_version:
            return "[blue]△[/blue]"  # Installed but not in requirements.txt
        return "[red]✗[/red]"  # Not installed

    def list_packages(self, show_all: bool = False, show_deps: bool = False):
        """List packages in requirements.txt and/or all installed packages"""
        req_packages = self._parse_requirements()
        installed_packages = self._get_all_installed_packages()

        # Remove system packages from installed_packages
        for pkg in list(installed_packages.keys()):
            if pkg.lower() in ("pip", "setuptools", "wheel") or pkg.startswith(
                ("pip-", "setuptools-", "wheel-")
            ):
                del installed_packages[pkg]

        if show_deps:
            # For tree view, show only installed main packages
            packages_to_show = {
                name: version
                for name, version in self._get_all_main_packages().items()
                if name in installed_packages
            }
        elif show_all:
            # For -a flag, show only installed packages
            packages_to_show = installed_packages
        else:
            # For default view, show all main packages and requirements.txt
            packages_to_show = self._get_all_main_packages()

        if not packages_to_show:
            console.print("[yellow]No packages found[/yellow]")
            return

        table = Table(
            title="Package Dependencies",
            show_header=True,
            header_style="bold magenta",
            title_justify="left",
            expand=False,
        )

        if show_deps:
            table.add_column("Package Tree", style="cyan", no_wrap=True)
            table.add_column("Required", style="blue")
            table.add_column("Installed", style="cyan")
            table.add_column("Status", justify="right")
        else:
            table.add_column("Package", style="cyan")
            table.add_column("Required", style="blue")
            table.add_column("Installed", style="cyan")
            table.add_column("Status", justify="right")

        def format_tree(tree: dict, level: int = 0) -> list:
            """Format dependency tree for display"""
            rows = []
            prefix = "│   " * (level - 1) + "├── " if level > 0 else ""
            for pkg, subtree in tree.items():
                # Only include installed packages in the tree
                if pkg in installed_packages:
                    rows.append((pkg, level, prefix))
                    rows.extend(format_tree(subtree, level + 1))
            return rows

        if show_deps:
            # Build and display dependency trees for each root package
            main_packages = self._get_all_main_packages()
            for name in sorted(main_packages.keys()):
                if name not in installed_packages:
                    continue  # Skip uninstalled packages

                tree = {name: self._build_dependency_tree(name)}
                formatted_tree = format_tree(tree)

                if (
                    formatted_tree
                ):  # Only show trees that have installed packages
                    for pkg, level, prefix in formatted_tree:
                        pkg_required = req_packages.get(pkg, "")
                        pkg_installed = installed_packages.get(pkg)
                        pkg_status = self._get_package_status(
                            pkg, pkg_required, pkg_installed
                        )

                        display_name = f"{prefix}{pkg}" if level > 0 else pkg
                        # For dependencies (level > 0), only show version info
                        required_display = (
                            pkg_required.lstrip("=")
                            if pkg_required
                            else "[yellow]None[/yellow]" if level == 0 else ""
                        )
                        # Make dependencies dimmed
                        if level > 0:
                            display_name = f"[dim]{display_name}[/dim]"
                            if pkg_installed:
                                pkg_installed = f"[dim]{pkg_installed}[/dim]"
                            pkg_status = f"[dim]{pkg_status}[/dim]"

                        table.add_row(
                            display_name,
                            required_display,
                            pkg_installed or "[yellow]None[/yellow]",
                            pkg_status,
                        )

                    # Add a blank row between trees if there are more trees to come
                    if (
                        name
                        != sorted(
                            [
                                p
                                for p in main_packages.keys()
                                if p in installed_packages
                            ]
                        )[-1]
                    ):
                        table.add_row("", "", "", "")
        else:
            # Original flat list display
            for name, version in sorted(packages_to_show.items()):
                required_version = req_packages.get(name, "")
                installed_version = installed_packages.get(name)

                if (
                    show_all
                    and not required_version
                    and name.startswith(("pip-", "pip", "setuptools", "wheel"))
                ):
                    continue

                status = self._get_package_status(
                    name, required_version, installed_version
                )

                table.add_row(
                    name,
                    (
                        required_version.lstrip("=")
                        if required_version
                        else "[yellow]None[/yellow]"
                    ),
                    installed_version or "[yellow]None[/yellow]",
                    status,
                )

        console.print("\n")
        console.print(table)
        console.print(
            "\nStatus: "
            "[green]✓[/green] Installed and in requirements.txt  "
            "[red]✗[/red] Not installed (severe)  "
            "[yellow]≠[/yellow] Version mismatch  "
            "[blue]△[/blue] Not in requirements.txt\n"
        )
