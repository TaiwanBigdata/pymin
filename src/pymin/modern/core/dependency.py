# Package dependency analysis functionality
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict
from importlib.metadata import distribution, distributions, PackageNotFoundError

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

    def __init__(self, venv_path: Optional[Path] = None):
        """
        Initialize dependency analyzer.

        Args:
            venv_path: Optional virtual environment path
        """
        self.venv_path = venv_path
        self._pkg_manager = PackageManager(venv_path)

    def build_dependency_tree(
        self,
        package: str,
        max_depth: Optional[int] = None,
        include_versions: bool = True,
    ) -> DependencyNode:
        """
        Build dependency tree for package.

        Args:
            package: Package name
            max_depth: Maximum depth to traverse
            include_versions: Whether to include version constraints

        Returns:
            Root node of dependency tree

        Raises:
            DependencyError: If building tree fails
        """
        try:
            visited = set()

            def _build_tree(pkg: str, depth: int = 0) -> DependencyNode:
                if pkg in visited:
                    return DependencyNode(pkg, "...")

                if max_depth is not None and depth >= max_depth:
                    return DependencyNode(pkg, "...")

                visited.add(pkg)
                version = None

                try:
                    info = self._pkg_manager.get_package_info(pkg)
                    if include_versions:
                        version = info.get("version")

                    node = DependencyNode(pkg, version)
                    requires = info.get("requires", "")

                    if requires:
                        for dep in requires.split(","):
                            dep = dep.split(";")[0].strip()  # Remove markers
                            dep_name = dep.split()[0]
                            dep_version = None
                            if include_versions and " " in dep:
                                dep_version = dep.split(" ", 1)[1]

                            child = _build_tree(dep_name, depth + 1)
                            if child:
                                node.add_child(child)

                    return node

                except Exception:
                    console.warning(f"Failed to get dependencies for {pkg}")
                    return DependencyNode(pkg, "error")

            return _build_tree(package)

        except Exception as e:
            raise DependencyError(
                f"Failed to build dependency tree for {package}",
                details=str(e),
            )

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

        # Format current node
        version = f" ({node.version})" if node.version else ""
        result = [f"{prefix}{branch}{node.name}{version}"]

        # Prepare prefix for children
        child_prefix = prefix + ("    " if is_last else "│   ")

        # Format children
        for i, child in enumerate(node.children):
            is_last_child = i == len(node.children) - 1
            result.append(self.format_tree(child, child_prefix, is_last_child))

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
