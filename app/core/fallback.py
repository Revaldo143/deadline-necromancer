"""Rule-based resurrection planner.

Runs when Ollama is unreachable (or returns something unusable), so the app
is always fully demonstrable. It works purely from autopsy facts — no AI —
and is honest about it: plans it produces carry mode="fallback".
"""

from ..models.schemas import PlanStep, ProjectFacts, ResurrectionPlan


def _difficulty(revival_hours: float) -> str:
    if revival_hours <= 2:
        return "Easy"
    if revival_hours <= 6:
        return "Moderate"
    return "Herculean"


def build_fallback_plan(f: ProjectFacts) -> ResurrectionPlan:
    unfinished: list[str] = []
    steps: list[PlanStep] = []

    # --- cause of death, inferred from the evidence ---------------------
    if not f.has_commits:
        cause = "Stillborn — the repo was created, but never received a single commit."
    elif f.uncommitted_changes > 0:
        cause = (
            f"Died mid-sentence: {f.uncommitted_changes} uncommitted change(s) "
            "were left hanging in the working tree and never made it into history."
        )
    elif f.stash_count > 0:
        cause = (
            f"Interrupted mid-thought: work was stashed away "
            f"({f.stash_count} stash entr{'y' if f.stash_count == 1 else 'ies'}) and never came back."
        )
    elif f.todo_count >= 5:
        cause = (
            f"Buried under its own TODO list: {f.todo_count} unfinished markers "
            "piled up until starting again felt heavier than quitting."
        )
    else:
        cause = (
            f"Went quiet right after '{f.last_commit_message or 'the last commit'}' "
            "and was never picked up again."
        )

    # --- unfinished business --------------------------------------------
    if f.uncommitted_changes > 0:
        unfinished.append(
            f"{f.uncommitted_changes} uncommitted change(s) still sitting in the working tree"
        )
    if f.stash_count > 0:
        unfinished.append(
            f"{f.stash_count} stash entr{'y' if f.stash_count == 1 else 'ies'} never popped or dropped"
        )
    for sample in f.todo_samples:
        unfinished.append(sample)
    if not unfinished and f.last_commit_message:
        unfinished.append(f"Last words suggest more was planned: '{f.last_commit_message}'")

    # --- the plan: first step embarrassingly small ----------------------
    steps.append(
        PlanStep(
            step="Open the repo, run it, and just look around. Fix nothing yet.",
            minutes=10,
        )
    )
    if f.uncommitted_changes > 0:
        steps.append(
            PlanStep(
                step=(
                    f"Deal with the {f.uncommitted_changes} uncommitted change(s): "
                    "commit what still makes sense, discard the rest. Clean corpse, clean start."
                ),
                minutes=15,
            )
        )
    if f.stash_count > 0:
        steps.append(
            PlanStep(
                step="Pop the oldest stash and read it like a note from past-you. Keep it or drop it — decide today.",
                minutes=10,
            )
        )
    if f.todo_samples:
        steps.append(
            PlanStep(
                step=f"Tackle exactly ONE marker: {f.todo_samples[0]}",
                minutes=25,
            )
        )
    steps.append(
        PlanStep(
            step="Re-read the README, then write down the single smallest shippable next step.",
            minutes=15,
        )
    )
    steps.append(
        PlanStep(
            step="Do that one step. Nothing else. Then commit — the resurrection is official.",
            minutes=30,
        )
    )

    # --- honest hour estimates from evidence ----------------------------
    revival = 0.75 + f.todo_count * 0.2 + f.uncommitted_changes * 0.15 + f.stash_count * 0.25
    revival = round(min(max(revival, 0.5), 10.0), 1)
    restart = round(max(revival * 4, f.total_commits * 0.3, revival + 1.5), 1)

    summary = f"{f.name} is a {f.primary_language} project"
    if f.total_commits:
        summary += f" with {f.total_commits} commit{'s' if f.total_commits != 1 else ''}"
    if f.days_dead:
        summary += f", dead for {f.days_dead} day{'s' if f.days_dead != 1 else ''}"
    summary += "."
    if f.readme_line:
        summary += f' It described itself as: "{f.readme_line}".'

    return ResurrectionPlan(
        cause_of_death=cause,
        autopsy_summary=summary,
        unfinished_business=unfinished[:6],
        steps=steps[:6],
        revival_hours=revival,
        restart_hours=restart,
        difficulty=_difficulty(revival),
        mode="fallback",
    )
