from pathlib import Path

from app.core.scanner import find_repos, is_repo


def test_finds_repos_and_skips_plain_folders(make_repo, tmp_path):
    a = make_repo("alpha")
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "readme.txt").write_text("not a repo")
    group = tmp_path / "group"
    group.mkdir()
    b = make_repo("group/beta")

    found = find_repos(tmp_path)
    assert a in found and b in found
    assert len(found) == 2


def test_root_itself_can_be_a_repo(make_repo, tmp_path):
    repo = make_repo("solo")
    assert find_repos(repo) == [repo]


def test_node_modules_are_never_entered(make_repo, tmp_path):
    nm = tmp_path / "node_modules"
    nm.mkdir()
    hidden = make_repo("node_modules/hidden-repo")
    visible = make_repo("visible")
    found = find_repos(tmp_path)
    assert visible in found
    assert hidden not in found


def test_missing_root_returns_empty(tmp_path):
    assert find_repos(tmp_path / "does-not-exist") == []


def test_is_repo(empty_repo, tmp_path):
    assert is_repo(empty_repo) is True
    assert is_repo(tmp_path) is False
