"""Virtual environment information command"""

import click
from ...core.venv_manager import VenvManager
from ...ui.env_view import display_environment_info
from ...ui.console import progress_status, console


@click.command()
def info():
    """Show environment information"""
    try:
        with progress_status("Getting environment information...") as status:
            manager = VenvManager()
            env_info = manager.get_environment_info()
        display_environment_info(env_info)
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
