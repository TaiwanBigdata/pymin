"""Package name similarity search command"""

import click
from ...core.search import PackageSearcher
from ...ui.console import print_error, print_warning, console
from rich.table import Table
from rich.text import Text


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
