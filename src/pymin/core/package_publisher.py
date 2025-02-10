# Package publishing functionality
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import tomllib

from ..ui import console
from .exceptions import PackageError
from .utils import read_pyproject_toml


class PackagePublisher:
    """Publish packages to PyPI."""

    def __init__(self):
        """Initialize package publisher."""
        self.pypi_url = "https://upload.pypi.org/legacy/"
        self.test_pypi_url = "https://test.pypi.org/legacy/"
        self.pypirc_path = Path.home() / ".pypirc"

    def _check_requirements(self) -> None:
        """
        Check if all requirements for publishing are met.

        Raises:
            PackageError: If any requirement is not met
        """
        # Check for pyproject.toml
        if not Path("pyproject.toml").exists():
            raise PackageError("pyproject.toml not found")

        # Check for required tools
        try:
            subprocess.run(
                ["pip", "show", "build", "twine"],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            raise PackageError(
                "Required tools not installed",
                "Run: pip install build twine",
            )

    def _update_version(self, version: str) -> None:
        """
        Update version in pyproject.toml.

        Args:
            version: New version string
        """
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            content = f.read()

        # Update version
        content = re.sub(
            r'version\s*=\s*"[^"]+"',
            f'version = "{version}"',
            content,
        )

        with open("pyproject.toml", "w", encoding="utf-8") as f:
            f.write(content)

    def _build_package(self) -> None:
        """
        Build package using build tool.

        Raises:
            PackageError: If build fails
        """
        try:
            subprocess.run(
                ["python", "-m", "build"],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise PackageError(f"Failed to build package: {e.stderr}")

    def _upload_package(self, test: bool = False) -> None:
        """
        Upload package using twine.

        Args:
            test: Whether to upload to Test PyPI

        Raises:
            PackageError: If upload fails
        """
        repo_flag = "--repository testpypi" if test else ""

        try:
            result = subprocess.run(
                f"twine upload {repo_flag} dist/*",
                shell=True,
                capture_output=True,
                text=True,
                check=True,
                env={"PYTHONIOENCODING": "utf-8", **os.environ},
            )
        except subprocess.CalledProcessError as e:
            raise PackageError(f"Failed to upload package: {e.stderr}")

    def _clean_dist(self) -> None:
        """Clean up dist directory."""
        if Path("dist").exists():
            shutil.rmtree("dist")

    def publish(self, test: bool = False) -> None:
        """
        Publish package to PyPI.

        Args:
            test: Whether to publish to Test PyPI

        Raises:
            PackageError: If publishing fails
        """
        try:
            # Check requirements
            self._check_requirements()

            # Get current version
            project_info = read_pyproject_toml("pyproject.toml")
            current_version = project_info["project"]["version"]

            # For test PyPI, append .dev0 to version
            if test:
                test_version = f"{current_version}.dev0"
                self._update_version(test_version)

            # Build package
            console.start_status("Building package...")
            self._build_package()
            console.success("Package built successfully")

            # Upload package
            console.start_status("Uploading to PyPI...")
            self._upload_package(test)
            console.success(
                f"Package published successfully to {'Test ' if test else ''}PyPI"
            )

            # Clean up
            self._clean_dist()
            console.success("Cleaned up build files")

            # Restore original version for test PyPI
            if test:
                self._update_version(current_version)
                console.success(f"Restored original version: {current_version}")

        except Exception as e:
            console.error(str(e))
            # Clean up on error
            self._clean_dist()
            if test and "current_version" in locals():
                self._update_version(current_version)
            raise

        finally:
            console.stop_status()
