# Package name validation service with PyPI availability checking and security analysis
import re
import keyword
import requests
from packaging.utils import canonicalize_name
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from typing import List, Tuple, Set, Optional
from ..ui.style import StyleType, SymbolType
from ..ui.console import print_error, print_warning, print_success, console


class PackageNameChecker:
    """Check package name availability and validity"""

    PYPI_URL = "https://pypi.org/pypi"
    SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self):
        self._popular_packages_cache = None
        self._spinner_idx = 0

    def _get_spinner(self) -> str:
        """Get next spinner character"""
        char = self.SPINNER_CHARS[self._spinner_idx]
        self._spinner_idx = (self._spinner_idx + 1) % len(self.SPINNER_CHARS)
        return char

    def _get_popular_packages(self) -> List[str]:
        """Get all packages from PyPI for similarity checking"""
        if self._popular_packages_cache is not None:
            return self._popular_packages_cache

        with Live(Text(), refresh_per_second=10, console=console) as live:
            try:
                live.update(
                    Text.from_markup(
                        f"[blue]{self._get_spinner()} Fetching package list from PyPI..."
                    )
                )
                response = requests.get("https://pypi.org/simple/")
                response.raise_for_status()

                packages = re.findall(r"<a[^>]*>(.*?)</a>", response.text)
                self._popular_packages_cache = list(set(packages))

                live.update(
                    Text.from_markup(
                        "[green]✓ Package list fetched successfully!"
                    )
                )
                return self._popular_packages_cache
            except requests.RequestException:
                live.update(
                    Text.from_markup("[red]✗ Failed to fetch package list!")
                )
                print_error("Failed to fetch package list from PyPI")
                return []

    @staticmethod
    def validate_name(name: str) -> tuple[bool, str]:
        """Validate package name according to PyPI naming rules"""
        normalized_name = canonicalize_name(name)

        if not name:
            return False, "Package name cannot be empty"
        if len(name) > 214:
            return False, "Package name must be 214 characters or less"

        if name.lower() in keyword.kwlist:
            return False, "Package name cannot be a Python keyword"

        if not re.match(r"^[A-Za-z0-9][-A-Za-z0-9._]+[A-Za-z0-9]$", name):
            return (
                False,
                "Package name can only contain ASCII letters, numbers, ., -, _",
            )

        if re.search(r"[-._]{2,}", name):
            return False, "Package name cannot have consecutive . - _"

        if all(c in ".-_" for c in name):
            return False, "Package name cannot be composed entirely of . - _"

        return True, ""

    def check_availability(self, name: str) -> dict:
        """Check if a package name is available on PyPI"""
        result = {
            "name": name,
            "normalized_name": canonicalize_name(name),
            "is_valid": False,
            "is_available": False,
            "message": "",
            "security_issues": [],
        }

        # Basic validation
        is_valid, message = self.validate_name(name)
        if not is_valid:
            result["message"] = message
            return result

        result["is_valid"] = True

        # Check availability
        response = requests.get(f"{self.PYPI_URL}/{name}/json")
        if response.status_code == 404:
            result["is_available"] = True
            result["message"] = "This package name is available!"

            # Check for similar packages
            packages = self._get_popular_packages()
            if packages:
                with Live(
                    Text(), refresh_per_second=10, console=console
                ) as live:
                    similar_packages = PackageSearcher().search_similar(
                        name, packages
                    )
                    live.update(Text.from_markup("[green]✓ Check completed!"))

                if similar_packages:
                    result["security_issues"] = similar_packages
                    result[
                        "message"
                    ] += "\n\nWarning: Found potential typosquatting packages:"
                    for pkg, score in similar_packages[:5]:
                        result[
                            "message"
                        ] += f"\n - {pkg} (similarity: {score:.2%})"
        else:
            result["message"] = "This package name is already in use"

        return result

    def display_result(self, result: dict):
        """Display the check results with proper formatting"""
        if result["is_valid"] and result["is_available"]:
            status_color = "green"
        else:
            status_color = "red"

        text = Text()
        text.append("Package Name: ")
        text.append(f"{result['name']}\n", style="cyan")
        text.append(f"Normalized Name: ")
        text.append(f"{result['normalized_name']}\n", style="cyan")
        text.append(f"Valid Format: {'✓' if result['is_valid'] else '✗'}\n")
        text.append(f"Available: {'✓' if result['is_available'] else '✗'}\n")

        # Split message into main message and warning
        main_message = result["message"]
        if "\n\nWarning:" in main_message:
            main_message, _ = main_message.split("\n\nWarning:", 1)
            text.append(
                f"Message: {main_message}", style=f"{status_color} bold"
            )
            text.append("\n\nWarning:\n", style="yellow")

            # Use security_issues to generate warning messages
            for pkg, score in result["security_issues"][:5]:
                pkg_url = f"https://pypi.org/project/{pkg}"
                text.append(" - ", style="yellow")
                pkg_text = Text(pkg, style="yellow")
                pkg_text.stylize(f"link {pkg_url}")
                text.append(pkg_text)
                text.append(
                    f" (similarity: {score:.2%})\n",
                    style="yellow",
                )
        else:
            text.append(
                f"Message: {main_message}", style=f"{status_color} bold"
            )

        console.print(
            Panel.fit(
                text,
                title="PyPI Package Name Check Results",
                title_align="left",
                border_style="blue",
            )
        )


class PackageSearcher:
    """Search for similar package names on PyPI"""

    PYPI_URL = "https://pypi.org/project"
    SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold
        self._packages_cache = None
        self._spinner_idx = 0

    def _get_spinner(self) -> str:
        """Get next spinner character"""
        char = self.SPINNER_CHARS[self._spinner_idx]
        self._spinner_idx = (self._spinner_idx + 1) % len(self.SPINNER_CHARS)
        return char

    def _get_all_packages(self) -> List[str]:
        """Fetch all package names from PyPI"""
        if self._packages_cache is not None:
            return self._packages_cache

        with Live(Text(), refresh_per_second=10, console=console) as live:
            try:
                live.update(
                    Text.from_markup(
                        f"[blue]{self._get_spinner()} Fetching package list from PyPI..."
                    )
                )
                response = requests.get("https://pypi.org/simple/")
                response.raise_for_status()

                packages = re.findall(r"<a[^>]*>(.*?)</a>", response.text)
                self._packages_cache = list(set(packages))
                live.update(
                    Text.from_markup(
                        "[green]✓ Package list fetched successfully!"
                    )
                )
                return self._packages_cache
            except requests.RequestException:
                live.update(
                    Text.from_markup("[red]✗ Failed to fetch package list!")
                )
                print_error("Failed to fetch package list from PyPI")
                return []

    @staticmethod
    def _normalized_name(name: str) -> str:
        """Normalize package name"""
        return name.lower().replace("_", "-")

    def search_similar(
        self, name: str, packages: Optional[List[str]] = None
    ) -> List[Tuple[str, float]]:
        """Search for packages with names similar to the given name"""
        if packages is None:
            packages = self._get_all_packages()
        if not packages:
            return []

        with Live(Text(), refresh_per_second=10, console=console) as live:
            total = len(packages)
            normalized_query = self._normalized_name(name)
            query_length = len(normalized_query)
            similar_packages = []
            batch_size = max(1, total // 100)  # Process in batches of ~100
            processed = 0

            # Process packages in batches
            for i in range(0, total, batch_size):
                # Get current batch
                batch_packages = packages[i : i + batch_size]
                processed += len(batch_packages)

                # Update progress
                live.update(
                    Text.from_markup(
                        f"[blue]{self._get_spinner()} Checking similar packages... ({processed}/{total}) [{int(processed/total*100)}%]"
                    )
                )

                # Process current batch
                for pkg in batch_packages:
                    # Normalize package name
                    normalized_pkg = self._normalized_name(pkg)
                    pkg_length = len(normalized_pkg)

                    # Quick filter: length check
                    if not (
                        0.7 * query_length <= pkg_length <= 1.3 * query_length
                    ):
                        continue

                    # Calculate similarity
                    similarity = self._calculate_similarity(
                        normalized_query, normalized_pkg
                    )
                    if similarity >= self.similarity_threshold and pkg != name:
                        similar_packages.append((pkg, similarity))

            live.update(Text.from_markup("[green]✓ Search completed!"))

            # Sort by similarity score in descending order
            return sorted(similar_packages, key=lambda x: x[1], reverse=True)

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using SequenceMatcher"""
        from difflib import SequenceMatcher

        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def get_package_url(self, package_name: str) -> str:
        """Generate PyPI URL for a package"""
        return f"{self.PYPI_URL}/{package_name}"
