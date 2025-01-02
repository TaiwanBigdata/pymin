# String similarity analysis service for package name comparison
from typing import List, Tuple
from difflib import SequenceMatcher
from rich.live import Live
from rich.text import Text
from .utils import normalize_name


def _normalized_name(name: str) -> str:
    """Normalize package name"""
    return normalize_name(name)


def _calculate_similarity(name1: str, name2: str) -> float:
    """Calculate similarity ratio between two package names"""
    return SequenceMatcher(None, name1, name2).ratio()


def find_similar_packages(
    name: str,
    packages: List[str],
    similarity_threshold: float,
    live: Live,
    spinner_func=None,
) -> List[Tuple[str, float]]:
    """
    Find packages with names similar to the given name.

    Args:
        name: Package name to search for
        packages: List of package names to search in
        similarity_threshold: Minimum similarity score (0.0-1.0)
        live: Live display object for progress updates
        spinner_func: Optional function to get spinner character

    Returns:
        List of tuples containing (package_name, similarity_score)
    """
    total = len(packages)
    normalized_query = _normalized_name(name)
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
        spinner = spinner_func() if spinner_func else "⠋"
        live.update(
            Text.from_markup(
                f"[blue]{spinner} Checking similar packages... ({processed}/{total}) [{int(processed/total*100)}%]"
            )
        )

        # Process current batch
        for pkg in batch_packages:
            # Normalize package name
            normalized_pkg = _normalized_name(pkg)
            pkg_length = len(normalized_pkg)

            # Quick filter: length check
            if not (0.7 * query_length <= pkg_length <= 1.3 * query_length):
                continue

            # Calculate similarity
            similarity = _calculate_similarity(normalized_query, normalized_pkg)
            if similarity >= similarity_threshold and pkg != name:
                similar_packages.append((pkg, similarity))

    # Sort by similarity score in descending order
    return sorted(similar_packages, key=lambda x: x[1], reverse=True)
