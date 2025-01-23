"""Style definitions for consistent UI appearance"""

from rich.style import Style
from rich.theme import Theme
from enum import Enum
from dataclasses import dataclass


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
    PACKAGE_VERSION = Style(color="bright_black")
    PACKAGE_DEPENDENCY = Style(dim=True)

    # Environment related styles
    VENV_ACTIVE = Style(color="green", bold=True)
    VENV_INACTIVE = Style(color="yellow")
    VENV_PATH = Style(color="blue")
    ENV_NAME = Style(color="green")
    ENV_PATH = Style(color="bright_black")
    ENV_PROJECT_NAME = Style(color="cyan")
    ENV_VENV_NAME = Style(dim=True)
    ENV_VERSION = Style(color="cyan")
    ENV_FIELD_NAME = Style(dim=True)

    # Other styles
    HIGHLIGHT = Style(color="cyan")
    DIM = Style(dim=True)
    URL = Style(color="blue", underline=True)
    COMMAND = Style(color="cyan")

    def __call__(self):
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
    VERSION_MISMATCH = "≠"
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


def get_status_symbol(status: str) -> str:
    """Get status symbol for given status"""
    try:
        # Special case for missing packages
        if status.lower() == "missing":
            return SymbolType.NOT_INSTALLED
        return SymbolType[status.upper()]
    except KeyError:
        return (
            SymbolType.NOT_INSTALLED
        )  # Default to NOT_INSTALLED symbol for unknown status


def get_style(style_name: str) -> Style:
    """Get style for given style name"""
    try:
        return StyleType[style_name.upper()].value
    except KeyError:
        return Style()


# Default configurations
DEFAULT_PANEL = PanelConfig()
DEFAULT_TABLE = TableConfig()
