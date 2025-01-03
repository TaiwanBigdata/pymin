# PyMin

### pymin (0.0.1)

PyMin embodies Python's minimalist philosophy: a focused tool that does one thing exceptionally well. The name reflects our commitment to minimalism - minimal configuration, minimal complexity, but maximum effectiveness in Python development workflow.

Just as Python emphasizes readability and simplicity, PyMin provides a clean, intuitive interface for package management and development environment setup. No unnecessary features, no complex configurations - just straightforward, reliable development tools.

The name "PyMin" carries dual meanings:

**In English: "Py" (Python) + "Min" (Minimal/Minimalist)**
- Represents our commitment to minimalist design and focused functionality
- Follows Python's "Simple is better than complex" philosophy

**In Taiwanese: "歹命" (Pháiⁿ-miā)**
- A humorous reference to the common challenges in Python development
- Reflects developers' daily struggles with environment setup and package management
- Turns development pain points into a playful and helpful tool

This duality in naming captures both our design philosophy and the real-world problems we're solving, while adding a touch of Taiwanese developer humor to the Python ecosystem.

A CLI tool for PyPI package management, providing package name validation, virtual environment management, and project information display with rich output formatting.

#### Package Name Validation
![Package Name Check](docs/images/check_package.png)

#### Environment Information
![Environment Information](docs/images/env_info.png)


# Features

## Core Features

1. Package Name Validation
   - Real-time PyPI availability check
   - PEP 503 naming convention validation
   - Standardized name formatting
   - Similar package name search

2. Environment Management
   - Virtual environment creation and management
   - Project information display
   - System environment inspection
   - Development setup assistance

3. Rich User Interface
   - Color-coded status indicators
   - Formatted results presentation
   - Clear error messages
   - Intuitive command structure

4. Developer Experience
   - Minimal configuration required
   - Straightforward workflows
   - Real-time feedback
   - Comprehensive environment info


# Installation

## Quick Start

Install via pipx:
```bash
$ pipx install pymin
```

### System Requirements
| Component | Requirement                |
|-----------|----------------------------|
| Python    | >=3.8 |
| OS        | Platform independent       |


# Usage

## Command Interface

The CLI provides two command interfaces:

| Command | Description                       |
|---------|----------------------------------|
| pm      | Main command (recommended)        |
| pymin   | Alternative full name            |

### Available Commands

| Command    | Description                          |
|------------|--------------------------------------|
| check      | Check package name availability      |
| search     | Search for similar package names     |
| venv       | Create a virtual environment         |
| activate   | Show venv activation command         |
| deactivate | Show venv deactivation command       |
| info       | Show environment information         |

### Command Examples

#### Check Package Name
```bash
$ pm check my-package-name
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

#### Create Virtual Environment
```bash
# Create with default name 'env'
$ pm venv

# Create with custom name
$ pm venv my_env
```

### Command Details

#### check
Check if a package name is available on PyPI
```bash
pm check NAME
```
- `NAME`: Package name to validate (required)

#### search
Search for similar package names on PyPI
```bash
pm search NAME [--threshold VALUE]
```
- `NAME`: Package name to search for (required)
- `--threshold VALUE`: Similarity threshold, 0.0-1.0 (default: 0.8)

#### venv
Create a virtual environment
```bash
pm venv [NAME]
```
- `NAME`: Virtual environment name (default: env)

#### activate, deactivate
Show virtual environment activation/deactivation commands
```bash
pm activate
pm deactivate
```

#### info
Display environment information
```bash
pm info
```


# License

This project is licensed under the MIT License.


# Project Structure

```
pymin/
├── docs/
│   └── images/
│       ├── check_package.png
│       └── env_info.png
├── src/
│   └── pymin/
│       ├── __main__.py        # Allow direct execution of the package
│       ├── check.py           # Package name validation service with PyPI availability checking and security analysis
│       ├── cli.py             # Command-line interface providing PyPI package name validation and search functionality
│       ├── search.py          # Package name similarity search service with PyPI integration
│       ├── security.py        # Security service for package name typosquatting detection and analysis
│       ├── similarity.py      # String similarity analysis service for package name comparison
│       ├── utils.py           # Utility functions for package name normalization and string manipulation
│       ├── validators.py      # Package name validation service implementing PyPI naming conventions
│       └── venv.py            # CLI environment management service
├── LICENSE
├── pyproject.toml
├── readgen.toml
└── README.md
```


---
> This document was automatically generated by [ReadGen](https://github.com/TaiwanBigdata/readgen).
