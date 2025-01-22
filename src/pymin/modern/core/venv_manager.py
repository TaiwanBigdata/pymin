"""Core functionality for virtual environment management"""

from pathlib import Path
from typing import Dict, Any, Optional
from .venv_analyzer import VenvAnalyzer


class VenvManager:
    """Manager for virtual environment operations"""

    def __init__(self, project_path: Optional[str] = None):
        """Initialize VenvManager with project path"""
        self.analyzer = VenvAnalyzer(project_path)

    def get_environment_info(self) -> Dict[str, Any]:
        """Get comprehensive environment information"""
        # Get basic environment info from analyzer
        env_info = self.analyzer.get_venv_info()
        return env_info
