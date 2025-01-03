# Package name similarity search service with PyPI integration
import requests
import re
from typing import List, Tuple
from rich.console import Console
from rich.live import Live
from rich.text import Text
from .utils import normalize_name
from .similarity import find_similar_packages

console = Console()


class PackageSearcher:
    """Search for similar package names on PyPI"""

    PYPI_URL = "https://pypi.org/project"
    SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(
        self, similarity_threshold: float = 0.8
    ):  # Keep default at 80%
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

                # Parse response using same method as check.py
                packages = re.findall(r"<a[^>]*>(.*?)</a>", response.text)
                self._packages_cache = list(
                    set(packages)
                )  # Use deduplicated list
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
                console.print(
                    "[red]Failed to fetch package list from PyPI[/red]"
                )
                return []

    def search_similar(self, name: str) -> List[Tuple[str, float]]:
        """
        Search for packages with names similar to the given name.

        Args:
            name: The package name to search for

        Returns:
            List of tuples containing (package_name, similarity_score)
        """
        packages = self._get_all_packages()
        if not packages:
            return []

        with Live(Text(), refresh_per_second=10, console=console) as live:
            similar_packages = find_similar_packages(
                name=name,
                packages=packages,
                similarity_threshold=self.similarity_threshold,
                live=live,
                spinner_func=self._get_spinner,
            )
            live.update(Text.from_markup("[green]✓ Search completed!"))

        return similar_packages

    def get_package_url(self, package_name: str) -> str:
        """Generate PyPI URL for a package"""
        return f"{self.PYPI_URL}/{package_name}"
