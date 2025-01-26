"""Package management for virtual environments"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from ..ui.console import progress_status, print_error


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

        # 2. Check existing packages and conflicts
        existing = self._get_installed_packages()
        conflicts = self._check_conflicts(package_specs, existing)
        if conflicts:
            for conflict in conflicts:
                results[conflict["package"]] = {
                    "status": "conflict",
                    "message": f"Version conflict: {conflict['requested']} requested, {conflict['installed']} installed",
                }
            return results

        # 3. Check dependencies
        dependencies = {}
        for name, version in package_specs:
            try:
                deps = self._check_dependencies(name, version)
                dependencies[name] = deps
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "message": f"Failed to check dependencies: {str(e)}",
                }
                return results

        # 4. Install packages
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

                # Execute installation
                subprocess.run(cmd, check=True, capture_output=True, text=True)

                results[name] = {
                    "status": "installed",
                    "version": version or self._get_installed_version(name),
                    "dependencies": dependencies.get(name, []),
                }
            except subprocess.CalledProcessError as e:
                results[name] = {"status": "error", "message": e.stderr}
            except Exception as e:
                results[name] = {"status": "error", "message": str(e)}

        # 5. Update requirements.txt
        if any(r["status"] == "installed" for r in results.values()):
            try:
                self._update_requirements(
                    added=[
                        f"{name}=={results[name]['version']}"
                        for name, result in results.items()
                        if result["status"] == "installed"
                    ],
                    dev=dev,
                )
            except Exception as e:
                print_error(f"Failed to update requirements.txt: {str(e)}")

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

        # 1. Check if packages exist
        existing = self._get_installed_packages()
        for pkg in packages:
            if pkg not in existing:
                results[pkg] = {
                    "status": "not_found",
                    "message": "Package not installed",
                }
                continue

            # 2. Check if package is a dependency
            try:
                is_dep, dependents = self._is_dependency(pkg)
                if is_dep:
                    results[pkg] = {
                        "status": "error",
                        "message": f"Package is a dependency of: {', '.join(dependents)}",
                    }
                    continue

                # 3. Remove package
                cmd = [str(self._pip_path), "uninstall", "-y", pkg]
                subprocess.run(cmd, check=True, capture_output=True, text=True)

                results[pkg] = {"status": "removed", "version": existing[pkg]}
            except subprocess.CalledProcessError as e:
                results[pkg] = {"status": "error", "message": e.stderr}
            except Exception as e:
                results[pkg] = {"status": "error", "message": str(e)}

        # 4. Update requirements.txt
        if any(r["status"] == "removed" for r in results.values()):
            try:
                self._update_requirements(
                    removed=[
                        name
                        for name, result in results.items()
                        if result["status"] == "removed"
                    ]
                )
            except Exception as e:
                print_error(f"Failed to update requirements.txt: {str(e)}")

        return results

    def _parse_package_spec(self, spec: str) -> Tuple[str, Optional[str]]:
        """Parse package specification into name and version"""
        if "==" in spec:
            name, version = spec.split("==")
            return name.strip(), version.strip()
        return spec.strip(), None

    def _get_installed_packages(self) -> Dict[str, str]:
        """Get dict of installed packages and their versions"""
        try:
            cmd = [str(self._pip_path), "list", "--format=json"]
            output = subprocess.run(
                cmd, check=True, capture_output=True, text=True
            )
            packages = eval(output.stdout)  # Safe as we control the input
            return {pkg["name"]: pkg["version"] for pkg in packages}
        except Exception as e:
            raise RuntimeError(f"Failed to get installed packages: {str(e)}")

    def _get_installed_version(self, package: str) -> Optional[str]:
        """Get installed version of a package"""
        packages = self._get_installed_packages()
        return packages.get(package)

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

    def _check_dependencies(
        self, package: str, version: Optional[str] = None
    ) -> List[str]:
        """Check package dependencies"""
        try:
            cmd = [str(self._pip_path), "show", package]
            if version:
                cmd[-1] = f"{package}=={version}"
            output = subprocess.run(
                cmd, check=True, capture_output=True, text=True
            )

            # Parse dependencies from output
            deps = []
            for line in output.stdout.split("\n"):
                if line.startswith("Requires:"):
                    deps = [d.strip() for d in line[9:].split(",") if d.strip()]
                    break
            return deps
        except subprocess.CalledProcessError:
            # Package not found or version doesn't exist
            return []
        except Exception as e:
            raise RuntimeError(f"Failed to check dependencies: {str(e)}")

    def _is_dependency(self, package: str) -> Tuple[bool, List[str]]:
        """Check if package is a dependency of other packages"""
        try:
            cmd = [str(self._pip_path), "list", "--format=json"]
            output = subprocess.run(
                cmd, check=True, capture_output=True, text=True
            )
            packages = eval(output.stdout)  # Safe as we control the input

            dependents = []
            for pkg in packages:
                deps = self._check_dependencies(pkg["name"])
                if package in deps:
                    dependents.append(pkg["name"])

            return bool(dependents), dependents
        except Exception as e:
            raise RuntimeError(
                f"Failed to check if package is a dependency: {str(e)}"
            )

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
