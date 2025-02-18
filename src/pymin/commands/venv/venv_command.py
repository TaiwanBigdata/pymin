"""Virtual environment creation command"""

import click
from pathlib import Path
from rich.panel import Panel
from ...ui.formatting import Text
from rich.prompt import Confirm
from ...core.venv_manager import VenvManager
from ...ui.console import (
    print_success,
    print_error,
    print_warning,
    progress_status,
    console,
    display_panel,
    print_tips,
)
from ...ui.style import StyleType, SymbolType, DEFAULT_PANEL
from ...core.events import events, EventType


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
    try:
        manager = VenvManager()
        venv_path = Path(name or "env")

        # Check if environment exists
        if venv_path.exists():
            if not rebuild:
                if not yes and not Confirm.ask(
                    f"\nEnvironment {venv_path} already exists. Rebuild?",
                    default=False,
                ):
                    return
                rebuild = True

        # Create environment
        with progress_status("Creating virtual environment...") as status:

            def on_venv_creating(venv_path):
                status.update(
                    f"Creating virtual environment: [bold]{venv_path}[/bold]..."
                )

            def on_venv_retrieving(venv_path):
                status.update(f"Retrieving installed system information...")

            events.on(EventType.Venv.CREATING, on_venv_creating)
            events.on(EventType.Venv.RETRIEVING, on_venv_retrieving)

            env_info = manager.create_environment(venv_path, rebuild=rebuild)

            # Create panel content using Text class
            content = (
                Text()
                .append_field(
                    "Virtual Environment",
                    env_info["project"]["name"],
                    note=venv_path.name,
                    value_style=StyleType.ENV_PROJECT_NAME,
                    note_style=StyleType.ENV_VENV_NAME,
                )
                .append_field(
                    "Python Version",
                    env_info["system"]["python"]["version"] or "Unknown",
                    value_style=StyleType.ENV_VERSION,
                )
                .append_field(
                    "Pip Version",
                    env_info["system"]["pip"]["version"] or "Unknown",
                    value_style=StyleType.ENV_VERSION,
                )
                .append_field(
                    "Location",
                    str(venv_path.absolute()),
                    value_style=StyleType.ENV_PATH,
                )
                .append_field(
                    "Status",
                    f"{SymbolType.SUCCESS} Created",
                    value_style=StyleType.SUCCESS,
                    add_line_after=False,
                )
            )

            # Display the panel
            display_panel("Environment Created", content)

        # Install requirements if they exist
        requirements_file = Path("requirements.txt")
        pyproject_file = Path("pyproject.toml")

        if requirements_file.exists() or pyproject_file.exists():
            with progress_status("Installing dependencies...") as status:

                def on_package_installing(pkg_name: str, **kwargs):
                    # 從 kwargs 取得額外資訊
                    extras = kwargs.get("extras")
                    version = kwargs.get("version")
                    constraint = kwargs.get("constraint")
                    total_packages = kwargs.get("total_packages")
                    current_index = kwargs.get("current_index")

                    # 格式化顯示訊息
                    extras_str = (
                        f"[{','.join(sorted(extras))}]" if extras else ""
                    )
                    version_str = (
                        f"{constraint or '=='}{version}" if version else ""
                    )

                    # 更新狀態顯示
                    status.update(
                        f"Installing dependencies... ({current_index}/{total_packages})\n"
                        f"[dim]Installing {pkg_name}{extras_str}{version_str}...[/dim]"
                    )

                # 註冊事件監聽
                events.on(EventType.Package.INSTALLING, on_package_installing)
                manager.install_requirements(venv_path)
                print_success("Virtual environment created successfully")
                console.print()

        # Show activation tip
        print_tips("Use [cyan]pm on[/cyan] to activate the environment")

    except Exception as e:
        print_error(f"Failed to create environment: {str(e)}")
        return
