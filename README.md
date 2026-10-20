# ⚰️ Deadline Necromancer

**Every dead project deserves a second life.**

Every developer has a `~/projects` folder that is really a graveyard: dozens of repos
started with genuine excitement and abandoned mid-feature. Starting over feels easier
than going back — so the graveyard keeps growing, and all that half-finished work rots.

**Deadline Necromancer** performs an autopsy on every abandoned repo in a folder —
when it died, what it left unfinished, what its last words were — and then a **local
open-weight model (Gemma, via Ollama)** writes a *resurrection plan*: a lazy-first,
smallest-possible-steps path back to life, with an honest estimate of how many hours
reviving saves versus starting from scratch.

The laziest way to finish a project is to not start a new one.

![status](https://img.shields.io/badge/runs-100%25%20locally-brightgreen)
![model](https://img.shields.io/badge/model-Gemma%20via%20Ollama-blueviolet)
![license](https://img.shields.io/badge/license-MIT-green)

## Why local, why open?

Your abandoned code is your *most* private code — half-baked ideas, experiments you'd
never publish, the occasional secret committed at 2 AM. Sending that to a cloud API for
a summary is a bad trade. Deadline Necromancer runs **entirely on your machine**: the
autopsy is plain git archaeology, and the reasoning is done by Gemma running locally
through Ollama. No code ever leaves your laptop — and because the model is open-weight,
the tool works offline, costs nothing per call, and can't be taken away by a pricing
change. Open innovation isn't a footnote here; it's the only way this product is
acceptable to use.

## Features

- 🪦 **Graveyard scan** — finds every git repo under a folder and lays out tombstone
  cards: death date, days dead, last commit ("last words"), language, commit count.
- 🔬 **Autopsy engine** — pure git archaeology: TODO/FIXME/HACK markers, uncommitted
  changes left hanging, forgotten stashes, branch count, README claims vs. reality.
- 🧠 **Gemma resurrection plans** — cause of death, unfinished business, and a 3–6 step
  plan whose first step is *embarrassingly small* (momentum beats ambition).
- 💸 **The Lazy Payoff** — every plan shows revival hours vs. restart-from-scratch
  hours, and exactly how much time laziness saves you.
- 🛟 **Never crashes** — if Ollama is down or the model returns nonsense, a rule-based
  fallback planner produces an honest plan (clearly labelled "Demo mode"). The demo
  cannot die.
- 🔒 **Private by architecture** — no cloud calls, no telemetry, no accounts.

## Quickstart

```bash
# 1. Install Ollama and pull the model (one time)
ollama pull gemma3:12b        # smaller machines: gemma3:4b works too

# 2. Install and run
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py                 # → http://127.0.0.1:8000
```

No Ollama? The app still runs in demo mode — you'll get rule-based plans instead
of Gemma's.

### Try the demo graveyard

```bash
python scripts/seed_graveyard.py   # creates ./sample_graveyard with 3 dead repos
```

Then scan the `sample_graveyard` folder in the UI: a fitness API that died mid-auth
with secrets in its TODOs, a crypto dashboard that chased websockets into the grave,
and a family recipe app with a half-finished feature hiding in a stash.

## Configuration

Environment variables (see `.env.example`):

| Variable          | Default                  | Meaning                        |
| ----------------- | ------------------------ | ------------------------------ |
| `OLLAMA_HOST`     | `http://localhost:11434` | Ollama endpoint                |
| `NECRO_MODEL`     | `gemma3:12b`             | Open-weight model for plans    |
| `DEFAULT_SCAN_PATH` | `~/projects`           | Folder scanned on first load   |
| `PORT`            | `8000`                   | Server port                    |

## Project structure

```
deadline-necromancer/
├── run.py                    # entry point
├── app/
│   ├── main.py               # FastAPI app (API + static frontend)
│   ├── config.py             # env-driven settings
│   ├── api/routes.py         # /api/health, /api/scan, /api/resurrect
│   ├── core/
│   │   ├── scanner.py        # finds git repos under a folder
│   │   ├── autopsy.py        # git archaeology → ProjectFacts
│   │   ├── necromancer.py    # Gemma via Ollama + validation + cache
│   │   └── fallback.py       # rule-based planner (demo mode)
│   ├── models/schemas.py     # pydantic contracts
│   └── static/               # vanilla HTML/CSS/JS graveyard UI
├── scripts/seed_graveyard.py # demo data: 3 believable corpses
└── tests/                    # 24 tests: scanner, autopsy, fallback, LLM parsing, API
```

## Tests

```bash
python -m pytest -q
```

The LLM layer is tested with a mocked Ollama: valid JSON is accepted, garbage output
degrades to the fallback planner, and absurd numbers from the model are clamped to
sane ranges. Model output is treated as untrusted input, because it is.

## How it works

1. **Scan** — the scanner walks your folder (skipping `node_modules`, venvs and hidden
   dirs) and collects every git repo.
2. **Autopsy** — for each repo, git tells the story: first/last commits, TODO markers
   in the committed tree, uncommitted changes, stashes, branches, README.
3. **Necromancy** — the autopsy report goes to Gemma with a strict JSON contract. The
   response is parsed defensively, numbers are clamped, and the plan is cached.
4. **Payoff** — revival vs. restart hours are rendered as the Lazy Payoff bars in the
   UI, so the value of *not* starting over is always visible.

## Built for

Hacktoberfest Open-Source AI Challenge — Week 3, "Slow and Steady" 🦥
Because steady resurrection beats frantic restarting.

## License

MIT © Revaldo S
