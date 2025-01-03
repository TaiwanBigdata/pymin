# PyMin (歹命)

### pymin (0.0.0)

> Simple is better than complex. — The Zen of Python

PyMin embodies Python's minimalist philosophy: a focused tool that does one thing exceptionally well. The name reflects our commitment to minimalism - minimal configuration, minimal complexity, but maximum effectiveness in PyPI package name validation.

Just as Python emphasizes readability and simplicity, PyMin provides a clean, intuitive interface for package name validation. No unnecessary features, no complex configurations - just straightforward, reliable package name checking.

The name "PyMin" carries dual meanings:

-   In English: "Py" (Python) + "Min" (Minimal/Minimalist)
    -   Represents our commitment to minimalist design and focused functionality
    -   Follows Python's "Simple is better than complex" philosophy
-   In Taiwanese: "歹命" (Pháiⁿ-miā)
    -   A humorous reference to the common frustration of finding package names already taken
    -   Reflects the daily struggles of developers trying to find available PyPI names
    -   Turns a common developer pain point into a playful tool name

This duality in naming captures both our design philosophy and the real-world problem we're solving, while adding a touch of Taiwanese developer humor to the Python ecosystem.

# Features

## Core Features

1. Package Name Validation

    - Real-time PyPI availability check
    - PEP 503 naming convention validation
    - Standardized name formatting
    - Typosquatting detection

2. Rich User Interface

    - Color-coded status indicators
    - Interactive progress display
    - Formatted results presentation
    - Visual validation markers

3. Developer Experience
    - Intuitive command structure
    - Comprehensive error messages
    - Real-time feedback
    - Multiple command aliases

## Design Philosophy

-   **Minimalism**: Focus on essential functionality
-   **Simplicity**: One command, clear purpose
-   **Efficiency**: Fast validation with smart caching
-   **Security**: Built-in safety checks

# Installation

## Quick Start

Install via pipx:

```bash
$ pipx install pymin
```

### System Requirements

| Component | Requirement          |
| --------- | -------------------- |
| Python    | >=3.8                |
| OS        | Platform independent |

# Usage

## Command Interface

The CLI provides two command interfaces:

| Command | Description  |
| ------- | ------------ |
| pymin   | Main command |
| pm      | Short alias  |

### Basic Usage

```bash
❯ pymin
🔍 PyPI Package Name Checker

# or using alias
❯ pm
🔍 PyPI Package Name Checker
```

### Available Commands

| Command    | Description                        |
| ---------- | ---------------------------------- |
| check      | Validate package name availability |
| search     | Find similar package names         |
| venv       | Create a virtual environment       |
| activate   | Show activation command            |
| deactivate | Show deactivation command          |

### Command Examples

#### Check Package Name

```bash
$ pymin check my-package-name
┌─ PyPI Package Name Check Results ─┐
│ Package Name: my-package-name     │
│ Normalized Name: my-package-name  │
│ Valid Format: ✓                   │
│ Available: ✓                      │
│ Message: Package name available!  │
└───────────────────────────────────┘
```

#### Search Similar Names

```bash
# Default similarity (80%)
$ pm search fastapi

# Custom similarity threshold
$ pm search fastapi --threshold 0.85
```

#### Virtual Environment Management

```bash
# Create virtual environment
$ pm venv
✓ Virtual environment created at env

# Create with custom path
$ pm venv --path my_env
✓ Virtual environment created at my_env

# Show activation command
$ pm activate
┌─ Virtual Environment Activation ─┐
│ Run this command to activate:    │
│                                 │
│ source env/bin/activate         │
└─────────────────────────────────┘

# Show deactivation command
$ pm deactivate
┌─ Virtual Environment Deactivation ─┐
│ Run this command to deactivate:    │
│                                    │
│ deactivate                         │
└────────────────────────────────────┘
```

### Command Options

| Command | Option      | Description                        | Type  | Default |
| ------- | ----------- | ---------------------------------- | ----- | ------- |
| check   | name        | Target package name to validate    | str   | -       |
| search  | name        | Package name to search for         | str   | -       |
| search  | --threshold | Similarity threshold (0.0-1.0)     | float | 0.8     |
| venv    | --path      | Path to create virtual environment | str   | env     |

# License

This project is licensed under the MIT License.

# Project Structure

```
pymin/
├── src/
│   └── pypi_toolkit/
│       ├── check.py       # Package name validation service with PyPI availability checking and security analysis
│       ├── cli.py         # Command-line interface providing PyPI package name validation and search functionality
│       ├── search.py      # Package name similarity search service with PyPI integration
│       ├── security.py    # Security service for package name typosquatting detection and analysis
│       ├── similarity.py  # String similarity analysis service for package name comparison
│       ├── utils.py       # Utility functions for package name normalization and string manipulation
│       └── validators.py  # Package name validation service implementing PyPI naming conventions
├── LICENSE
├── pyproject.toml
├── readgen.toml
└── README.md
```

---

> This document was automatically generated by [ReadGen](https://github.com/TaiwanBigdata/readgen).
