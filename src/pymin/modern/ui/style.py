"""Style definitions for consistent UI appearance"""

from rich.style import Style
from rich.theme import Theme
from enum import Enum

# Color constants
COLORS = {
    "success": "green",
    "error": "red",
    "warning": "yellow",
    "info": "blue",
    "highlight": "cyan",
    "dim": "bright_black",
}


class StyleType(Enum):
    """Style definitions that can be used directly without .value"""

    # Title styles
    TITLE = Style(color="cyan", bold=True)
    SUBTITLE = Style(color="blue", bold=True)
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
    # Other styles
    HIGHLIGHT = Style(color="cyan")
    DIM = Style(dim=True)
    URL = Style(color="blue", underline=True)
    COMMAND = Style(color="cyan")

    def __call__(self):
        return self.value


class SymbolType(Enum):
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


# Theme definition
THEME = Theme(
    {
        "success": f"bold {COLORS['success']}",
        "error": f"bold {COLORS['error']}",
        "warning": COLORS["warning"],
        "info": COLORS["info"],
        "highlight": COLORS["highlight"],
        "dim": COLORS["dim"],
    }
)


def get_status_symbol(status: str) -> str:
    """Get status symbol for given status"""
    try:
        return SymbolType[status.upper()].value
    except KeyError:
        return SymbolType.BULLET.value


def get_style(style_name: str) -> Style:
    """Get style for given style name"""
    try:
        return StyleType[style_name.upper()].value
    except KeyError:
        return Style()
