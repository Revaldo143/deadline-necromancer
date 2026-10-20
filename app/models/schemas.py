"""Pydantic schemas shared by the autopsy engine, the LLM layer and the API."""

from typing import Optional

from pydantic import BaseModel, Field


class ProjectFacts(BaseModel):
    """Everything the autopsy can learn about a repo without any AI."""

    name: str
    path: str
    error: Optional[str] = None

    has_commits: bool = False
    first_commit_at: Optional[str] = None  # ISO 8601
    last_commit_at: Optional[str] = None  # ISO 8601
    days_dead: int = 0
    total_commits: int = 0
    active_span_days: int = 0
    last_commit_message: str = ""

    todo_count: int = 0
    todo_samples: list[str] = Field(default_factory=list)

    uncommitted_changes: int = 0
    stash_count: int = 0
    branch_count: int = 0
    current_branch: str = ""

    readme_line: str = ""
    primary_language: str = "Unknown"
    languages: list[str] = Field(default_factory=list)
    file_count: int = 0


class PlanStep(BaseModel):
    step: str
    minutes: int


class ResurrectionPlan(BaseModel):
    """The necromancy output — produced by Gemma, or by the fallback planner."""

    cause_of_death: str
    autopsy_summary: str
    unfinished_business: list[str] = Field(default_factory=list)
    steps: list[PlanStep] = Field(default_factory=list)
    revival_hours: float
    restart_hours: float
    difficulty: str  # Easy | Moderate | Herculean
    mode: str  # "llm" | "fallback"

    @property
    def hours_saved(self) -> float:
        return round(max(self.restart_hours - self.revival_hours, 0.0), 1)


class ScanRequest(BaseModel):
    path: Optional[str] = None


class ScanResponse(BaseModel):
    path: str
    projects: list[ProjectFacts]


class ResurrectRequest(BaseModel):
    path: str
    force: bool = False


class ResurrectResponse(BaseModel):
    project: ProjectFacts
    plan: ResurrectionPlan
    hours_saved: float


class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    model: str
    model_available: Optional[bool] = None
    default_scan_path: str
