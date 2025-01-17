# Package management functionality
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import sys
import importlib
import importlib.metadata
from packaging.requirements import Requirement

from .exceptions import PackageError
from .utils import normalize_package_name
from ..ui import console


class PackageManager:
    """Manages Python package operations."""

    def __init__(self, venv_path: Optional[Path] = None):
        """
        Initialize package manager.

        Args:
            venv_path: Optional virtual environment path
        """
        self.venv_path = venv_path
        self._installed_packages_cache = None
        self._dependencies_cache = {}

        # Switch to virtual environment if exists
        if venv_path and venv_path.exists():
            try:
                self._switch_virtual_env(str(venv_path))
            except Exception as e:
                raise PackageError(
                    "Failed to switch virtual environment",
                    details=str(e),
                )

    def _switch_virtual_env(self, venv_path: str) -> None:
        """Switch to specified virtual environment."""
        # Handle different platform paths
        bin_dir = "Scripts" if sys.platform == "win32" else "bin"
        python_path = Path(venv_path) / bin_dir / "python"
        if not python_path.exists() and sys.platform == "win32":
            python_path = python_path.with_suffix(".exe")

        if not python_path.exists():
            raise ValueError(f"Python executable not found: {python_path}")

        # Get site-packages path
        site_packages = self._get_venv_site_packages(str(python_path))
        if not Path(site_packages).exists():
            raise ValueError(
                f"Site-packages directory not found: {site_packages}"
            )

        # Update PYTHONPATH environment variable
        import os

        os.environ["PYTHONPATH"] = site_packages

        # Remove all existing site-packages from sys.path
        sys.path = [p for p in sys.path if "site-packages" not in p]

        # Add the virtual environment's site-packages at the beginning
        sys.path.insert(0, site_packages)

        # Clear all existing distributions cache
        importlib.metadata.MetadataPathFinder.invalidate_caches()
        importlib.reload(importlib.metadata)

    def _get_venv_site_packages(self, python_path: str) -> str:
        """Get site-packages directory from Python interpreter."""
        import subprocess

        try:
            cmd = [
                python_path,
                "-c",
                "import sysconfig; print(sysconfig.get_path('purelib'))",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Failed to get site-packages path: {e}")

    def _get_system_packages(self) -> Set[str]:
        """Get a set of known system packages that should be excluded."""
        return {
            "pip",
            "setuptools",
            "wheel",
        }

    def _get_package_dependencies(self, package_name: str) -> Set[str]:
        """Get direct dependencies for a package with their versions."""
        if package_name in self._dependencies_cache:
            return self._dependencies_cache[package_name]

        try:
            dist = importlib.metadata.distribution(package_name)
            direct_deps = set()

            if dist.requires:
                for req in dist.requires:
                    try:
                        req_obj = Requirement(req)
                        dep_name = req_obj.name
                        # Only add dependency if it's installed
                        try:
                            dep_dist = importlib.metadata.distribution(dep_name)
                            # Keep original case and add version
                            direct_deps.add(
                                f"{dep_dist.metadata['Name']}=={dep_dist.version}"
                            )
                        except importlib.metadata.PackageNotFoundError:
                            continue
                    except Exception:
                        console.warning(f"Failed to parse requirement: {req}")
                        continue

            self._dependencies_cache[package_name] = direct_deps
            return direct_deps
        except importlib.metadata.PackageNotFoundError:
            self._dependencies_cache[package_name] = set()
            return set()
        except Exception as e:
            console.warning(
                f"Failed to get dependencies for {package_name}: {e}"
            )
            return set()

    def list_installed(
        self,
        top_level_only: bool = False,
    ) -> Dict[str, str]:
        """List installed packages.

        Args:
            top_level_only: Only return top-level packages

        Returns:
            Dictionary mapping package names to versions
        """
        try:
            packages = {}
            all_dependencies = set()

            # Get all installed distributions
            for dist in importlib.metadata.distributions():
                packages[dist.metadata["Name"]] = dist.version
                if not top_level_only:
                    continue

                # Collect all dependencies for top-level filtering
                try:
                    requires = dist.requires or []
                    for req in requires:
                        # Extract the package name from the requirement
                        dep_name = req.split()[0]
                        dep_name = dep_name.split(">")[0]
                        dep_name = dep_name.split("<")[0]
                        dep_name = dep_name.split("=")[0]
                        dep_name = dep_name.split("[")[0]
                        all_dependencies.add(dep_name)
                except Exception as e:
                    console.warning(
                        f"Failed to parse dependencies for {dist.metadata['Name']}: {e}"
                    )

            if top_level_only:
                # A package is top-level if it's not a dependency of any other package
                return {
                    name: version
                    for name, version in packages.items()
                    if name not in all_dependencies
                }

            return packages

        except Exception as e:
            raise PackageError(
                "Failed to list installed packages",
                details=str(e),
            )

    def get_requirements(self) -> Dict[str, str]:
        """
        Get packages from requirements.txt.

        Returns:
            Dictionary mapping package names to version constraints
        """
        try:
            if not self.venv_path:
                return {}

            req_file = self.venv_path.parent / "requirements.txt"
            if not req_file.exists():
                return {}

            reqs = {}
            with open(req_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Handle different requirement formats
                        if "==" in line:
                            name, version = line.split("==")
                            reqs[normalize_package_name(name)] = f"=={version}"
                        elif ">=" in line:
                            name, version = line.split(">=")
                            reqs[normalize_package_name(name)] = f">={version}"
                        elif "<=" in line:
                            name, version = line.split("<=")
                            reqs[normalize_package_name(name)] = f"<={version}"
                        else:
                            reqs[normalize_package_name(line)] = ""
            return reqs

        except Exception as e:
            raise PackageError(
                "Failed to read requirements.txt",
                details=str(e),
            )

    def get_package_tree(self, package_name: str) -> Dict[str, List[str]]:
        """
        Get dependency tree for a package.

        Args:
            package_name: Name of the package

        Returns:
            Dictionary mapping package names to their direct dependencies
        """
        tree = {}
        visited = set()

        def build_tree(pkg: str) -> None:
            if pkg in visited:
                return
            visited.add(pkg)
            deps = self._get_package_dependencies(pkg)
            tree[pkg] = list(deps)
            for dep in deps:
                build_tree(dep)

        build_tree(package_name)
        return tree

    def get_all_packages(self) -> Dict[str, Tuple[str, Optional[str]]]:
        """
        Get all packages with their installed and required versions.

        Returns:
            Dictionary mapping package names to (installed_version, required_version)
        """
        installed = self.list_installed(top_level_only=False)
        required = self.get_requirements()

        all_packages = {}

        # Add installed packages
        for name, version in installed.items():
            all_packages[name] = (version, required.get(name))

        # Add packages that are only in requirements
        for name, version in required.items():
            if name not in all_packages:
                all_packages[name] = (None, version)

        return all_packages

    def debug_package_info(self) -> None:
        """Debug method to check package information."""
        console.print("\n[bold cyan]Debug Package Information[/]")

        # 1. Check installed packages
        console.print("\n[bold]1. All Installed Packages:[/]")
        installed = self.list_installed(top_level_only=False)
        for name, version in installed.items():
            console.print(f"  {name}: {version}")

        # 2. Check requirements
        console.print("\n[bold]2. Requirements.txt Packages:[/]")
        required = self.get_requirements()
        for name, version in required.items():
            console.print(f"  {name}: {version}")

        # 3. Check top-level packages
        console.print("\n[bold]3. Top-level Packages:[/]")
        top_level = self.list_installed(top_level_only=True)
        for name, version in top_level.items():
            console.print(f"  {name}: {version}")

        # 4. Check dependencies for each top-level package
        console.print("\n[bold]4. Dependencies for Top-level Packages:[/]")
        for name in top_level:
            deps = self._get_package_dependencies(name)
            console.print(f"\n  [cyan]{name}[/] depends on:")
            for dep in deps:
                console.print(f"    - {dep}")

        # 5. Check package metadata
        console.print("\n[bold]5. Sample Package Metadata:[/]")
        if top_level:
            sample_pkg = next(iter(top_level))
            try:
                dist = importlib.metadata.distribution(sample_pkg)
                console.print(f"\n  [cyan]{sample_pkg}[/] metadata:")
                console.print(f"    Name: {dist.metadata['Name']}")
                console.print(f"    Version: {dist.version}")
                if dist.requires:
                    console.print("    Requires:")
                    for req in dist.requires:
                        console.print(f"      - {req}")
            except Exception as e:
                console.print(f"  Error getting metadata: {e}")
