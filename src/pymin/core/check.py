# Package name validation service with PyPI availability checking and security analysis
import re
import requests
from typing import List, Dict, Optional, Tuple
from packaging.utils import canonicalize_name
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from .validators import PackageNameValidator
from .security import SecurityChecker
from ..ui.console import (
    print_error,
    print_warning,
    print_success,
    console,
    display_panel,
)


class PackageNameChecker:
    """Check package name availability and validity"""

    PYPI_URL = "https://pypi.org/pypi"
    SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self):
        self.validator = PackageNameValidator()
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
        is_valid, message = self.validator.validate(name)
        if not is_valid:
            result["message"] = message
            return result

        result["is_valid"] = True

        # Check availability
        response = requests.get(f"{self.PYPI_URL}/{name}/json")
        if response.status_code == 404:
            result["is_available"] = True
            result["message"] = "This package name is available!"

            # Only perform security checks if the name is available
            security = SecurityChecker()
            packages = self._get_popular_packages()
            if packages:
                with Live(
                    Text(), refresh_per_second=10, console=console
                ) as live:
                    security_issues = security.check_typosquatting(
                        name, packages, live
                    )
                    live.update(Text.from_markup("[green]✓ Check completed!"))

                if security_issues:
                    result["security_issues"] = security_issues
                    result[
                        "message"
                    ] += "\n\nWarning: Found potential typosquatting packages:"
                    for pkg, score in security_issues[
                        :5
                    ]:  # Only display the top 5 most similar
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

        display_panel(title="PyPI Package Name Check Results", content=text)
