# Security service for package name typosquatting detection and analysis
from typing import List, Tuple
from rich.console import Console
from rich.live import Live
from rich.text import Text
from .similarity import find_similar_packages

console = Console()


class SecurityChecker:
    """Security checker for package names"""

    def __init__(
        self, similarity_threshold: float = 0.85
    ):  # Higher threshold for security
        self.similarity_threshold = similarity_threshold

    def check_typosquatting(
        self, name: str, packages: List[str], live: Live
    ) -> List[Tuple[str, float]]:
        """
        Check for potential typosquatting packages.

        Args:
            name: Package name to check
            packages: List of package names to check against
            live: Live display object for progress updates

        Returns:
            List of tuples containing (package_name, similarity_score)
        """
        return find_similar_packages(
            name=name,
            packages=packages,
            similarity_threshold=self.similarity_threshold,
            live=live,
        )
