# Package dependency analysis functionality
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict
from importlib.metadata import distribution, distributions, PackageNotFoundError
import importlib.metadata

from .exceptions import DependencyError
from .package import PackageManager
from .utils import normalize_package_name
from ..ui import console


class DependencyNode:
    """Represents a node in dependency tree."""

    def __init__(self, name: str, version: Optional[str] = None):
        """
        Initialize dependency node.

        Args:
            name: Package name
            version: Optional version constraint
        """
        self.name = name
        self.version = version
        self.children: List[DependencyNode] = []
        self._visited = set()

    def add_child(self, node: "DependencyNode") -> None:
        """Add child node."""
        if node.name not in self._visited:
            self._visited.add(node.name)
            self.children.append(node)

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "dependencies": [child.to_dict() for child in self.children],
        }


class DependencyAnalyzer:
    """Analyzes package dependencies and relationships."""

    def __init__(self, pkg_manager):
        self._pkg_manager = pkg_manager
        self._processed_deps = set()  # Track processed dependencies

    def build_dependency_tree(
        self,
        package: str,
        level: int = 0,
        processed_deps: Optional[Set[str]] = None,
    ) -> Dict:
        """Build dependency tree for a package.

        Args:
            package: Package name to analyze
            level: Current depth level in tree
            processed_deps: Set of already processed dependencies

        Returns:
            Dictionary containing package info and dependencies
        """
        if processed_deps is None:
            processed_deps = set()

        try:
            # Get installed packages
            installed_packages = self._pkg_manager.list_installed(
                top_level_only=False
            )

            # Get package metadata
            try:
                dist = importlib.metadata.distribution(package)
                package_name = dist.metadata["Name"]  # Get original name
                installed_version = installed_packages.get(package_name)
            except Exception:
                package_name = package
                installed_version = None

            # Get normalized name for dependency tracking
            normalized_name = normalize_package_name(package_name)

            # Get package dependencies
            dependencies = self._pkg_manager._get_package_dependencies(
                normalized_name
            )

            # Create package info
            package_info = {
                "name": package_name,  # Use original name from metadata
                "installed_version": installed_version,
                "required_version": None,  # We'll add this later when comparing with requirements.txt
                "level": level,
                "dependencies": [],
            }

            # Process dependencies if not already processed
            if normalized_name not in processed_deps:
                processed_deps.add(normalized_name)

                for dep in dependencies:
                    # Parse dependency name and version
                    if "==" in dep:
                        dep_name, dep_version = dep.split("==")
                    else:
                        dep_name = dep
                        dep_version = None

                    # Get normalized name for dependency
                    dep_normalized = normalize_package_name(dep_name)
                    # If dependency was already processed, mark it as repeated
                    if dep_normalized in processed_deps:
                        package_info["dependencies"].append(
                            {
                                "name": dep_name,
                                "installed_version": dep_version,
                                "required_version": None,
                                "level": level + 1,
                                "repeated": True,
                            }
                        )
                    else:
                        # Recursively build tree for new dependencies
                        dep_info = self.build_dependency_tree(
                            dep_name, level + 1, processed_deps
                        )
                        package_info["dependencies"].append(dep_info)

            return package_info

        except Exception as e:
            console.warning(
                f"Failed to analyze dependencies for {package}: {str(e)}"
            )
            return {
                "name": package,
                "installed_version": None,
                "required_version": None,
                "level": level,
                "dependencies": [],
                "error": str(e),
            }

    def format_tree(
        self,
        node: DependencyNode,
        prefix: str = "",
        is_last: bool = True,
    ) -> str:
        """
        Format dependency tree as string.

        Args:
            node: Root node
            prefix: Line prefix for formatting
            is_last: Whether this is the last node in current level

        Returns:
            Formatted tree string
        """
        # Choose the appropriate branch characters
        branch = "└── " if is_last else "├── "
        indent = "    " if is_last else "│   "

        # Format current node
        version = f" ({node.version})" if node.version else ""
        result = [f"{prefix}{branch}{node.name}{version}"]

        # Format children
        for i, child in enumerate(node.children):
            is_last_child = i == len(node.children) - 1
            result.append(
                self.format_tree(
                    child,
                    prefix + indent,
                    is_last_child,
                )
            )

        return "\n".join(result)

    def get_dependencies(
        self,
        package: str,
        recursive: bool = False,
        include_versions: bool = False,
    ) -> Dict[str, Set[str]]:
        """
        Get package dependencies.

        Args:
            package: Package name
            recursive: Whether to get recursive dependencies
            include_versions: Whether to include version constraints

        Returns:
            Dictionary mapping packages to their dependencies

        Raises:
            DependencyError: If getting dependencies fails
        """
        try:
            dependencies = {}
            visited = set()

            def _get_deps(pkg: str) -> None:
                if pkg in visited:
                    return

                visited.add(pkg)
                pkg_deps = set()

                try:
                    info = self._pkg_manager.get_package_info(pkg)
                    requires = info.get("requires", "")

                    if requires:
                        for dep in requires.split(","):
                            dep = dep.split(";")[0].strip()  # Remove markers
                            if include_versions:
                                pkg_deps.add(dep)
                            else:
                                pkg_deps.add(dep.split()[0])

                            if recursive:
                                _get_deps(dep.split()[0])

                except Exception:
                    console.warning(f"Failed to get dependencies for {pkg}")

                dependencies[pkg] = pkg_deps

            _get_deps(package)
            return dependencies

        except Exception as e:
            raise DependencyError(
                f"Failed to analyze dependencies for {package}",
                details=str(e),
            )

    def find_reverse_dependencies(self, package: str) -> Dict[str, Set[str]]:
        """
        Find packages that depend on the given package.

        Args:
            package: Package name

        Returns:
            Dictionary mapping packages to their dependents

        Raises:
            DependencyError: If finding reverse dependencies fails
        """
        try:
            reverse_deps = defaultdict(set)
            installed = self._pkg_manager.list_installed()

            for pkg in installed:
                deps = self.get_dependencies(pkg)
                for dep_pkg, dep_set in deps.items():
                    for dep in dep_set:
                        dep_name = dep.split()[0]  # Remove version
                        if normalize_package_name(
                            dep_name
                        ) == normalize_package_name(package):
                            reverse_deps[package].add(pkg)

            return dict(reverse_deps)

        except Exception as e:
            raise DependencyError(
                f"Failed to find reverse dependencies for {package}",
                details=str(e),
            )

    def check_conflicts(self) -> List[Tuple[str, str, str]]:
        """
        Check for dependency conflicts.

        Returns:
            List of (package, dependency, conflict) tuples

        Raises:
            DependencyError: If checking conflicts fails
        """
        try:
            conflicts = []
            installed = self._pkg_manager.list_installed()

            # Build dependency graph
            deps_graph = {}
            for pkg in installed:
                deps = self.get_dependencies(pkg, include_versions=True)
                deps_graph.update(deps)

            # Check for conflicts
            for pkg, deps in deps_graph.items():
                for dep in deps:
                    try:
                        # Parse package name and version
                        dep = dep.split(";")[0].strip()  # Remove markers
                        dep_name = dep.split()[0]
                        dep_version = None
                        if " " in dep:
                            dep_version = dep.split(" ", 1)[1]

                        # Check if installed version matches requirement
                        if dep_name in installed:
                            current_version = installed[dep_name]
                            if dep_version and current_version != dep_version:
                                conflicts.append((pkg, dep, current_version))

                    except Exception:
                        continue

            return conflicts

        except Exception as e:
            raise DependencyError(
                "Failed to check dependency conflicts",
                details=str(e),
            )

    def analyze_impact(self, package: str) -> Dict[str, List[str]]:
        """
        Analyze impact of removing a package.

        Args:
            package: Package name

        Returns:
            Dictionary with analysis results

        Raises:
            DependencyError: If impact analysis fails
        """
        try:
            analysis = {
                "direct_dependents": [],
                "indirect_dependents": [],
                "safe_to_remove": True,
            }

            # Find reverse dependencies
            reverse_deps = self.find_reverse_dependencies(package)
            direct_deps = reverse_deps.get(package, set())

            if direct_deps:
                analysis["direct_dependents"] = sorted(direct_deps)
                analysis["safe_to_remove"] = False

                # Find indirect dependencies
                for dep in direct_deps:
                    indirect = self.find_reverse_dependencies(dep)
                    for pkg_set in indirect.values():
                        analysis["indirect_dependents"].extend(
                            pkg
                            for pkg in pkg_set
                            if pkg not in direct_deps and pkg != package
                        )

                analysis["indirect_dependents"] = sorted(
                    set(analysis["indirect_dependents"])
                )

            return analysis

        except Exception as e:
            raise DependencyError(
                f"Failed to analyze impact of removing {package}",
                details=str(e),
            )

    def find_cycles(self) -> List[List[str]]:
        """
        Find dependency cycles.

        Returns:
            List of dependency cycles found

        Raises:
            DependencyError: If finding cycles fails
        """
        try:
            cycles = []
            installed = self._pkg_manager.list_installed()

            # Build dependency graph
            graph = defaultdict(set)
            for pkg in installed:
                deps = self.get_dependencies(pkg)
                for dep_set in deps.values():
                    for dep in dep_set:
                        dep_name = dep.split()[0]
                        if dep_name in installed:
                            graph[pkg].add(dep_name)

            # Find cycles using DFS
            def _find_cycles(
                node: str,
                visited: Set[str],
                path: List[str],
                start: str,
            ) -> None:
                if node in visited:
                    if node == start and len(path) > 2:
                        cycles.append(path[:])
                    return

                visited.add(node)
                path.append(node)

                for neighbor in graph[node]:
                    _find_cycles(neighbor, visited.copy(), path[:], start)

            # Check each node
            for pkg in installed:
                _find_cycles(pkg, set(), [], pkg)

            return [cycle for cycle in cycles if len(cycle) > 2]

        except Exception as e:
            raise DependencyError(
                "Failed to find dependency cycles",
                details=str(e),
            )
