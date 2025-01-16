# Console display functionality
from typing import Optional, Any, List
from rich.console import Console as RichConsole
from rich.prompt import Confirm
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.status import Status

from .style import Colors, Styles, Symbols


class Console:
    """Wrapper for rich.console.Console with additional functionality."""

    def __init__(self):
        """Initialize console with default settings."""
        self._console = RichConsole()
        self._status: Optional[Status] = None

    def print(self, *args, **kwargs):
        """Print to console using rich formatting."""
        self._console.print(*args, **kwargs)

    def success(self, message: str, details: Optional[str] = None):
        """
        Print success message.

        Args:
            message: Main success message
            details: Optional details
        """
        text = Text()
        text.append(f"{Symbols.SUCCESS} ", style=Styles.SUCCESS)
        text.append(message)
        self.print(text)
        if details:
            self.print(Text(details, style=Styles.DIM))

    def error(self, message: str, details: Optional[str] = None):
        """
        Print error message.

        Args:
            message: Main error message
            details: Optional error details
        """
        text = Text()
        text.append(f"{Symbols.ERROR} ", style=Styles.ERROR)
        text.append(message)
        self.print(text)
        if details:
            self.print(Text(details, style=Styles.DIM))

    def warning(self, message: str, details: Optional[str] = None):
        """
        Print warning message.

        Args:
            message: Main warning message
            details: Optional warning details
        """
        text = Text()
        text.append(f"{Symbols.WARNING} ", style=Styles.WARNING)
        text.append(message)
        self.print(text)
        if details:
            self.print(Text(details, style=Styles.DIM))

    def info(self, message: str, details: Optional[str] = None):
        """
        Print info message.

        Args:
            message: Main info message
            details: Optional info details
        """
        text = Text()
        text.append(f"{Symbols.INFO} ", style=Styles.INFO)
        text.append(message)
        self.print(text)
        if details:
            self.print(Text(details, style=Styles.DIM))

    def confirm(self, message: str, default: bool = False) -> bool:
        """
        Ask for user confirmation.

        Args:
            message: Confirmation message
            default: Default response if user just presses Enter

        Returns:
            True if user confirmed, False otherwise
        """
        return Confirm.ask(message, default=default)

    def create_table(
        self, title: Optional[str] = None, show_header: bool = True, **kwargs
    ) -> Table:
        """
        Create a new table with consistent styling.

        Args:
            title: Optional table title
            show_header: Whether to show table header
            **kwargs: Additional arguments passed to Table

        Returns:
            Styled table instance
        """
        return Table(
            title=title,
            show_header=show_header,
            header_style=Styles.BOLD,
            title_style=Styles.BOLD,
            **kwargs,
        )

    def create_panel(
        self, content: Any, title: Optional[str] = None, **kwargs
    ) -> Panel:
        """
        Create a new panel with consistent styling.

        Args:
            content: Panel content
            title: Optional panel title
            **kwargs: Additional arguments passed to Panel

        Returns:
            Styled panel instance
        """
        return Panel(
            content,
            title=title,
            title_align="left",
            border_style="bright_blue",
            **kwargs,
        )

    def start_status(self, message: str) -> None:
        """
        Start a status spinner with message.

        Args:
            message: Status message to display
        """
        if self._status:
            self._status.stop()
        self._status = self._console.status(message, spinner="dots")
        self._status.start()

    def update_status(self, message: str) -> None:
        """
        Update current status message.

        Args:
            message: New status message
        """
        if self._status:
            self._status.update(message)

    def stop_status(self) -> None:
        """Stop current status spinner."""
        if self._status:
            self._status.stop()
            self._status = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_status()


# Global console instance
console = Console()
