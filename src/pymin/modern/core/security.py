# Security analysis service for package names
from typing import List, Tuple
from rich.live import Live
from .similarity import find_similar_packages


class SecurityChecker:
    """Check package names for security issues"""

    def __init__(self, similarity_threshold: float = 0.8):
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
