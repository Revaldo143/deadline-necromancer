"""The autopsy: pure git archaeology. No AI involved.

Reads a repository's history and working tree and produces a ProjectFacts
record: when it died, how it lived, what it left unfinished. Every git call
is timeout-guarded and failure-tolerant — a broken repo yields an `error`
field, never an exception.
"""

import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ..models.schemas import ProjectFacts

GIT_TIMEOUT = 15
MAX_TODO_LINES = 500

EXT_TO_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".html": "HTML",
    ".css": "CSS",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".sh": "Shell",
    ".ipynb": "Jupyter",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".dart": "Dart",
    ".vue": "Vue",
    ".sql": "SQL",
}

TODO_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b[:\s]*(.*)")
README_NAMES = ("README.md", "readme.md", "README.rst", "README.txt", "README")


def _git(repo: Path, *args: str) -> tuple[bool, str]:
    """Run a git command in `repo`. Returns (success, stdout). Never raises."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
        )
        return result.returncode == 0, (result.stdout or "").strip()
    except (subprocess.TimeoutExpired, OSError):
        return False, ""


def _iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _readme_line(repo: Path) -> str:
    for name in README_NAMES:
        candidate = repo / name
        try:
            if candidate.is_file():
                for raw in candidate.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = raw.strip().lstrip("#").strip()
                    if line:
                        return line[:160]
        except OSError:
            continue
    return ""


def _todos(repo: Path) -> tuple[int, list[str]]:
    """Count TODO/FIXME/HACK/XXX markers in the committed tree (HEAD)."""
    ok, out = _git(
        repo, "grep", "-I", "-n", "-E", r"\b(TODO|FIXME|HACK|XXX)\b", "HEAD", "--", "."
    )
    if not ok or not out:
        return 0, []
    lines = out.splitlines()[:MAX_TODO_LINES]
    samples: list[str] = []
    for line in lines:
        # git grep format: HEAD:path/to/file.py:42:    # TODO: fix this
        parts = line.split(":", 3)
        text = parts[3].strip() if len(parts) == 4 else line.strip()
        match = TODO_PATTERN.search(text)
        if match:
            note = (match.group(2) or "").strip()
            label = match.group(1) + (f": {note}" if note else "")
            samples.append(label[:140])
        if len(samples) >= 5:
            break
    return len(lines), samples


def _languages(repo: Path) -> tuple[str, list[str], int]:
    ok, out = _git(repo, "ls-files")
    if not ok or not out:
        return "Unknown", [], 0
    files = [f for f in out.splitlines() if f.strip()]
    counter: Counter[str] = Counter()
    for name in files:
        lang = EXT_TO_LANGUAGE.get(Path(name).suffix.lower())
        if lang:
            counter[lang] += 1
    ranked = [lang for lang, _ in counter.most_common(3)]
    primary = ranked[0] if ranked else "Unknown"
    return primary, ranked, len(files)


def autopsy_repo(repo: Path) -> ProjectFacts:
    """Perform a full autopsy on one repository."""
    repo = Path(repo)
    facts = ProjectFacts(name=repo.name, path=str(repo))

    ok, _ = _git(repo, "rev-parse", "--git-dir")
    if not ok:
        facts.error = "Not a readable git repository."
        return facts

    # --- commit history -------------------------------------------------
    ok, out = _git(repo, "log", "--format=%ct%x09%s")
    if ok and out:
        rows = []
        for line in out.splitlines():
            ts_str, _, subject = line.partition("\t")
            try:
                rows.append((int(ts_str), subject.strip()))
            except ValueError:
                continue
        if rows:
            facts.has_commits = True
            facts.total_commits = len(rows)
            last_ts, last_subject = rows[0]
            first_ts = rows[-1][0]
            facts.last_commit_at = _iso(last_ts)
            facts.first_commit_at = _iso(first_ts)
            facts.last_commit_message = last_subject[:200]
            now_ts = int(datetime.now(tz=timezone.utc).timestamp())
            facts.days_dead = max((now_ts - last_ts) // 86400, 0)
            facts.active_span_days = max((last_ts - first_ts) // 86400, 0)

    # --- working tree ---------------------------------------------------
    ok, out = _git(repo, "status", "--porcelain")
    if ok:
        facts.uncommitted_changes = len([ln for ln in out.splitlines() if ln.strip()])

    ok, out = _git(repo, "stash", "list")
    if ok:
        facts.stash_count = len([ln for ln in out.splitlines() if ln.strip()])

    ok, out = _git(repo, "branch", "--format=%(refname:short)")
    if ok:
        facts.branch_count = len([ln for ln in out.splitlines() if ln.strip()])

    ok, out = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if ok:
        facts.current_branch = out

    # --- content --------------------------------------------------------
    if facts.has_commits:
        facts.todo_count, facts.todo_samples = _todos(repo)
    facts.primary_language, facts.languages, facts.file_count = _languages(repo)
    facts.readme_line = _readme_line(repo)

    return facts
