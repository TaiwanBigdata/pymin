"""Package management for virtual environments"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from ..ui.console import progress_status, print_error, console
from rich.text import Text
from rich.tree import Tree
from rich.style import Style
from .package_analyzer import PackageAnalyzer


class PackageManager:
    """Package management for virtual environments"""

    def __init__(self, venv_path: Path):
        """Initialize package manager

        Args:
            venv_path: Path to the virtual environment
        """
        self.venv_path = venv_path
        self.requirements_path = Path("requirements.txt")
        self._pip_path = self._get_pip_path()

        # Initialize package analyzer with project root directory
        self.package_analyzer = PackageAnalyzer()

    def _check_pip_upgrade(self, stderr: str) -> None:
        """Check if pip needs upgrade and handle it

        Args:
            stderr: Error output from pip
        """
        if "new version of pip available" in stderr.lower():
            try:
                # Get current and latest version
                current_version = None
                latest_version = None
                for line in stderr.split("\n"):
                    if "new release" in line.lower():
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "->":
                                current_version = parts[i - 1]
                                latest_version = parts[i + 1]
                                break

                if current_version and latest_version:
                    console.print(
                        f"[yellow]⚠ A new version of pip is available: {current_version} -> {latest_version}[/yellow]"
                    )
                    console.print(
                        "[dim]To update, run: pip install --upgrade pip[/dim]"
                    )
            except Exception:
                pass

    def _build_dependency_tree(
        self,
        name: str,
        version: str,
        deps: List[str],
        visited: Optional[Set[str]] = None,
    ) -> Tree:
        """Build a rich Tree structure for package dependencies"""
        if visited is None:
            visited = set()

        # Create tree node
        tree = Tree(
            Text.assemble(
                (name, "cyan"),
                ("==", "dim"),
                (version, "cyan"),
            )
        )

        # Add dependencies
        if deps:
            visited.add(name)
            for dep in sorted(deps):
                if dep not in visited:
                    dep_version = self._get_installed_version(dep)
                    dep_deps = self._check_dependencies(dep)
                    dep_tree = self._build_dependency_tree(
                        dep, dep_version, dep_deps, visited
                    )
                    tree.add(dep_tree)

        return tree

    def add_packages(
        self,
        packages: List[str],
        *,
        dev: bool = False,
        editable: bool = False,
        no_deps: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """Add packages to the virtual environment

        Args:
            packages: List of packages to install, each can include version specifier
            dev: Whether to install as development dependencies
            editable: Whether to install in editable mode
            no_deps: Whether to skip dependencies installation

        Returns:
            Dict with installation results for each package
        """
        results = {}

        # 1. Parse package specifications
        package_specs = [self._parse_package_spec(pkg) for pkg in packages]

        # 2. Install packages one by one
        for name, version in package_specs:
            try:
                # Construct pip command
                cmd = [str(self._pip_path), "install"]
                if editable:
                    cmd.append("-e")
                if no_deps:
                    cmd.append("--no-deps")
                pkg_spec = f"{name}=={version}" if version else name
                cmd.append(pkg_spec)

                # First try: capture output to check for pip upgrade notice
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                # If we get a pip upgrade notice, try again
                if (
                    process.returncode != 0
                    and "new release of pip available" in process.stderr.lower()
                ):
                    self._check_pip_upgrade(process.stderr)
                    # Second try: capture output again
                    process = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True,
                    )

                # If installation was successful
                if (
                    process.returncode == 0
                    or "Successfully installed" in process.stdout
                ):
                    # Get installed version
                    self.package_analyzer.clear_cache()
                    packages_after = (
                        self.package_analyzer.get_installed_packages()
                    )

                    # Try to find the package with case-insensitive matching
                    pkg_name = name.lower()
                    matching_pkg = None
                    for installed_pkg, info in packages_after.items():
                        if installed_pkg.lower() == pkg_name:
                            matching_pkg = installed_pkg
                            pkg_info = info
                            break

                    if matching_pkg:
                        results[matching_pkg] = {
                            "status": "installed",
                            "version": pkg_info["installed_version"],
                            "dependencies": sorted(pkg_info["dependencies"]),
                            "existing_dependencies": [],
                            "new_dependencies": sorted(
                                pkg_info["dependencies"]
                            ),
                        }

                        # Update requirements.txt
                        self._update_requirements(
                            added=[
                                f"{matching_pkg}=={pkg_info['installed_version']}"
                            ],
                            dev=dev,
                        )
                    else:
                        # Try to get the version from pip list
                        try:
                            pip_list = subprocess.run(
                                [str(self._pip_path), "list", "--format=json"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                check=True,
                            )
                            packages_list = eval(
                                pip_list.stdout
                            )  # Safe as we control the input
                            for pkg in packages_list:
                                if pkg["name"].lower() == name.lower():
                                    results[pkg["name"]] = {
                                        "status": "installed",
                                        "version": pkg["version"],
                                        "dependencies": [],
                                        "existing_dependencies": [],
                                        "new_dependencies": [],
                                    }
                                    # Update requirements.txt
                                    self._update_requirements(
                                        added=[
                                            f"{pkg['name']}=={pkg['version']}"
                                        ],
                                        dev=dev,
                                    )
                                    break
                            else:
                                results[name] = {
                                    "status": "error",
                                    "message": "Package not found after installation",
                                }
                        except Exception:
                            results[name] = {
                                "status": "error",
                                "message": "Package not found after installation",
                            }
                else:
                    # Real error occurred
                    results[name] = {
                        "status": "error",
                        "message": process.stderr,
                    }

            except subprocess.CalledProcessError as e:
                results[name] = {
                    "status": "error",
                    "message": e.stderr if e.stderr else str(e),
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "message": str(e),
                }

        return results

    def remove_packages(
        self,
        packages: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Remove packages from the virtual environment

        Args:
            packages: List of packages to remove

        Returns:
            Dict with removal results for each package
        """
        results = {}

        # Clear cache to get fresh package information
        self.package_analyzer.clear_cache()

        # Get package information from analyzer
        installed_packages = self.package_analyzer.get_installed_packages()

        # Create a case-insensitive lookup dictionary using normalized names
        pkg_case_map = {
            self.package_analyzer._normalize_package_name(pkg): pkg
            for pkg in installed_packages.keys()
        }

        # Get all dependencies
        all_dependencies = self._get_all_dependencies()
        packages_to_remove = set()
        dependency_info = {}

        # 1. Check each package
        for pkg in packages:
            # Normalize the package name
            pkg_normalized = self.package_analyzer._normalize_package_name(pkg)

            # Try to find the actual package name with correct case
            actual_pkg_name = pkg_case_map.get(pkg_normalized)

            if not actual_pkg_name:
                results[pkg] = {
                    "status": "not_found",
                    "message": "Package not installed",
                }
                continue

            # Add the main package to removal list
            packages_to_remove.add(actual_pkg_name)

            # Check its dependencies
            pkg_info = installed_packages[actual_pkg_name]
            pkg_deps = pkg_info.get("dependencies", [])
            removable_deps = set()
            kept_deps = set()

            # For each dependency
            for dep in pkg_deps:
                # If dependency exists in installed packages
                if dep in installed_packages:
                    # Check if it's used by other packages
                    other_dependents = all_dependencies.get(dep, set()) - {
                        actual_pkg_name
                    }
                    if not other_dependents:
                        removable_deps.add(dep)
                    else:
                        kept_deps.add(dep)
                        if dep not in dependency_info:
                            dependency_info[dep] = {
                                "kept_for": list(other_dependents)
                            }

            # Store dependency information
            dependency_info[actual_pkg_name] = {
                "removable_deps": list(removable_deps),
                "kept_deps": list(kept_deps),
                **{
                    dep: dependency_info[dep]
                    for dep in kept_deps
                    if dep in dependency_info
                },
            }

        # 2. Remove packages
        for pkg in packages_to_remove:
            try:
                cmd = [str(self._pip_path), "uninstall", "-y", pkg]
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                if process.returncode == 0:
                    pkg_info = installed_packages[pkg]
                    results[pkg] = {
                        "status": "removed",
                        "version": pkg_info["installed_version"],
                        "dependencies": pkg_info["dependencies"],
                        "dependency_info": dependency_info.get(pkg, {}),
                    }

                    # Update requirements.txt
                    self._update_requirements(removed=[pkg])
                else:
                    results[pkg] = {
                        "status": "error",
                        "message": (
                            process.stderr
                            if process.stderr
                            else "Unknown error during uninstallation"
                        ),
                    }

            except Exception as e:
                results[pkg] = {
                    "status": "error",
                    "message": str(e),
                }

        return results

    def _parse_package_spec(self, spec: str) -> Tuple[str, Optional[str]]:
        """Parse package specification into name and version"""
        if "==" in spec:
            name, version = spec.split("==")
            return name.strip(), version.strip()
        return spec.strip(), None

    def _get_installed_packages(self) -> Dict[str, Dict[str, Any]]:
        """Get installed packages and their information

        Returns:
            Dict mapping package names to their information
        """
        return self.package_analyzer.get_installed_packages()

    def _get_all_dependencies(self) -> Dict[str, Set[str]]:
        """Get all packages and their dependents

        Returns:
            Dict mapping package names to sets of packages that depend on them
        """
        packages = self._get_installed_packages()
        dependents = {}

        # Build dependency map
        for pkg_name, pkg_info in packages.items():
            for dep in pkg_info["dependencies"]:
                if dep not in dependents:
                    dependents[dep] = set()
                dependents[dep].add(pkg_name)

        return dependents

    def _get_installed_version(self, package: str) -> Optional[str]:
        """Get installed version of a package

        Args:
            package: Package name

        Returns:
            Version string if installed, None otherwise
        """
        packages = self.package_analyzer.get_installed_packages()
        if package in packages:
            return packages[package]["installed_version"]
        return None

    def _check_conflicts(
        self,
        package_specs: List[Tuple[str, Optional[str]]],
        existing: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Check for version conflicts"""
        conflicts = []
        for name, version in package_specs:
            if name in existing and version and existing[name] != version:
                conflicts.append(
                    {
                        "package": name,
                        "requested": version,
                        "installed": existing[name],
                    }
                )
        return conflicts

    def _check_dependencies(self, package: str) -> List[str]:
        """Get dependencies of a package

        Args:
            package: Package name

        Returns:
            List of dependency names
        """
        packages = self.package_analyzer.get_installed_packages()
        if package in packages:
            return packages[package]["dependencies"]
        return []

    def _is_dependency(self, package: str) -> Tuple[bool, List[str]]:
        """Check if package is a dependency of other packages

        Args:
            package: Package name to check

        Returns:
            Tuple of (is_dependency, list_of_dependent_packages)
        """
        packages = self.package_analyzer.get_installed_packages()
        dependents = []

        for pkg_name, pkg_info in packages.items():
            if pkg_name != package and package in pkg_info["dependencies"]:
                dependents.append(pkg_name)

        return bool(dependents), dependents

    def _update_requirements(
        self,
        added: Optional[List[str]] = None,
        removed: Optional[List[str]] = None,
        dev: bool = False,
    ) -> None:
        """Update requirements.txt file"""
        try:
            # Read existing requirements
            requirements = []
            if self.requirements_path.exists():
                with open(self.requirements_path) as f:
                    requirements = [line.strip() for line in f if line.strip()]

            # Remove packages
            if removed:
                requirements = [
                    r
                    for r in requirements
                    if not any(r.startswith(f"{pkg}==") for pkg in removed)
                ]

            # Add packages
            if added:
                requirements.extend(added)

            # Write back
            with open(self.requirements_path, "w") as f:
                f.write("\n".join(sorted(requirements)) + "\n")
        except Exception as e:
            raise RuntimeError(f"Failed to update requirements.txt: {str(e)}")

    def _get_pip_path(self) -> Path:
        """Get path to pip executable"""
        if sys.platform == "win32":
            pip_path = self.venv_path / "Scripts" / "pip.exe"
        else:
            pip_path = self.venv_path / "bin" / "pip"

        if not pip_path.exists():
            raise RuntimeError(f"pip not found at {pip_path}")

        return pip_path
