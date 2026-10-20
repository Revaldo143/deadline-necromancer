"""HTTP API: health, scan (find + autopsy), resurrect (plan generation)."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..core import necromancer
from ..core.autopsy import autopsy_repo
from ..core.scanner import find_repos, is_repo
from ..models.schemas import (
    HealthResponse,
    ResurrectRequest,
    ResurrectResponse,
    ScanRequest,
    ScanResponse,
)

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    reachable, available = necromancer.ollama_status()
    return HealthResponse(
        status="ok",
        ollama_reachable=reachable,
        model=settings.MODEL,
        model_available=available,
        default_scan_path=settings.DEFAULT_SCAN_PATH,
    )


@router.post("/scan", response_model=ScanResponse)
def scan(req: ScanRequest) -> ScanResponse:
    path_val = (req.path or "").strip().strip('"\'')
    raw = path_val if path_val else settings.DEFAULT_SCAN_PATH
    root = Path(raw).expanduser()
    if not root.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {raw}")
    if not root.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a folder: {raw}")

    repos = find_repos(root, max_depth=settings.MAX_SCAN_DEPTH)
    facts = [autopsy_repo(repo) for repo in repos]

    # Readable repos first (most recently deceased first), broken ones last.
    facts.sort(key=lambda f: (f.error is not None, -(f.days_dead)))
    return ScanResponse(path=str(root), projects=facts)


@router.post("/resurrect", response_model=ResurrectResponse)
def resurrect(req: ResurrectRequest) -> ResurrectResponse:
    raw = (req.path or "").strip().strip('"\'')
    root = Path(raw).expanduser()
    if not root.exists() or not is_repo(root):
        raise HTTPException(status_code=404, detail=f"Not a git repository: {req.path}")

    facts = autopsy_repo(root)
    if facts.error:
        raise HTTPException(status_code=422, detail=facts.error)

    plan = necromancer.generate_plan(facts, force=req.force)
    return ResurrectResponse(project=facts, plan=plan, hours_saved=plan.hours_saved)
