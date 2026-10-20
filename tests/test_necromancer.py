import json

import pytest

from app.core import necromancer
from app.models.schemas import ProjectFacts


@pytest.fixture(autouse=True)
def _no_cache():
    necromancer.clear_cache()
    yield
    necromancer.clear_cache()


def facts():
    return ProjectFacts(
        name="demo", path="/tmp/demo", has_commits=True, total_commits=5,
        days_dead=30, last_commit_at="2026-09-20T00:00:00+00:00",
        last_commit_message="wip", primary_language="Python",
    )


class FakeTags:
    def raise_for_status(self):
        pass

    def json(self):
        return {"models": [{"name": "gemma2:2b"}]}


class FakeChat:
    def __init__(self, content):
        self._content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": self._content}}


GOOD_PLAN = json.dumps({
    "cause_of_death": "Died of neglect.",
    "autopsy_summary": "A small Python tool that got halfway.",
    "unfinished_business": ["the wip commit"],
    "steps": [
        {"step": "Open it and run it", "minutes": 10},
        {"step": "Finish the wip", "minutes": 45},
    ],
    "revival_hours": 2.0,
    "restart_hours": 9.0,
    "difficulty": "Easy",
})


def test_llm_plan_used_when_ollama_healthy(monkeypatch):
    monkeypatch.setattr(necromancer.httpx, "get", lambda *a, **k: FakeTags())
    monkeypatch.setattr(necromancer.httpx, "post", lambda *a, **k: FakeChat(GOOD_PLAN))
    plan = necromancer.generate_plan(facts())
    assert plan.mode == "llm"
    assert plan.cause_of_death == "Died of neglect."
    assert plan.revival_hours == 2.0
    assert plan.restart_hours == 9.0


def test_garbage_model_output_falls_back(monkeypatch):
    monkeypatch.setattr(necromancer.httpx, "get", lambda *a, **k: FakeTags())
    monkeypatch.setattr(necromancer.httpx, "post", lambda *a, **k: FakeChat("not json at all"))
    plan = necromancer.generate_plan(facts())
    assert plan.mode == "fallback"


def test_unreachable_ollama_falls_back(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(necromancer.httpx, "get", boom)
    plan = necromancer.generate_plan(facts())
    assert plan.mode == "fallback"


def test_status_unreachable(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("nope")

    monkeypatch.setattr(necromancer.httpx, "get", boom)
    reachable, available = necromancer.ollama_status()
    assert reachable is False
    assert available is None


def test_bad_numbers_are_clamped(monkeypatch):
    bad = json.loads(GOOD_PLAN)
    bad["revival_hours"] = 5000
    bad["restart_hours"] = 1  # less than revival — must be repaired
    bad["difficulty"] = "Impossible"
    bad["steps"] = [{"step": "x", "minutes": 99999}, {"step": "y", "minutes": 5}]
    monkeypatch.setattr(necromancer.httpx, "get", lambda *a, **k: FakeTags())
    monkeypatch.setattr(necromancer.httpx, "post", lambda *a, **k: FakeChat(json.dumps(bad)))
    plan = necromancer.generate_plan(facts())
    assert plan.mode == "llm"
    assert plan.revival_hours <= 40
    assert plan.restart_hours > plan.revival_hours
    assert plan.difficulty in {"Easy", "Moderate", "Herculean"}
    assert all(s.minutes <= 480 for s in plan.steps)
