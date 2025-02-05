"""PyPI integration commands"""

import click
from typing import Optional
from ..core.check import PackageNameChecker
from ..core.search import PackageSearcher
from ..core.release import PackageReleaser
from ..ui.console import print_error, print_warning, print_success, console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel


@click.command()
@click.argument("name")
def check(name):
    """Check package name availability"""
    try:
        checker = PackageNameChecker()
        result = checker.check_availability(name)
        checker.display_result(result)
    except Exception as e:
        print_error(f"Failed to check package name: {str(e)}")
        return


@click.command()
@click.argument("name")
@click.option(
    "--threshold",
    "-t",
    default=0.8,
    help="Similarity threshold (0.0-1.0)",
    type=float,
)
def search(name: str, threshold: float):
    """Search for similar package names on PyPI"""
    try:
        searcher = PackageSearcher(similarity_threshold=threshold)
        results = searcher.search_similar(name)

        if not results:
            print_warning("No similar packages found.")
            return

        table = Table(
            title=Text.assemble(
                "Similar Packages to '",
                (name, "cyan"),
                "'",
            ),
            show_header=True,
            header_style="bold magenta",
            expand=False,
            title_justify="left",
        )

        table.add_column("Package Name", style="cyan")
        table.add_column("Similarity", justify="center")
        table.add_column("PyPI URL", style="blue")

        for pkg_name, similarity in results:
            url = searcher.get_package_url(pkg_name)
            table.add_row(
                pkg_name, f"{similarity:.2%}", f"[link={url}]{url}[/link]"
            )

        console.print("\n")  # Add empty line
        console.print(table)
        console.print(
            "\n[dim]Tip: Click on package names or URLs to open in browser[/dim]"
        )
    except Exception as e:
        print_error(f"Failed to search for similar packages: {str(e)}")
        return


@click.command()
@click.option(
    "--test",
    is_flag=True,
    help="Publish to Test PyPI instead of PyPI",
)
def release(test: bool):
    """Build and publish package to PyPI or Test PyPI"""
    try:
        releaser = PackageReleaser()
        releaser.release(test=test)
    except Exception as e:
        print_error(f"Failed to release package: {str(e)}")
        return
