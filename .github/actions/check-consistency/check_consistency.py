import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PYPROJECT = ROOT / "pyproject.toml"
DEVCONTAINER = ROOT / ".devcontainer" / "devcontainer.json"
PYTHON_VERSION_FILE = ROOT / ".python-version"
DOCKERFILE = ROOT / "Dockerfile"


def find_workspace_files():
  return sorted(ROOT.glob("*.code-workspace"))


def read_pyproject():
  if sys.version_info >= (3, 11):
    import tomllib  # pylint: disable=import-outside-toplevel
  else:
    import tomli as tomllib  # type: ignore # pylint: disable=import-outside-toplevel

  with PYPROJECT.open("rb") as f:
    return tomllib.load(f)


def read_devcontainer():
  with DEVCONTAINER.open("r", encoding="utf-8") as f:
    return json.load(f)


def extract_container_name(run_args):
  if not isinstance(run_args, list):
    return None
  for i, value in enumerate(run_args):
    if value == "--name" and i + 1 < len(run_args):
      return run_args[i + 1]
  return None


def extract_min_python_version(spec: str):
  match = re.search(r">=\s*([0-9]+(?:\.[0-9]+){1,2})", spec or "")
  return match.group(1) if match else None


def extract_docker_python_version(first_line: str):
  match = re.search(
    r"^FROM\s+python:([0-9]+(?:\.[0-9]+){1,2})",
    first_line.strip(),
    re.IGNORECASE,
  )
  return match.group(1) if match else None


def main() -> None:
  errors = []

  pyproject = read_pyproject()
  devcontainer = read_devcontainer()

  project_name = pyproject.get("project", {}).get("name")
  container_name = extract_container_name(devcontainer.get("runArgs", []))

  if not project_name:
    errors.append("Missing project.name in pyproject.toml")
  if not container_name:
    errors.append("Missing runArgs --name in .devcontainer/devcontainer.json")
  if project_name and container_name and project_name != container_name:
    errors.append(
      "Name mismatch: "
      f"pyproject project.name='{project_name}' "
      f"vs devcontainer runArgs --name='{container_name}'"
    )

  workspace_files = find_workspace_files()
  if not workspace_files:
    errors.append("Missing *.code-workspace file in repository root")
  elif len(workspace_files) > 1:
    workspace_file_list = ", ".join(p.name for p in workspace_files)
    errors.append(
      "Multiple *.code-workspace files found in repository root: "
      f"{workspace_file_list}"
    )
  elif project_name:
    workspace_filename = workspace_files[0].name
    expected_workspace_filename = f"{project_name}.code-workspace"
    if workspace_filename != expected_workspace_filename:
      errors.append(
        "Workspace filename mismatch: "
        f"found '{workspace_filename}' "
        f"but expected '{expected_workspace_filename}'"
      )

  requires_python = pyproject.get("project", {}).get("requires-python")
  pyproject_version = extract_min_python_version(requires_python)
  python_version_file = PYTHON_VERSION_FILE.read_text(encoding="utf-8").strip()

  docker_lines = DOCKERFILE.read_text(encoding="utf-8").splitlines()
  docker_first_line = docker_lines[0] if docker_lines else ""
  docker_version = extract_docker_python_version(docker_first_line)

  if not pyproject_version:
    errors.append("Could not parse minimum version from project.requires-python")
  if not python_version_file:
    errors.append("Missing value in .python-version")
  if not docker_version:
    errors.append("Could not parse Python version from Dockerfile FROM line")

  if pyproject_version and python_version_file and pyproject_version != python_version_file:
    errors.append(
      "Python version mismatch: "
      f"pyproject requires-python minimum='{pyproject_version}' "
      f"vs .python-version='{python_version_file}'"
    )
  if pyproject_version and docker_version and pyproject_version != docker_version:
    errors.append(
      "Python version mismatch: "
      f"pyproject requires-python minimum='{pyproject_version}' "
      f"vs Dockerfile='{docker_version}'"
    )

  if errors:
    for error in errors:
      print(f"[FAIL] {error}")
    sys.exit(1)

  print("[PASS] Consistency checks passed")
  print(f"  project name: {project_name}")
  print(f"  python version: {pyproject_version}")


if __name__ == "__main__":
  main()
