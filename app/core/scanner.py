"""Finds git repositories ("corpses") under a root folder.

Deliberately conservative: never descends into a repo it already found,
never enters dependency/vendor directories, and silently skips anything
it cannot read. A scan must never crash because one folder is weird.
"""

from pathlib import Path

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".next",
    "target",
    ".tox",
}


def is_repo(path: Path) -> bool:
    """A directory is a repo if it contains a `.git` entry (dir or file)."""
    try:
        return (path / ".git").exists()
    except OSError:
        return False


def find_repos(root: str | Path, max_depth: int = 3) -> list[Path]:
    """Return every git repo at or below `root`, up to `max_depth` levels."""
    root = Path(root).expanduser()
    if not root.exists() or not root.is_dir():
        return []
    if is_repo(root):
        return [root]

    found: list[Path] = []

    def walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(directory.iterdir())
        except (PermissionError, OSError):
            return
        for entry in entries:
            try:
                if not entry.is_dir():
                    continue
            except OSError:
                continue
            if entry.name in SKIP_DIRS or entry.name.startswith("."):
                continue
            if is_repo(entry):
                found.append(entry)
            else:
                walk(entry, depth + 1)

    walk(root, 1)
    return sorted(found)
