# Python Project Template

[![Consistency Check](https://github.com/jnoelvictorino/python-template/actions/workflows/consistency-check.yml/badge.svg)](https://github.com/jnoelvictorino/python-template/actions/workflows/consistency-check.yml)

A modern Python project template with Dev Container and Docker support.

## Tech Stack

- **Python 3.12** with modern package management
- **uv** for fast, efficient dependency management
- **Docker** support for containerized applications
- **Dev Container** for consistent development environment
- **VS Code** extensions for Python development
- **GitHub Actions** for CI/CD and consistency checks
- **pyproject.toml** for project metadata and dependency management
- **Dependency groups** for organizing project features

## Project Structure

```
.
├── .devcontainer/      # Dev Container configuration
├── .github/            # GitHub configurations
│   ├── actions/        # GitHub automation scripts/actions
│   └── workflows/      # GitHub Actions workflows
├── .vscode/            # VS Code settings
│   └── settings.json   # VS Code editor settings
├── .env.template       # Environment variables template
├── .gitignore          # Git ignore rules
├── .python-version     # Python version specification
├── Dockerfile          # Container image definition
└── pyproject.toml      # Project metadata and dependencies

```

## Getting Started

### Prerequisites

#### For Containerized Development
- Docker and Docker Compose (for containerized development)
- VS Code with Remote - Containers extension

#### For Local Development
- Python 3.12 installed (use pyenv or similar)

### Common Setup

Use this checklist whenever you rename the template or change the environment:

- [ ] Project name
	- [ ] [pyproject.toml](pyproject.toml): `name`
  - [ ] [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json): `name`.
  - [ ] [python-template.code-workspace](python-template.code-workspace): `python-template`
- [ ] Python version
	- [ ] [.python-version](.python-version): `3.12`
	- [ ] [pyproject.toml](pyproject.toml): `requires-python = ">=3.12"`
	- [ ] [Dockerfile](Dockerfile): `FROM python:3.12-slim`
- [ ] [Dependency Groups](#dependency-groups)
	- [ ] [pyproject.toml:11](pyproject.toml#L11): base dependencies
  - [ ] [pyproject.toml:22](pyproject.toml#L22): dependency groups
- [ ] Coding and Editor style
  - Indentation: 2-space
  - Line length: 88 characters
  - Linters: Ruff & Pylint
  - Formatter/editor settings: VS Code
  - Configuration files:
    - [pyproject.toml:41-46](pyproject.toml#L41-L46): Ruff line length and indentation, plus Pylint indentation
    - [.vscode/settings.json](.vscode/settings.json): the whole file, including `editor.insertSpaces`, `editor.tabSize`, and `editor.detectIndentation`

### Setup with Dev Container

1. Open the project in VS Code
2. Click "Reopen in Container" when prompted
3. The container will build automatically with all dependencies

### Setup without Dev Container

1. Activate virtual environment
    - Unix: `source .venv/bin/activate`
    - Windows: `.venv\Scripts\activate`
2. Install `uv`
    - `pip install uv`
3. Sync dependencies
    - `uv sync --all-groups`

## Dependency Groups

This project uses uv's dependency groups for organized feature management:

```bash
# Install base dependencies plus all dependency groups
uv sync --all-groups

# Install specific groups
uv sync --group=dashboard
uv sync --group=train
uv sync --group=hpc
```

### Available Groups

- **dashboard**: Streamlit and Plotly for UI/visualization
- **train**: Machine learning and MLflow for training pipelines
- **hpc**: Combines train and dashboard groups for high-performance computing

## Configuration

### Environment Variables

Copy `.env.template` to `.env` and update with your values:

```bash
cp .env.template .env
```

Never commit `.env` — it's in `.gitignore`.

## Development

### Python Version

* 3.12 (in `.python-version`)
* Used by dev containers and tools like `pyenv`.

### Code Style

- **Line length**: 88 characters (Ruff setting)
- **Indentation**: 2 spaces (Ruff, Pylint, and VS Code settings)
- **Formatting**: 2 spaces (VS Code)
- **Linters**: Ruff & Pylint (configured in `pyproject.toml`)

### Consistency Checks

This template includes CI and script validation to prevent config drift:

- **Project name consistency**: Should match 
  - `pyproject.toml` project name
  - `.devcontainer/devcontainer.json` container name.
- **Python version consistency**: Should match
  - `.python-version`
  - `pyproject.toml` (`requires-python` minimum)
  - `Dockerfile` base Python tag must match.


#### Manual Consistency Check
```bash
python .github/actions/check-consistency/check_consistency.py
```

### Automated Consistency Check via Github Actions
```text
.github/workflows/consistency-check.yml
```

### Jupyter Notebooks

The environment includes Jupyter support:

```bash
jupyter notebook
```

## License

MIT
