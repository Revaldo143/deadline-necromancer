"""The necromancer: turns autopsy facts into a resurrection plan using a
local open-weight model (Gemma) served by Ollama.

Design rules:
- The LLM is the brain, but it is never a single point of failure. Any
  problem — Ollama down, model missing, malformed JSON — degrades to the
  rule-based fallback planner instead of an error.
- Model output is treated as untrusted: parsed defensively, numbers are
  clamped to sane ranges, and the plan is validated before it is returned.
- Results are cached per repo state, so re-opening a project is instant.
"""

import json
import re

import httpx

from ..config import settings
from ..models.schemas import PlanStep, ProjectFacts, ResurrectionPlan
from .fallback import build_fallback_plan

_cache: dict[str, ResurrectionPlan] = {}

VALID_DIFFICULTIES = {"Easy", "Moderate", "Herculean"}

SYSTEM_PROMPT = """You are the Deadline Necromancer, an AI that resurrects abandoned software projects.
You are given the autopsy of a dead git repository. Your job is to explain how it died and produce a
realistic, kind, lazy-first plan to bring it back to life. The first plan step must be embarrassingly
small (15 minutes or less) — momentum beats ambition. Be specific: reference the actual TODOs, the
last commit message and the unfinished work you were given. A little dark humour is welcome, but the
plan must be genuinely useful. Respond with JSON only, no markdown fences, matching exactly this shape:
{
  "cause_of_death": "one or two sentences",
  "autopsy_summary": "two or three sentences: what this project was and how far it got",
  "unfinished_business": ["short item", "..."],
  "steps": [{"step": "concrete action", "minutes": 10}],
  "revival_hours": 2.5,
  "restart_hours": 12.0,
  "difficulty": "Easy" | "Moderate" | "Herculean"
}
Rules: 3 to 6 steps; restart_hours must be bigger than revival_hours (rebuilding from scratch always
costs more than reviving); difficulty is Easy if revival_hours <= 2, Moderate if <= 6, else Herculean."""


def ollama_status() -> tuple[bool, bool | None]:
    """Returns (reachable, model_available). Never raises."""
    try:
        resp = httpx.get(
            f"{settings.OLLAMA_HOST}/api/tags", timeout=settings.OLLAMA_HEALTH_TIMEOUT
        )
        resp.raise_for_status()
        models = [m.get("name", "") for m in resp.json().get("models", [])]
        base = settings.MODEL.split(":")[0]
        available = any(
            name == settings.MODEL or name.split(":")[0] == base for name in models
        )
        return True, available
    except Exception:
        return False, None


def _facts_block(f: ProjectFacts) -> str:
    lines = [
        f"Project name: {f.name}",
        f"Primary language: {f.primary_language}",
        f"Total commits: {f.total_commits}",
        f"Active span: {f.active_span_days} days",
        f"Days since last commit (days dead): {f.days_dead}",
        f"Last commit message: {f.last_commit_message or '(none)'}",
        f"README first line: {f.readme_line or '(no README)'}",
        f"Uncommitted changes in working tree: {f.uncommitted_changes}",
        f"Stashes left behind: {f.stash_count}",
        f"TODO/FIXME/HACK markers in code: {f.todo_count}",
    ]
    for sample in f.todo_samples:
        lines.append(f"  - marker: {sample}")
    return "\n".join(lines)


def _clamp(value: float, low: float, high: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return min(max(number, low), high)


def _parse_plan(raw: str, f: ProjectFacts) -> ResurrectionPlan | None:
    """Parse and sanitize model JSON. Returns None if it is unusable."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None

    cause = str(data.get("cause_of_death", "")).strip()
    summary = str(data.get("autopsy_summary", "")).strip()
    if not cause or not summary:
        return None

    steps: list[PlanStep] = []
    for item in data.get("steps", [])[:6]:
        if isinstance(item, dict) and str(item.get("step", "")).strip():
            minutes = int(_clamp(item.get("minutes", 20), 1, 480, 20))
            steps.append(PlanStep(step=str(item["step"]).strip()[:300], minutes=minutes))
    if len(steps) < 2:
        return None

    revival = _clamp(data.get("revival_hours"), 0.25, 40.0, 2.0)
    restart = _clamp(data.get("restart_hours"), 0.5, 200.0, revival * 4)
    if restart <= revival:
        restart = round(revival * 4, 1)

    difficulty = str(data.get("difficulty", "")).strip()
    if difficulty not in VALID_DIFFICULTIES:
        difficulty = "Easy" if revival <= 2 else "Moderate" if revival <= 6 else "Herculean"

    unfinished = [
        str(x).strip()[:200] for x in data.get("unfinished_business", []) if str(x).strip()
    ][:6]

    return ResurrectionPlan(
        cause_of_death=cause[:500],
        autopsy_summary=summary[:800],
        unfinished_business=unfinished,
        steps=steps,
        revival_hours=round(revival, 1),
        restart_hours=round(restart, 1),
        difficulty=difficulty,
        mode="llm",
    )


def _llm_plan(f: ProjectFacts) -> ResurrectionPlan | None:
    payload = {
        "model": settings.MODEL,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.4},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "AUTOPSY REPORT\n" + _facts_block(f)},
        ],
    }
    resp = httpx.post(
        f"{settings.OLLAMA_HOST}/api/chat", json=payload, timeout=settings.OLLAMA_TIMEOUT
    )
    resp.raise_for_status()
    content = resp.json().get("message", {}).get("content", "")
    return _parse_plan(content, f)


def generate_plan(f: ProjectFacts, force: bool = False) -> ResurrectionPlan:
    """Full necromancy for one project. Falls back gracefully, always returns."""
    key = f"{f.path}@{f.last_commit_at or 'no-commits'}"
    if not force and key in _cache:
        return _cache[key]

    plan: ResurrectionPlan | None = None
    reachable, _ = ollama_status()
    if reachable:
        try:
            plan = _llm_plan(f)
        except Exception:
            plan = None
    if plan is None:
        plan = build_fallback_plan(f)

    _cache[key] = plan
    return plan


def clear_cache() -> None:
    _cache.clear()
