"""Event system for package management"""

from typing import Dict, Set, Callable, Any
from threading import Lock


class EventType:
    """Event type constants for package management"""

    class Package:
        """Package related events"""

        INSTALLING = "package.installing"
        INSTALLED = "package.installed"
        FAILED = "package.failed"

    class Venv:
        """Virtual environment related events"""

        CREATING = "venv.creating"
        CREATED = "venv.created"
        FAILED = "venv.failed"

    class Dependency:
        """Dependency related events"""

        COLLECTING = "dependency.collecting"
        COLLECTED = "dependency.collected"
        INSTALLING = "dependency.installing"
        INSTALLED = "dependency.installed"
        FAILED = "dependency.failed"


class EventSystem:
    """Simple event system for package management events"""

    _instance = None
    _lock = Lock()
    _listeners: Dict[str, Set[Callable]] = {}

    def __new__(cls):
        """Ensure singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._listeners = {}
        return cls._instance

    def on(self, event: str, callback: Callable) -> None:
        """Register an event listener

        Args:
            event: Event name to listen for
            callback: Function to call when event occurs
        """
        with self._lock:
            if event not in self._listeners:
                self._listeners[event] = set()
            self._listeners[event].add(callback)

    def off(self, event: str, callback: Callable) -> None:
        """Remove an event listener

        Args:
            event: Event name to remove listener from
            callback: Function to remove
        """
        with self._lock:
            if event in self._listeners and callback in self._listeners[event]:
                self._listeners[event].remove(callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event

        Args:
            event: Event name to emit
            *args: Positional arguments to pass to listeners
            **kwargs: Keyword arguments to pass to listeners
        """
        if event in self._listeners:
            for callback in list(self._listeners[event]):
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    from ..ui.console import print_warning

                    print_warning(f"Error in event listener: {str(e)}")


# Create global event system instance
events = EventSystem()
