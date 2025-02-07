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
from packaging import version
import re


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
        for pkg_name, pkg_version in package_specs:
            try:
                # Construct pip command
                cmd = [str(self._pip_path), "install"]
                if editable:
                    cmd.append("-e")
                if no_deps:
                    cmd.append("--no-deps")
                pkg_spec = (
                    f"{pkg_name}=={pkg_version}" if pkg_version else pkg_name
                )
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
                    pkg_name_lower = pkg_name.lower()
                    matching_pkg = None
                    for installed_pkg, info in packages_after.items():
                        if installed_pkg.lower() == pkg_name_lower:
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
                            packages_list = eval(pip_list.stdout)
                            for pkg in packages_list:
                                if pkg["name"].lower() == pkg_name.lower():
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
                                results[pkg_name] = {
                                    "status": "error",
                                    "message": "Package not found after installation",
                                }
                        except Exception:
                            results[pkg_name] = {
                                "status": "error",
                                "message": "Package not found after installation",
                            }
                else:
                    # Extract available versions from pip error message
                    available_versions = []
                    version_list_started = False

                    for line in process.stderr.split("\n"):
                        if "from versions:" in line:
                            version_list = (
                                line.split("from versions:", 1)[1]
                                .strip("() ")
                                .split(", ")
                            )
                            available_versions = [
                                v.strip() for v in version_list if v.strip()
                            ]
                            break

                    if available_versions:
                        # Sort versions using packaging.version
                        sorted_versions = sorted(
                            available_versions, key=lambda v: version.parse(v)
                        )
                        latest_versions = sorted_versions[-5:]

                        # Find versions close to the requested version
                        if pkg_version:
                            # Get closest available versions
                            close_versions = sorted(
                                sorted_versions,
                                key=lambda v: get_version_distance(
                                    v, pkg_version
                                ),
                            )[:5]

                            # Add version suggestions to error message
                            # Show latest versions in one line
                            latest_ver_list = ", ".join(
                                f"[cyan]{v}[/cyan]"
                                + (
                                    " (latest)"
                                    if v == latest_versions[-1]
                                    else ""
                                )
                                for v in reversed(latest_versions)
                            )

                            # Show similar versions in one line
                            similar_ver_list = ", ".join(
                                f"[cyan]{v}[/cyan]"
                                + (
                                    " (closest)"
                                    if v == close_versions[0]
                                    else ""
                                )
                                for v in close_versions
                            )

                            # Store version information for later use
                            version_info = {
                                "latest_versions": latest_ver_list,
                                "similar_versions": similar_ver_list,
                            }

                            # Show pip upgrade notice if needed
                            if (
                                "new release of pip available"
                                in process.stderr.lower()
                            ):
                                current_ver, latest_ver = (
                                    self._get_pip_versions(process.stderr)
                                )
                                if current_ver and latest_ver:
                                    console.print(
                                        f"\n[yellow]Pip update available:[/yellow] {current_ver} -> {latest_ver}"
                                    )
                                    console.print(
                                        "[dim]Run: pip install --upgrade pip[/dim]"
                                    )

                    results[pkg_name] = {
                        "status": "error",
                        "message": "Version not found",
                        "version_info": (
                            version_info if "version_info" in locals() else None
                        ),
                    }

            except subprocess.CalledProcessError as e:
                results[pkg_name] = {
                    "status": "error",
                    "message": e.stderr if e.stderr else str(e),
                }
            except Exception as e:
                results[pkg_name] = {
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
                # First remove any existing versions of the packages we're adding
                for pkg_spec in added:
                    pkg_name = pkg_spec.split("==")[0]
                    requirements = [
                        r
                        for r in requirements
                        if not r.startswith(f"{pkg_name}==")
                    ]
                # Then add the new versions
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

    def _get_pip_versions(
        self, stderr: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Extract current and latest pip versions from stderr"""
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
        return current_version, latest_version


def _get_pre_release_type_value(pre_type: str) -> int:
    """Get numeric value for pre-release type for ordering"""
    pre_type_order = {"a": 0, "b": 1, "rc": 2}
    return pre_type_order.get(pre_type, 3)


def get_version_distance(ver_str: str, target_str: str) -> float:
    """Calculate distance between two version strings with improved handling of pre-releases"""
    # Parse versions using packaging.version
    ver = version.parse(ver_str)
    target = version.parse(target_str)

    # Get release components
    ver_release = ver.release
    target_release = target.release

    # Pad with zeros to make same length
    max_len = max(len(ver_release), len(target_release))
    ver_parts = list(ver_release) + [0] * (max_len - len(ver_release))
    target_parts = list(target_release) + [0] * (max_len - len(target_release))

    # Calculate weighted distance for release parts
    distance = 0
    for i, (a, b) in enumerate(zip(ver_parts, target_parts)):
        weight = 10 ** (max_len - i - 1)
        distance += abs(a - b) * weight

    # Add pre-release penalty
    pre_release_penalty = 0
    if ver.is_prerelease or target.is_prerelease:
        # Penalize pre-releases but still keep them close to their release version
        pre_release_penalty = 0.5

        # If both are pre-releases, reduce penalty and compare their order
        if ver.is_prerelease and target.is_prerelease:
            pre_release_penalty = 0.25
            # Compare pre-release parts
            if ver.pre and target.pre:
                pre_type_diff = abs(
                    _get_pre_release_type_value(ver.pre[0])
                    - _get_pre_release_type_value(target.pre[0])
                )
                pre_num_diff = abs(ver.pre[1] - target.pre[1])
                pre_release_penalty += (
                    pre_type_diff + pre_num_diff * 0.1
                ) * 0.25

    return distance + pre_release_penalty
