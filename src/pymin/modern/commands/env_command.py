"""Environment management commands implementation"""

import click
from ..core.venv_manager import VenvManager
from ..ui.env_view import display_environment_info
from rich.console import Console

console = Console()


@click.command()
def info():
    """Show environment information"""
    try:
        manager = VenvManager()
        env_info = manager.get_environment_info()
        display_environment_info(env_info)
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
