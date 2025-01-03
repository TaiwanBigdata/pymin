# Package name validation service with PyPI availability checking and security analysis
import re
import keyword
import requests
from packaging.utils import canonicalize_name
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from .validators import PackageNameValidator
from .utils import normalize_name
from .validators import validate_package_name
from .security import SecurityChecker
from typing import List
from rich.live import Live

console = Console()


class PackageNameChecker:
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
        """
        Get all packages from PyPI for similarity checking
        """
        # Use cache to avoid repeated requests
        if self._popular_packages_cache is not None:
            return self._popular_packages_cache

        with Live(Text(), refresh_per_second=10, console=console) as live:
            try:
                live.update(
                    Text.from_markup(
                        f"[blue]{self._get_spinner()} Fetching package list from PyPI..."
                    )
                )
                # Get package list from PyPI simple API
                response = requests.get("https://pypi.org/simple/")
                response.raise_for_status()

                # Parse response content
                packages = re.findall(r"<a[^>]*>(.*?)</a>", response.text)
                self._popular_packages_cache = list(
                    set(packages)
                )  # Use deduplicated list

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
                console.print(
                    "[red]Failed to fetch package list from PyPI[/red]"
                )
                return []

    @staticmethod
    def validate_name(name: str) -> tuple[bool, str]:
        # Use packaging's standardization function
        normalized_name = canonicalize_name(name)

        # Basic length check
        if not name:
            return False, "Package name cannot be empty"
        if len(name) > 214:
            return False, "Package name must be 214 characters or less"

        # Python keyword check
        if name.lower() in keyword.kwlist:
            return False, "Package name cannot be a Python keyword"

        # Character validation
        if not re.match(r"^[A-Za-z0-9][-A-Za-z0-9._]+[A-Za-z0-9]$", name):
            return (
                False,
                "Package name can only contain ASCII letters, numbers, ., -, _",
            )

        # Consecutive punctuation check
        if re.search(r"[-._]{2,}", name):
            return False, "Package name cannot have consecutive . - _"

        # Full punctuation check
        if all(c in ".-_" for c in name):
            return False, "Package name cannot be composed entirely of . - _"

        return True, ""

    def check_availability(self, name: str) -> dict:
        result = {
            "name": name,
            "normalized_name": normalize_name(name),
            "canonical_name": canonicalize_name(name),
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
        response = requests.get(f"https://pypi.org/pypi/{name}/json")
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

        # Add security issues in yellow (This part can be removed, as it's already handled above)
        if (
            result.get("security_issues")
            and "\n\nWarning:" not in result["message"]
        ):
            text.append(
                "\n\nWarning:\n",
                style="yellow",
            )
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

        console.print(
            Panel.fit(
                text,
                title="PyPI Package Name Check Results",
                title_align="left",
            )
        )
