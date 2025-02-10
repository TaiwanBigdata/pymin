"""Package release command"""

import click
from ...core.release import PackageReleaser
from ...ui.console import print_error


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
