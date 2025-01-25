"""Text formatting patterns for UI components"""

from rich.text import Text as RichText
from typing import Optional, Dict, Any


class Text(RichText):
    """Enhanced Text class with formatting methods"""

    def append_header(
        self,
        content: str,
        style: str = "white bold",
        add_line_before: bool = True,
        add_line_after: bool = True,
    ) -> "Text":
        """Append a header to the Text object

        Args:
            content: The header content
            style: Style for the header (default: white bold)
            add_line_before: Whether to add a line before the header (default: True)
            add_line_after: Whether to add a line after the header (default: True)

        Returns:
            self for method chaining
        """
        if add_line_before:
            self.append("\n")
        self.append(content, style=style)
        if add_line_after:
            self.append("\n")
        return self

    def append_field(
        self,
        label: str,
        value: str,
        *,  # Force keyword arguments
        note: Optional[str] = None,
        label_style: str = "dim",
        value_style: str = "cyan",
        note_style: str = "dim",
        indent: int = 0,
        note_format: str = " ({note})",
        align: bool = False,
        min_label_width: Optional[int] = None,
        add_line_before: bool = False,
        add_line_after: bool = True,
    ) -> "Text":
        """Append a field with optional alignment and note

        Args:
            label: The field label
            value: The field value
            note: Optional note to display (replaces path)
            label_style: Style for the label (default: dim)
            value_style: Style for the value (default: cyan)
            note_style: Style for the note (default: dim)
            indent: Number of indentation levels (default: 0)
            note_format: Format string for the note (default: " ({note})")
            align: Whether to align the values (default: False)
            min_label_width: Minimum width for label alignment (default: None)
            add_line_before: Whether to add a line before the field (default: False)
            add_line_after: Whether to add a line after the field (default: True)

        Returns:
            self for method chaining
        """
        # Add line before if requested
        if add_line_before:
            self.append("\n")

        # Calculate indentation
        indent_str = " " * (indent * 2)

        # Handle alignment
        if align:
            # Update maximum label width
            label_width = len(label)
            if min_label_width:
                label_width = max(label_width, min_label_width)
            self._max_label_width = max(self._max_label_width, label_width)

            # Format label with alignment
            formatted_label = f"{indent_str}{label:<{self._max_label_width}}"
        else:
            formatted_label = f"{indent_str}{label}:"

        # Append label
        self.append(formatted_label, style=label_style)
        self.append(" ")

        # Append value
        self.append(value, style=value_style)

        # Append note if provided
        if note:
            self.append(note_format.format(note=note), style=note_style)

        # Add line after if requested
        if add_line_after:
            self.append("\n")

        return self
