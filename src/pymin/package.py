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
from rich.style import Style
from .utils import get_current_shell

console = Console()


class PackageManager:
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.requirements_file = self.project_root / "requirements.txt"
        self._installed_packages_cache = None
        self._dependencies_cache = {}

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
            # Reset caches when removing package
            self._installed_packages_cache = None
            self._dependencies_cache = {}
            console.print(f"[green]✓ Removed {package}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error removing {package}:[/red]\n{str(e)}")
            return False

    def _get_all_installed_packages(self) -> Dict[str, str]:
        """Get all installed packages and their versions"""
        if self._installed_packages_cache is not None:
            return self._installed_packages_cache

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
        except Exception as e:
            # Fallback to pkg_resources if pip list fails
            console.print(
                f"[yellow]Warning: Falling back to pkg_resources: {e}[/yellow]"
            )
            for dist in pkg_resources.working_set:
                packages[dist.key] = dist.version

        self._installed_packages_cache = packages
        return packages

    def _get_package_dependencies(self, package: str) -> Dict[str, list]:
        """Get package dependencies using pkg_resources"""
        if package in self._dependencies_cache:
            return self._dependencies_cache[package]

        try:
            dist = pkg_resources.get_distribution(package)
            deps = {
                "requires": [req.project_name for req in dist.requires()],
                "required_by": [],
            }
            self._dependencies_cache[package] = deps
            return deps
        except Exception:
            empty_deps = {"requires": [], "required_by": []}
            self._dependencies_cache[package] = empty_deps
            return empty_deps

    def _get_all_main_packages(self) -> Dict[str, str]:
        """Get all installed main packages (not dependencies) and their versions"""
        installed = self._get_all_installed_packages()
        main_packages = {}

        # First, add all packages from requirements.txt
        req_packages = self._parse_requirements()
        for pkg in req_packages:
            main_packages[pkg] = installed.get(pkg, "")

        # Get directly installed packages using pip
        try:
            result = subprocess.run(
                ["pip", "list", "--not-required", "--format=json"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                import json

                for pkg in json.loads(result.stdout):
                    name = pkg["name"]
                    # Skip system packages
                    if name.lower() in (
                        "pip",
                        "setuptools",
                        "wheel",
                    ) or name.startswith(("pip-", "setuptools-", "wheel-")):
                        continue
                    # Add if not already in main_packages
                    if name not in main_packages:
                        main_packages[name] = pkg["version"]
        except Exception as e:
            # If pip list fails, try to get non-dependency packages using pkg_resources
            try:
                # Get all dependencies
                all_deps = set()
                for dist in pkg_resources.working_set:
                    if not (
                        dist.key.lower() in ("pip", "setuptools", "wheel")
                        or dist.key.startswith(
                            ("pip-", "setuptools-", "wheel-")
                        )
                    ):
                        for req in dist.requires():
                            all_deps.add(req.project_name)

                # Add packages that are not dependencies
                for dist in pkg_resources.working_set:
                    name = dist.key
                    if (
                        name not in main_packages
                        and name not in all_deps
                        and not (
                            name.lower() in ("pip", "setuptools", "wheel")
                            or name.startswith(
                                ("pip-", "setuptools-", "wheel-")
                            )
                        )
                    ):
                        main_packages[name] = dist.version
            except Exception as e2:
                console.print(
                    f"[yellow]Warning: Could not get direct dependencies: {e2}[/yellow]"
                )

        return main_packages

    def _get_original_package_name(self, name: str) -> str:
        """Get original package name from pip list"""
        try:
            result = subprocess.run(
                ["pip", "list", "--format=json"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                import json

                for pkg in json.loads(result.stdout):
                    if pkg["name"].lower() == name.lower():
                        return pkg["name"]
        except Exception:
            pass
        return name

    def _normalize_package_name(self, name: str) -> str:
        """Normalize package name for comparison (convert to lowercase and replace hyphens with underscores)"""
        return name.lower().replace("-", "_")

    def _get_canonical_package_name(self, name: str) -> str:
        """Get the canonical package name from pip list"""
        normalized_name = self._normalize_package_name(name)
        try:
            if self._installed_packages_cache is None:
                result = subprocess.run(
                    ["pip", "list", "--format=json"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    import json

                    self._installed_packages_cache = {
                        pkg["name"]: pkg["version"]
                        for pkg in json.loads(result.stdout)
                    }

            # Find the package name with correct casing and format
            for pkg_name in self._installed_packages_cache:
                if self._normalize_package_name(pkg_name) == normalized_name:
                    return pkg_name
        except Exception:
            pass
        return name

    def _build_dependency_tree(self, package: str, seen=None) -> dict:
        """Build a dependency tree for a package"""
        if seen is None:
            seen = set()

        normalized_package = self._normalize_package_name(package)
        if normalized_package in {
            self._normalize_package_name(p) for p in seen
        }:
            return {}  # Prevent circular dependencies

        seen.add(package)
        tree = {}

        try:
            # Get dependencies using pip show
            result = subprocess.run(
                ["pip", "show", package],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                # Parse dependencies from pip show output
                for line in result.stdout.split("\n"):
                    if line.startswith("Requires:"):
                        deps = [
                            dep.strip()
                            for dep in line.replace("Requires:", "")
                            .strip()
                            .split(",")
                            if dep.strip()
                        ]
                        for dep in deps:
                            normalized_dep = self._normalize_package_name(dep)
                            if normalized_dep not in {
                                self._normalize_package_name(p) for p in seen
                            }:
                                # Get canonical package name
                                canonical_name = (
                                    self._get_canonical_package_name(dep)
                                )
                                tree[canonical_name] = (
                                    self._build_dependency_tree(
                                        canonical_name, seen
                                    )
                                )
                        break
        except Exception:
            pass

        return tree

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

    def list_packages(
        self,
        show_all: bool = False,
        show_deps: bool = False,
        fix: bool = False,
        auto_fix: bool = False,
    ):
        """List packages in requirements.txt and/or all installed packages"""
        # Check virtual environment status
        venv_active = bool(os.environ.get("VIRTUAL_ENV"))
        current_venv = Path("env")
        current_venv_exists = current_venv.exists() and current_venv.is_dir()

        if not venv_active:
            console.print(
                "\n[red bold]⚠ Warning: No active virtual environment![/red bold]"
            )
            if current_venv_exists:
                console.print(
                    "[yellow]A virtual environment exists but is not activated.[/yellow]"
                )
                # 建構原本的指令參數
                cmd_args = ["pm", "list"]
                if show_all:
                    cmd_args.append("-a")
                if show_deps:
                    cmd_args.append("-t")
                if fix:
                    cmd_args.append("--fix")
                if auto_fix:
                    cmd_args.append("-f")
                cmd = " ".join(cmd_args)

                if Confirm.ask(
                    f"\n[yellow]Do you want to activate the environment and run '[cyan]{cmd}[/cyan]'?[/yellow]"
                ):
                    shell, shell_name = get_current_shell()
                    activate_script = current_venv / "bin" / "activate"
                    os.execl(
                        shell,
                        shell_name,
                        "-c",
                        f"source {activate_script} && {cmd} && exec {shell_name}",
                    )
                    return
            else:
                console.print(
                    "[yellow]No virtual environment found in current directory.[/yellow]"
                )
                console.print("[yellow]Run: pm venv[/yellow]")
                return

        if fix:
            return self.fix_packages(auto_fix)

        req_packages = self._parse_requirements()
        installed_packages = self._get_all_installed_packages()

        # Convert package names to canonical form
        req_packages = {
            self._get_canonical_package_name(name): version
            for name, version in req_packages.items()
        }
        installed_packages = {
            self._get_canonical_package_name(name): version
            for name, version in installed_packages.items()
        }

        # Get main packages
        if show_deps:
            packages_to_show = self._get_all_main_packages()
        elif show_all:
            packages_to_show = {
                name: version
                for name, version in installed_packages.items()
                if not (
                    name.lower() in ("pip", "setuptools", "wheel")
                    or name.startswith(("pip-", "setuptools-", "wheel-"))
                )
            }
        else:
            packages_to_show = self._get_all_main_packages()

        # Convert packages_to_show to canonical form
        packages_to_show = {
            self._get_canonical_package_name(name): version
            for name, version in packages_to_show.items()
        }

        if not packages_to_show:
            console.print("[yellow]No packages found[/yellow]")
            return

        # Create table
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

            # Build all trees at once with progress bar
            trees = {}
            package_list = sorted(packages_to_show.keys())
            with console.status(
                "[yellow]Building dependency tree...[/yellow]",
                spinner="dots",
            ) as status:
                # Build trees
                for i, name in enumerate(package_list):
                    status.update(
                        f"[yellow]Building dependency tree... ({i + 1}/{len(package_list)})[/yellow]"
                    )
                    if name in installed_packages:
                        trees[name] = self._build_dependency_tree(name)
                    elif (
                        name in req_packages
                    ):  # Add uninstalled but required packages
                        trees[name] = {}

                # Format trees with progress indicator
                status.update("[yellow]Formatting dependency tree...[/yellow]")
                for name in sorted(trees.keys()):

                    def format_tree(
                        pkg: str,
                        tree: dict,
                        level: int = 0,
                        last_sibling=True,
                        prefix="",
                    ) -> None:
                        # Get package information
                        pkg_required = req_packages.get(pkg, "")
                        pkg_installed = installed_packages.get(pkg)
                        pkg_status = self._get_package_status(
                            pkg, pkg_required, pkg_installed
                        )

                        # Create tree branches
                        if level > 0:
                            branch = "└── " if last_sibling else "├── "
                            display_name = f"{prefix}{branch}{pkg}"
                            if tree.get("circular"):
                                display_name += " [dim](circular)[/dim]"
                        else:
                            display_name = pkg

                        # Format display values
                        required_display = (
                            pkg_required.lstrip("=")
                            if pkg_required
                            else "[yellow]None[/yellow]" if level == 0 else ""
                        )

                        # Dim the display for dependencies
                        if level > 0:
                            display_name = f"[dim]{display_name}[/dim]"
                            if pkg_installed:
                                pkg_installed = f"[dim]{pkg_installed}[/dim]"
                            pkg_status = f"[dim]{pkg_status}[/dim]"

                        # Add row to table
                        table.add_row(
                            display_name,
                            required_display,
                            pkg_installed or "[yellow]None[/yellow]",
                            pkg_status,
                        )

                        # Process dependencies recursively
                        if not tree.get("circular"):
                            deps = [
                                (k, v)
                                for k, v in sorted(tree.items())
                                if k != "circular"
                            ]
                            for i, (dep, subtree) in enumerate(deps):
                                new_prefix = prefix + (
                                    "    " if last_sibling else "│   "
                                )
                                # Get sub-dependencies if not already in tree
                                if not subtree and dep in installed_packages:
                                    subtree = self._build_dependency_tree(dep)
                                format_tree(
                                    dep,
                                    subtree,
                                    level + 1,
                                    i == len(deps) - 1,
                                    new_prefix,
                                )

                    format_tree(name, trees[name])
                    if name != sorted(trees.keys())[-1]:
                        table.add_row("", "", "", "")
        else:
            table.add_column("Package", style="")
            table.add_column("Required", style="blue")
            table.add_column("Installed", style="cyan")
            table.add_column("Status", justify="right")

            # Get main packages for checking
            main_packages = self._get_all_main_packages()

            for name in sorted(packages_to_show.keys()):
                required_version = req_packages.get(name, "")
                installed_version = installed_packages.get(name)
                status = self._get_package_status(
                    name, required_version, installed_version
                )

                # Dim the display if it's not a main package
                if name not in main_packages:
                    name = f"[dim]{name}[/dim]"
                    if installed_version:
                        installed_version = f"[dim]{installed_version}[/dim]"
                    status = f"[dim]{status}[/dim]"

                table.add_row(
                    name,
                    (
                        required_version.lstrip("=")
                        if required_version
                        else ("" if show_all else "[yellow]None[/yellow]")
                    ),
                    installed_version or "[yellow]None[/yellow]",
                    status,
                )
        console.print(table)

    def fix_packages(self, auto_fix: bool = False) -> bool:
        """Fix package inconsistencies:
        1. Install missing packages from requirements.txt
        2. Add installed packages to requirements.txt
        3. Fix version mismatches
        """
        req_packages = self._parse_requirements()
        installed_packages = self._get_all_installed_packages()
        fixed = False

        # Group issues by type
        missing_packages = []  # in requirements.txt but not installed
        unlisted_packages = []  # installed but not in requirements.txt
        version_mismatches = []  # version doesn't match requirements.txt

        for name, req_version in req_packages.items():
            if name not in installed_packages:
                missing_packages.append((name, req_version.lstrip("==")))
            elif req_version and installed_packages[name] != req_version.lstrip(
                "=="
            ):
                version_mismatches.append(
                    (name, req_version.lstrip("=="), installed_packages[name])
                )

        # Get directly installed packages using pip
        try:
            result = subprocess.run(
                ["pip", "list", "--not-required", "--format=json"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                import json

                for pkg in json.loads(result.stdout):
                    name = pkg["name"]
                    if name not in req_packages and not (
                        name.lower() in ("pip", "setuptools", "wheel")
                        or name.startswith(("pip-", "setuptools-", "wheel-"))
                    ):
                        unlisted_packages.append((name, pkg["version"]))
        except Exception:
            pass

        # Display issues
        if not (missing_packages or unlisted_packages or version_mismatches):
            console.print("[green]No package inconsistencies found[/green]")
            return True

        if missing_packages:
            console.print("\n[red]Missing packages:[/red]")
            for name, version in missing_packages:
                text = Text()
                text.append("  ", style=Style(color="red"))
                text.append("✗", style=Style(color="red"))
                text.append(" ")
                text.append(f"{name}=={version}", style=Style())
                console.print(text)

        if unlisted_packages:
            console.print("\nPackages not in requirements.txt:")
            for name, version in unlisted_packages:
                text = Text()
                text.append("  ", style=Style(color="blue"))
                text.append("△", style=Style(color="blue"))
                text.append(" ")
                text.append(f"{name}=={version}", style=Style())
                console.print(text)

        if version_mismatches:
            console.print("\nVersion mismatches:")
            for name, req_version, inst_version in version_mismatches:
                text = Text()
                text.append("  ", style=Style(color="yellow"))
                text.append("≠", style=Style(color="yellow"))
                text.append(" ")
                text.append(name, style=Style())
                text.append(": required==")
                text.append(req_version)
                text.append(", installed==")
                text.append(inst_version, style=Style(color="red"))
                console.print(text)

        # Show summary of actions
        console.print("\nSummary of actions to be taken:")
        if missing_packages:
            console.print(
                f"  • Install {len(missing_packages)} missing package(s)"
            )
        if version_mismatches:
            console.print(
                f"  • Update {len(version_mismatches)} package version(s)"
            )
        if unlisted_packages:
            console.print(
                f"  • Add {len(unlisted_packages)} package(s) to requirements.txt"
            )

        # Auto-fix or ask for confirmation
        if not auto_fix:
            if not Confirm.ask("\nDo you want to fix these issues?"):
                return False

        # Fix missing packages
        for name, version in missing_packages:
            console.print(f"\n[dim]Installing {name}=={version}...[/dim]")
            if self.add(name, version):
                fixed = True

        # Fix version mismatches
        for name, req_version, _ in version_mismatches:
            console.print(f"\n[dim]Updating {name} to {req_version}...[/dim]")
            if self.add(name, req_version):
                fixed = True

        # Add unlisted packages to requirements.txt
        if unlisted_packages:
            packages = self._parse_requirements()
            for name, version in unlisted_packages:
                packages[name] = f"=={version}"
            self._write_requirements(packages)
            console.print("\n[green]✓ Updated requirements.txt[/green]")
            fixed = True

        if fixed:
            console.print("\n[green]✓ All issues have been fixed[/green]")
        return fixed
