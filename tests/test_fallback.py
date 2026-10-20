from app.core.fallback import build_fallback_plan
from app.models.schemas import ProjectFacts


def facts(**overrides):
    base = dict(
        name="demo",
        path="/tmp/demo",
        has_commits=True,
        total_commits=12,
        days_dead=90,
        last_commit_message="wip: almost there",
        primary_language="Python",
    )
    base.update(overrides)
    return ProjectFacts(**base)


def test_fallback_plan_is_valid_and_lazy_first():
    plan = build_fallback_plan(facts(todo_count=3, todo_samples=["TODO: ship it"]))
    assert plan.mode == "fallback"
    assert len(plan.steps) >= 3
    assert plan.steps[0].minutes <= 15  # first step must be embarrassingly small
    assert plan.revival_hours < plan.restart_hours
    assert plan.difficulty in {"Easy", "Moderate", "Herculean"}
    assert plan.hours_saved > 0


def test_fallback_blames_uncommitted_changes():
    plan = build_fallback_plan(facts(uncommitted_changes=4))
    assert "mid-sentence" in plan.cause_of_death
    assert any("uncommitted" in u for u in plan.unfinished_business)


def test_fallback_handles_stillborn_repo():
    plan = build_fallback_plan(facts(has_commits=False, total_commits=0))
    assert "Stillborn" in plan.cause_of_death
    assert len(plan.steps) >= 3
