"""
Cross-platform file utilities.
Replaces Windows-specific hardcoded paths with pathlib.
"""
import os
from pathlib import Path
from typing import Union

def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent

def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory exists, creating if necessary."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def safe_read_text(path: Union[str, Path], encoding: str = "utf-8", default: str = "") -> str:
    """Safely read text file with fallback default."""
    try:
        return Path(path).read_text(encoding=encoding)
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        return default

def safe_write_text(path: Union[str, Path], content: str, encoding: str = "utf-8") -> bool:
    """Safely write text file, creating directories if needed."""
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
        return True
    except (PermissionError, UnicodeEncodeError) as e:
        return False

def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize path for cross-platform compatibility."""
    return Path(path).resolve()

def get_data_directory() -> Path:
    """Get the data directory relative to project root."""
    return get_project_root() / "data"

def get_config_file_path(filename: str) -> Path:
    """Get path to configuration file."""
    return get_project_root() / filename