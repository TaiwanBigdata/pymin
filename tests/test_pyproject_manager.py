# Test file for PyProjectManager functionality

import pytest
from pathlib import Path
import tomlkit
from src.pymin.core.pyproject_manager import PyProjectManager


def test_init_with_existing_file(sample_pyproject):
    """Test initializing PyProjectManager with an existing file"""
    manager = PyProjectManager(sample_pyproject)
    assert manager.file_path == sample_pyproject
    assert manager._data is None  # Data should be lazy loaded


def test_init_with_nonexistent_file(temp_dir):
    """Test initializing PyProjectManager with a non-existent file"""
    nonexistent_path = temp_dir / "nonexistent.toml"
    manager = PyProjectManager(nonexistent_path)
    assert manager.file_path == nonexistent_path

    # Accessing data should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        _ = manager.data


def test_read_pyproject(sample_pyproject):
    """Test reading pyproject.toml content"""
    manager = PyProjectManager(sample_pyproject)
    data = manager.data

    assert "project" in data
    assert data["project"]["name"] == "test-project"
    assert data["project"]["version"] == "0.1.0"
    assert len(data["project"]["dependencies"]) == 2
    assert "requests>=2.31.0" in data["project"]["dependencies"]
    assert "click>=8.0.0" in data["project"]["dependencies"]


def test_write_pyproject(empty_pyproject):
    """Test writing changes to pyproject.toml"""
    manager = PyProjectManager(empty_pyproject)

    # Add a new dependency
    manager._ensure_dependencies_table()
    dep_list = manager.data["project"]["dependencies"]
    dep_list.append("fastapi>=0.100.0")
    manager._write()

    # Read the file again to verify changes
    with open(empty_pyproject, "r", encoding="utf-8") as f:
        content = tomlkit.parse(f.read())

    assert "fastapi>=0.100.0" in content["project"]["dependencies"]
    assert len(content["project"]["dependencies"]) == 1


def test_add_dependency(empty_pyproject):
    """Test adding a new dependency"""
    manager = PyProjectManager(empty_pyproject)

    # Add a new dependency
    manager.add_dependency("fastapi", "0.100.0", ">=")

    # Verify the dependency was added
    deps = manager.get_dependencies()
    assert "fastapi" in deps
    assert deps["fastapi"] == (">=", "0.100.0")


def test_add_duplicate_dependency(empty_pyproject):
    """Test adding a duplicate dependency"""
    manager = PyProjectManager(empty_pyproject)

    # Add the same dependency twice
    manager.add_dependency("fastapi", "0.100.0", ">=")
    manager.add_dependency("fastapi", "0.101.0", ">=")

    # Verify the dependency was updated
    deps = manager.get_dependencies()
    assert deps["fastapi"] == (">=", "0.101.0")

    # Verify there's only one instance of fastapi in the dependencies
    dep_list = manager.data["project"]["dependencies"]
    fastapi_deps = [d for d in dep_list if "fastapi" in d]
    assert len(fastapi_deps) == 1


def test_remove_dependency(sample_pyproject):
    """Test removing a dependency"""
    manager = PyProjectManager(sample_pyproject)

    # First add a dependency
    manager.add_dependency("fastapi", "0.100.0", ">=")

    # Then remove it
    manager.remove_dependency("fastapi")

    # Verify the dependency was removed
    deps = manager.get_dependencies()
    assert "fastapi" not in deps


def test_bulk_add_dependencies(empty_pyproject):
    """Test adding multiple dependencies at once"""
    manager = PyProjectManager(empty_pyproject)

    # Add multiple dependencies
    dependencies = {
        "fastapi": "0.100.0",  # Using default >=
        "pydantic": ("1.10.0", ">="),  # Explicit constraint
        "uvicorn": ("0.22.0", "=="),  # Different constraint
    }

    manager.bulk_add_dependencies(dependencies)

    # Verify all dependencies were added
    deps = manager.get_dependencies()
    assert deps["fastapi"] == (">=", "0.100.0")
    assert deps["pydantic"] == (">=", "1.10.0")
    assert deps["uvicorn"] == ("==", "0.22.0")


@pytest.mark.parametrize(
    "version,expected",
    [
        # Standard Release Versions (Recommended)
        ("1.2.3", True),  # Standard version number
        ("0.1.0", True),  # Zero version number
        ("20.0.0", True),  # Major version above 10
        # Pre-release Versions (Alpha/Beta/RC)
        ("1.2.3b1", True),  # Beta (recommended format)
        ("1.2.3beta1", True),  # Beta (explicit format)
        ("1.2.3a1", True),  # Alpha (recommended format)
        ("1.2.3alpha1", True),  # Alpha (explicit format)
        ("1.2.3rc1", True),  # Release Candidate
        # Development Versions
        ("1.2.3.dev0", True),  # Development version (recommended)
        # Post-release Versions
        ("1.2.3.post1", True),  # Post-release (recommended)
        # Combined Versions
        ("1.2.3b1.dev0", True),  # Beta + Development
        ("1.2.3.dev0.post1", True),  # Development + Post-release
        # Local Version Identifiers
        ("1.2.3+local", True),  # Simple local version
        ("1.2.3+abc.1", True),  # Local version with dot
        # Invalid Formats
        ("1.2", False),  # Missing patch number
        ("1.2.3.4", False),  # Too many version segments
        ("v1.2.3", False),  # Prefix not allowed
        ("1.2.3-beta1", False),  # Hyphen not allowed
        ("1.2.3_beta1", False),  # Underscore not allowed
        ("1.2.3beta", False),  # Missing pre-release number
        ("1.2.3+local_1", False),  # Underscore not allowed in local version
    ],
)
def test_version_validation_formats(version, expected, empty_pyproject):
    """Test version string validation with various formats following PEP 440 and best practices"""
    manager = PyProjectManager(empty_pyproject)
    result = manager._validate_version(version)
    assert (
        result == expected
    ), f"Version '{version}' validation failed. Expected {expected}, got {result}"


def test_dependency_parsing(empty_pyproject):
    """Test dependency string parsing"""
    manager = PyProjectManager(empty_pyproject)

    # Valid dependency strings
    name, constraint, version = manager._parse_dependency("requests>=2.31.0")
    assert name == "requests"
    assert constraint == ">="
    assert version == "2.31.0"

    name, constraint, version = manager._parse_dependency("fastapi==0.100.0")
    assert name == "fastapi"
    assert constraint == "=="
    assert version == "0.100.0"

    # Invalid dependency string
    with pytest.raises(ValueError):
        manager._parse_dependency("invalid-format")
