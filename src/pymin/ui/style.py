"""Style definitions for consistent UI appearance"""

from rich.style import Style
from rich.theme import Theme
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from rich.text import Text


class Colors(str, Enum):
    """Color definitions that can be used directly in f-strings"""

    SUCCESS = "green"
    ERROR = "red"
    WARNING = "yellow"
    INFO = "blue"
    HIGHLIGHT = "cyan"
    DIM = "bright_black"

    def __format__(self, format_spec):
        return str(self.value)


@dataclass
class PanelConfig:
    """Standard panel configuration"""

    title_align: str = "left"
    border_style: str = "blue"
    padding: tuple = (1, 2)


@dataclass
class TableConfig:
    """Standard table configuration"""

    title_justify: str = "left"
    show_header: bool = True
    header_style: str = "bold magenta"
    expand: bool = False
    padding: tuple = (0, 1)


class StyleType(Enum):
    """Style definitions that can be used directly without .value"""

    # Title styles
    TITLE = Style(color="cyan", bold=True)
    SUBTITLE = Style(color="blue", bold=True)
    SECTION_TITLE = Style(color="white", bold=True)

    # Status styles
    SUCCESS = Style(color="green", bold=True)
    ERROR = Style(color="red", bold=True)
    WARNING = Style(color="yellow")
    INFO = Style(color="blue")

    # Package status styles
    NORMAL = Style(color="green")
    REDUNDANT = Style(color="yellow")
    NOT_INSTALLED = Style(color="red")
    NOT_IN_REQUIREMENTS = Style(color="blue")
    VERSION_MISMATCH = Style(color="red")

    # Package related styles
    PACKAGE_NAME = Style(color="cyan")
    PACKAGE_VERSION = Style(color="blue")
    PACKAGE_DEPENDENCY = Style(dim=True)
    PACKAGE_EXTRAS = Style(color="magenta")

    # Environment related styles
    VENV_ACTIVE = Style(color="green", bold=True)
    VENV_INACTIVE = Style(color="yellow")
    VENV_PATH = Style(color="blue")
    ENV_NAME = Style(color="green")
    ENV_PATH = Style(color="bright_black")
    ENV_PROJECT_NAME = Style(color="cyan")
    ENV_VENV_NAME = Style(color="white", dim=True)
    ENV_VERSION = Style(color="cyan")
    ENV_FIELD_NAME = Style(dim=True)
    ENV_SWITCH_ARROW = Style(color="blue", bold=True)
    ENV_NONE = Style(color="white", dim=True)

    # Status styles
    LOADING = Style(color="cyan")  # Added for consistent loading status color

    # Other styles
    HIGHLIGHT = Style(color="cyan")
    DIM = Style(dim=True)
    URL = Style(color="blue", underline=True)
    COMMAND = Style(color="cyan")

    def __str__(self):
        return str(self.value)

    def __format__(self, format_spec):
        return str(self.value)

    def __get__(self, instance, owner):
        return self.value


class SymbolType(str, Enum):
    SUCCESS = "✓"
    ERROR = "✗"
    WARNING = "⚠"
    INFO = "ℹ"
    # Package status symbols
    NORMAL = "✓"
    REDUNDANT = "⚠"
    NOT_INSTALLED = "✗"
    NOT_IN_REQUIREMENTS = "△"
    VERSION_MISMATCH = "≠"  # Installed version doesn't match required version
    DUPLICATE = "⌥"  # Package is defined multiple times
    ARROW = "→"
    BULLET = "•"
    TREE_BRANCH = "├──"
    TREE_LAST = "└──"
    TREE_VERTICAL = "│"

    def __format__(self, format_spec):
        return str(self.value)


# Theme definition
THEME = Theme(
    {
        "success": f"bold {Colors.SUCCESS}",
        "error": f"bold {Colors.ERROR}",
        "warning": Colors.WARNING,
        "info": Colors.INFO,
        "highlight": Colors.HIGHLIGHT,
        "dim": Colors.DIM,
    }
)


def get_status_symbol(status: str) -> Text:
    """Get status symbol with consistent styling

    Args:
        status: Package status string

    Returns:
        Rich Text object with appropriate symbol and style
    """
    status = status.lower()
    if status == "normal":
        return Text(SymbolType.SUCCESS, style=StyleType.SUCCESS)
    elif status == "version_mismatch":
        return Text(SymbolType.VERSION_MISMATCH, style=StyleType.ERROR)
    elif status == "not_installed" or status == "missing":
        return Text(SymbolType.ERROR, style=StyleType.ERROR)
    elif status == "not_in_requirements":
        return Text(SymbolType.WARNING, style=StyleType.WARNING)
    elif status == "redundant":
        return Text(SymbolType.WARNING, style=StyleType.WARNING)
    elif status == "duplicate":
        return Text(SymbolType.DUPLICATE, style=StyleType.WARNING)
    else:
        return Text(SymbolType.ERROR, style=StyleType.ERROR)


def format_env_switch(from_env: Optional[Path], to_env: Optional[Path]) -> str:
    """Format environment switch message with consistent style"""

    def format_env(env_path: Optional[Path]) -> str:
        """Format a single environment path with proper styling"""
        if env_path is None:
            return f"[{StyleType.ENV_NONE}]none[/{StyleType.ENV_NONE}]"

        try:
            project_name = env_path.resolve().parent.name
            env_name = env_path.name
            if not project_name or not env_name:
                return f"[{StyleType.ENV_NONE}]none[/{StyleType.ENV_NONE}]"
            return f"[{StyleType.ENV_PROJECT_NAME}]{project_name}[/{StyleType.ENV_PROJECT_NAME}][{StyleType.ENV_VENV_NAME}]({env_name})[/{StyleType.ENV_VENV_NAME}]"
        except Exception:
            return f"[{StyleType.ENV_NONE}]none[/{StyleType.ENV_NONE}]"

    # Special cases for deactivation and already inactive
    if from_env is None and to_env is None:
        return "No virtual environment is currently active"

    # Format environment displays
    from_display = format_env(from_env)
    to_display = format_env(to_env)

    # Handle different transition cases
    if from_env is None and to_env is not None:
        return f"Activating environment: {from_display} [{StyleType.ENV_SWITCH_ARROW}]{SymbolType.ARROW}[/{StyleType.ENV_SWITCH_ARROW}] {to_display}"
    elif from_env is not None and to_env is None:
        return f"Deactivating environment: {from_display} [{StyleType.ENV_SWITCH_ARROW}]{SymbolType.ARROW}[/{StyleType.ENV_SWITCH_ARROW}] {to_display}"
    elif from_env == to_env or (
        from_env and to_env and from_env.samefile(to_env)
    ):
        return f"Environment is already active: {to_display}"
    else:
        # Check if we're activating from none
        try:
            if (
                from_env is None
                or not from_env.exists()
                or not (from_env / "bin" / "activate").exists()
            ):
                return f"Activating environment: {from_display} [{StyleType.ENV_SWITCH_ARROW}]{SymbolType.ARROW}[/{StyleType.ENV_SWITCH_ARROW}] {to_display}"
        except Exception:
            return f"Activating environment: {from_display} [{StyleType.ENV_SWITCH_ARROW}]{SymbolType.ARROW}[/{StyleType.ENV_SWITCH_ARROW}] {to_display}"

        return f"Switching environment: {from_display} [{StyleType.ENV_SWITCH_ARROW}]{SymbolType.ARROW}[/{StyleType.ENV_SWITCH_ARROW}] {to_display}"


def format_status_message(message: str, status_type: str = "info") -> str:
    """Format status message with consistent style

    Args:
        message: The status message to format
        status_type: The type of status (info, success, warning, error)
    """
    status_type = status_type.lower()
    symbol = SymbolType[status_type.upper()]
    style = StyleType[status_type.upper()]

    return f"[{style}]{symbol} {message}[/{style}]"


# Default configurations
DEFAULT_PANEL = PanelConfig()
DEFAULT_TABLE = TableConfig()
