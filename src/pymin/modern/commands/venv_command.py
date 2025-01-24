"""Virtual environment creation command implementation"""

import click
from pathlib import Path
from rich.panel import Panel
from rich.text import Text
from ..core.venv_manager import VenvManager
from ..ui.console import (
    print_success,
    print_error,
    print_warning,
    progress_status,
    console,
)
from ..ui.style import StyleType, SymbolType


@click.command()
@click.argument("name", required=False)
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "-r",
    "--rebuild",
    is_flag=True,
    help="Rebuild the environment if it already exists",
)
def venv(name: str = None, yes: bool = False, rebuild: bool = False):
    """Create a new virtual environment

    If NAME is not provided, it defaults to 'env' in the current directory.
    """
    venv_path = Path(name or "env")

    # Check if environment exists
    if venv_path.exists():
        if not rebuild:
            if not yes and not click.confirm(
                f"\nEnvironment {venv_path} already exists. Rebuild?",
                default=False,
            ):
                return
            rebuild = True

    try:
        with progress_status("Creating virtual environment..."):
            manager = VenvManager()
            env_info = manager.create_environment(venv_path, rebuild=rebuild)

        # Display environment information in a panel
        text = Text()
        text.append("Virtual Environment: ", style=StyleType.ENV_FIELD_NAME)
        text.append(
            f"{env_info['project_name']}",
            style=StyleType.ENV_PROJECT_NAME,
        )
        text.append(
            f"({env_info['env_name']})",
            style=StyleType.ENV_VENV_NAME,
        )
        text.append("\n")

        text.append("Python Version: ", style=StyleType.ENV_FIELD_NAME)
        text.append(
            env_info["python"]["version"] or "Unknown",
            style=StyleType.ENV_VERSION,
        )
        text.append("\n")

        text.append("Pip Version: ", style=StyleType.ENV_FIELD_NAME)
        text.append(
            env_info["pip"]["version"] or "Unknown",
            style=StyleType.ENV_VERSION,
        )
        text.append("\n")

        text.append("Location: ", style=StyleType.ENV_FIELD_NAME)
        text.append(str(venv_path.absolute()), style=StyleType.ENV_PATH)
        text.append("\n")

        text.append("Status: ", style=StyleType.ENV_FIELD_NAME)
        text.append(
            f"{SymbolType.SUCCESS} Created",
            style=StyleType.SUCCESS,
        )

        console.print(
            Panel(
                text,
                title="Environment Created",
                title_align="left",
                border_style=StyleType.SUCCESS,
                padding=(1, 2),
            )
        )

        # Install requirements if they exist
        requirements_file = Path("requirements.txt")
        if requirements_file.exists():
            with progress_status("Installing requirements..."):
                manager.install_requirements(venv_path)
            print_success("Requirements installed successfully")

        # Activate the environment
        print_success("Use 'pmm on' to activate the environment")

    except Exception as e:
        print_error(f"Failed to create environment: {str(e)}")
