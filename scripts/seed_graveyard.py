"""Conjure a demo graveyard: three abandoned repos with believable histories.

Usage:
    python scripts/seed_graveyard.py [target_dir]

Default target: ./sample_graveyard  (then scan that folder in the UI)

Each repo gets backdated commits, TODO markers, and its own distinctive
manner of death — one left changes uncommitted, one left a stash behind,
one simply faded away. Safe to re-run: the target folder is recreated.
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

AUTHOR = {"GIT_AUTHOR_NAME": "Past You", "GIT_AUTHOR_EMAIL": "past@you.dev",
          "GIT_COMMITTER_NAME": "Past You", "GIT_COMMITTER_EMAIL": "past@you.dev"}


def run(repo: Path, *args: str, env_extra: dict | None = None) -> None:
    env = {**os.environ, **AUTHOR, **(env_extra or {})}
    subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                   capture_output=True, text=True)


def commit(repo: Path, days_ago: int, message: str, files: dict[str, str]) -> None:
    for rel, content in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    when = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    stamp = f"@{int(when.timestamp())} +0000"
    run(repo, "add", "-A")
    run(repo, "commit", "-m", message,
        env_extra={"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp})


def init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True,
                   capture_output=True, text=True)
    run(path, "config", "user.email", "past@you.dev")
    run(path, "config", "user.name", "Past You")


def fitquest(root: Path) -> None:
    """Died ~7 months ago, mid-auth-feature, changes left uncommitted."""
    repo = root / "fitquest-api"
    init_repo(repo)
    commit(repo, 228, "init: FastAPI skeleton for FitQuest", {
        "README.md": "# FitQuest API\n\nTrack workouts, streaks and PRs. Gamified fitness for people who hate fitness apps.\n",
        "requirements.txt": "fastapi\nuvicorn\n",
        "app/main.py": "from fastapi import FastAPI\n\napp = FastAPI(title='FitQuest')\n",
    })
    commit(repo, 224, "add user model + workout CRUD", {
        "app/models.py": "class User:\n    pass\n\nclass Workout:\n    pass\n",
        "app/routes.py": "# TODO: add pagination to /workouts\n",
    })
    commit(repo, 219, "streaks engine v1", {
        "app/streaks.py": "def current_streak(days):\n    # FIXME: timezone handling is wrong for IST\n    return 0\n",
    })
    commit(repo, 214, "wip: JWT auth halfway, token refresh broken — fix tomorrow", {
        "app/auth.py": (
            "import jwt  # TODO: move secret to env before anyone sees this\n\n"
            "SECRET = 'hunter2'\n\n"
            "def login(user):\n    ...  # TODO: refresh tokens\n"
        ),
    })
    # Left hanging in the working tree, never committed:
    (repo / "app/auth.py").write_text(
        "import os\nimport jwt\n\nSECRET = os.environ['JWT_SECRET']\n\n"
        "def login(user):\n    ...  # still TODO: refresh tokens\n",
        encoding="utf-8",
    )
    (repo / "NOTES.md").write_text(
        "auth is 90% done, just need refresh tokens + tests. tomorrow for sure.\n",
        encoding="utf-8",
    )


def pumpfolio(root: Path) -> None:
    """Died ~11 months ago chasing a websocket feature that never landed."""
    repo = root / "pumpfolio"
    init_repo(repo)
    commit(repo, 340, "init: pumpfolio — portfolio tracker for degens", {
        "README.md": "# Pumpfolio\n\nA totally serious crypto portfolio dashboard.\n",
        "package.json": '{\n  "name": "pumpfolio",\n  "version": "0.1.0"\n}\n',
        "index.html": "<h1>pumpfolio</h1>\n",
    })
    commit(repo, 336, "coingecko prices, hardcoded and proud", {
        "src/prices.js": "// TODO: cache this, we are hammering the free tier\nconst KEY = 'demo';\n",
    })
    commit(repo, 331, "chart goes up (the line, not the portfolio)", {
        "src/chart.js": "export function draw() { /* canvas magic */ }\n// HACK: resize handler leaks listeners\n",
    })
    commit(repo, 329, "start websocket live prices — wip", {
        "src/live.js": "// TODO: reconnect logic\n// TODO: actually render the ticks\nexport const ws = null;\n",
    })


def amma_recipes(root: Path) -> None:
    """Died ~3 months ago; a half-finished search feature hides in a stash."""
    repo = root / "amma-recipes"
    init_repo(repo)
    commit(repo, 96, "init: amma recipes — family recipe archive", {
        "README.md": "# Amma Recipes\n\nSaving amma's recipes before they're lost. Search, tag, and print.\n",
        "app.py": "recipes = []\n",
    })
    commit(repo, 92, "add 12 recipes + ingredient tags", {
        "data/recipes.py": "RECIPES = ['sambar', 'rasam', 'poriyal']\n# TODO: add measurements converter (cups -> grams)\n",
    })
    commit(repo, 89, "print-friendly recipe cards", {
        "templates/card.html": "<article class='card'></article>\n",
    })
    # Half-finished Tamil search, stashed and forgotten:
    (repo / "search.py").write_text(
        "def search_tamil(query):\n    # transliteration map goes here\n    ...\n",
        encoding="utf-8",
    )
    run(repo, "add", "search.py")
    run(repo, "stash", "push", "-m", "tamil search wip")


def main() -> None:
    default_target = Path(__file__).resolve().parent.parent / "sample_graveyard"
    target = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else default_target
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    fitquest(target)
    pumpfolio(target)
    amma_recipes(target)

    print("🪦 Graveyard conjured at:", target)
    for child in sorted(target.iterdir()):
        print("   ⚰️ ", child.name)
    print("\nNow run the app (python run.py) and scan this folder in the UI.")


if __name__ == "__main__":
    main()
