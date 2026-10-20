"""Shared fixtures: build real (tiny) git repos in tmp dirs."""

import os
import subprocess
from pathlib import Path

import pytest

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.dev",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.dev",
}


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, **GIT_ENV}
    return subprocess.run(
        ["git", "-C", str(repo), *args], env=env, check=True,
        capture_output=True, text=True,
    )


@pytest.fixture
def make_repo(tmp_path):
    def _make(name="proj", commits=None, dirty=False, stash=False):
        if commits is None:
            commits = [("init commit", {"main.py": "print('hello')\n"})]
        repo = tmp_path / name
        repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-b", "main", str(repo)],
                       check=True, capture_output=True)
        git(repo, "config", "user.email", "test@example.dev")
        git(repo, "config", "user.name", "Test")
        for message, files in commits:
            for rel, content in files.items():
                target = repo / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-m", message)
        if dirty:
            (repo / "loose.txt").write_text("never committed\n", encoding="utf-8")
        if stash:
            (repo / "wip.py").write_text("wip = True\n", encoding="utf-8")
            git(repo, "add", "wip.py")
            git(repo, "stash", "push", "-m", "wip work")
        return repo

    return _make


@pytest.fixture
def empty_repo(tmp_path):
    repo = tmp_path / "empty"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(repo)],
                   check=True, capture_output=True)
    return repo
