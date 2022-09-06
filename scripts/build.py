"""Builds the project."""
import json
import os
import subprocess
from typing import Optional


def check_poetry_installed():
    """Checks if poetry is installed.

    Raises:
        ValueError: If poetry is not installed.
    """
    try:
        subprocess.check_output(["poetry", "--version"])
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise ValueError("Please install poetry https://python-poetry.org/docs/ first.")


def get_poetry_version() -> str:
    """Get the version of the package.

    Returns:
        str: The version of the package.
    """
    return subprocess.check_output(["poetry", "version", "-s"]).decode("utf-8").strip()


def poetry_build(format: Optional[str] = None) -> str:
    """Builds package and returns the path to the built package.

    Args:
        format (str): Optional; Limit the format to either sdist or wheel.

    Raises:
        ValueError: If the build failed.

    Returns:
        str: The full path to the built package.
    """
    cmd = ["poetry", "build"]
    if format:
        cmd.append(f"--format={format}")
    try:
        subprocess.check_output(cmd)
    except subprocess.CalledProcessError:
        raise ValueError("Failed to build package.")

    # Check if dist directory exists
    dist_dir = os.path.join(os.getcwd(), "dist")
    if not os.path.exists(dist_dir):
        raise ValueError("Failed to build package.")

    # Find all .tar.gz files in dist directory with version
    build_extension = ".tar.gz"
    if format == "wheel":
        build_extension = ".whl"
    version = get_poetry_version()
    files = [
        f for f in os.listdir(dist_dir) if f.endswith(build_extension) and version in f
    ]

    if len(files) != 1:
        raise ValueError("Failed to build package.")

    return os.path.join(dist_dir, files[0])


def poetry_export(file_name: str = "requirements.txt") -> str:
    """Exports the project.

    Args:
        file_name (str): The name of the file to export to.

    Raises:
        ValueError: If the export failed.

    Returns:
        str: The full path to the exported file.
    """
    cmd = [
        "poetry",
        "export",
        "--format",
        file_name,
        "--output",
        file_name,
        "--without-hashes",
    ]
    try:
        subprocess.check_output(cmd)
    except subprocess.CalledProcessError:
        raise ValueError("Failed to export project.")

    # Check if requirements.txt exists
    requirements_path = os.path.join(os.getcwd(), file_name)
    if not os.path.exists(requirements_path):
        raise ValueError("Failed to export project.")

    return requirements_path


def main():
    """Builds the project."""
    check_poetry_installed()
    build_path = poetry_build()
    build_name = os.path.basename(build_path)
    requirements_path = poetry_export()
    res = json.dumps(
        {
            "build_path": build_path,
            "build_name": build_name,
            "requirements": requirements_path,
        }
    )
    print(res)


if __name__ == "__main__":
    main()
