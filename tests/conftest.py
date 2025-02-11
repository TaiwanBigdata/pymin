"""Test configuration for pymin"""

import os
import sys
from pathlib import Path
import pytest
import tomlkit

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_pyproject(tmp_path):
    """Create a sample pyproject.toml file for testing"""
    pyproject_path = tmp_path / "pyproject.toml"
    content = {
        "project": {
            "name": "test-project",
            "version": "0.1.0",
            "dependencies": [
                "requests>=2.31.0",
                "click>=8.0.0",
            ],
        }
    }

    with open(pyproject_path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(content))

    return pyproject_path


@pytest.fixture
def empty_pyproject(tmp_path):
    """Create an empty pyproject.toml file for testing"""
    pyproject_path = tmp_path / "pyproject.toml"
    content = {"project": {"name": "test-project", "version": "0.1.0"}}

    with open(pyproject_path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(content))

    return pyproject_path


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing"""
    return tmp_path
