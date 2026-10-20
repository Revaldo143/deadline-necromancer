from app.core.autopsy import autopsy_repo


def test_autopsy_reads_history_and_markers(make_repo):
    repo = make_repo(commits=[
        ("init", {"main.py": "# TODO: wire the thing\n# FIXME: and this\nprint('x')\n"}),
        ("second commit", {"util.py": "y = 2\n"}),
    ])
    facts = autopsy_repo(repo)
    assert facts.error is None
    assert facts.has_commits is True
    assert facts.total_commits == 2
    assert facts.last_commit_message == "second commit"
    assert facts.days_dead == 0
    assert facts.todo_count == 2
    assert any("TODO" in s for s in facts.todo_samples)
    assert facts.primary_language == "Python"
    assert facts.file_count == 2


def test_autopsy_sees_dirty_tree_and_stash(make_repo):
    repo = make_repo(dirty=True, stash=True)
    facts = autopsy_repo(repo)
    assert facts.uncommitted_changes >= 1
    assert facts.stash_count == 1


def test_autopsy_handles_repo_with_no_commits(empty_repo):
    facts = autopsy_repo(empty_repo)
    assert facts.error is None
    assert facts.has_commits is False
    assert facts.total_commits == 0
    assert facts.days_dead == 0


def test_autopsy_readme_line(make_repo):
    repo = make_repo(commits=[
        ("init", {"README.md": "# Cool Thing\n\nDoes stuff.\n", "a.py": "x=1\n"}),
    ])
    facts = autopsy_repo(repo)
    assert facts.readme_line == "Cool Thing"


def test_autopsy_on_non_repo(tmp_path):
    facts = autopsy_repo(tmp_path)
    assert facts.error is not None
