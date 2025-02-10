"""Package name availability check command"""

import click
from ...core.check import PackageNameChecker
from ...ui.console import print_error


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
