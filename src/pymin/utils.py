# Utility functions for package name normalization and string manipulation
import re
import os
from pathlib import Path


def normalize_name(name: str) -> str:
    """
    Normalize package name according to PEP 503
    https://peps.python.org/pep-0503/#normalized-names
    """
    return re.sub(r"[-_.]+", "-", name).lower()
