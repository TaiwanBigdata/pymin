"""Virtual environment creation command"""

import click
from pathlib import Path
from rich.panel import Panel
from rich.text import Text
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
        with progress_status("Creating virtual environment..."):
            env_info = manager.create_environment(venv_path, rebuild=rebuild)

        # Display environment information in a panel
        text = Text()
        text.append("Virtual Environment: ", style=StyleType.ENV_FIELD_NAME)
        text.append(
            f"{env_info['project']['name']}",
            style=StyleType.ENV_PROJECT_NAME,
        )
        text.append(
            f"({venv_path.name})",
            style=StyleType.ENV_VENV_NAME,
        )
        text.append("\n")

        text.append("Python Version: ", style=StyleType.ENV_FIELD_NAME)
        text.append(
            env_info["system"]["python"]["version"] or "Unknown",
            style=StyleType.ENV_VERSION,
        )
        text.append("\n")

        text.append("Pip Version: ", style=StyleType.ENV_FIELD_NAME)
        text.append(
            env_info["system"]["pip"]["version"] or "Unknown",
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

        # Use display_panel to show the environment information
        display_panel("Environment Created", text)

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
                print_success("Dependencies installed successfully")

        # Show activation tip
        print_tips("Use 'pm on' to activate the environment")

    except Exception as e:
        print_error(f"Failed to create environment: {str(e)}")
        return
