# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Critical Rules
- **Always** read the RFC (sompyler/doc/rfc.md) before making changes. RFC conformance is of utmost importance.
- **Always** treat the somplyler and neusician directories as read-only.
- **Never** check in any CLAUDE file (.claude/, CLAUDE.md, CHANGELOG.md, .github/development-journal.md) to submodule repositories. They can be checked in to the root repository.
- **Always** perform fixture tests to find errors after in the implementation.
- **Always** verify that changes don't break RFC conformance
- **Never** add backward compatibility when changing code A to B. Code A must be removed; code B must be added. No dual support, no fallbacks, no OR conditions across old and new.
- **Always** pull the latest commits from the main repository and all submodules before starting work on any user prompt or plan.
- When questions arise during development, you **must** stop and ask the user how to proceed. **Override global rule**: the rule to minimize interruptions and proceed automatically does **not** apply in this project.

## General

Data in the `PLAN/` directory is for reference only and must not be changed.
- `PLAN/vue3js-app-proposal-for-sdk-claude` — planned frontend implementation (git submodule)
- `PLAN/sompyler` — the Sompyler synthesizer repository (git submodule)

The repository root contains the **Neusician** Flask application. Information here supersedes code location references inside the PLAN documents. Treat the submodule contents as already up-to-date.

## Running the App

Copy `neusician/templates/base.tmpl.stub` to `neusician/templates/base.tmpl` and customize it before first run.

Create `instance/config.py` (excluded from git) with at minimum:

```python
SECRET_KEY = 'change-me'
DATABASE = '/path/to/neusician.db'
NEUSICIAN_NEW_USER_REG_PREFIX = 'register:'
SOMPYLER = '/path/to/sompyler'
TMPDIR = '/tmp/neusician'
```

Run via WSGI entry point:
```sh
flask --app wsgi run
# or in production:
gunicorn wsgi:app
```

Worker directories must exist as `$TMPDIR/NN/` (zero-padded two-digit IDs) before the DB is initialized. The output directory is `$TMPDIR/OUT/`.

Optional config keys: `SOMPYLER_LIMITS` (colon-separated ulimit string where index 2 is `total_samples_max`), `WORKERS_PER_USER`, `MIDIEXP` (path to MIDI export tool), `EXT_PUBLISH_CMD`, `SCORE_EDITOR_BLUEPRINT` (dotted module name under `score-editors/`).

## Architecture

### Module Overview

| Module | Responsibility |
|---|---|
| `wsgi.py` | Entry point — calls `create_app()` |
| `neusician/server.py` | All Flask routes; thin layer, delegates to domain modules |
| `neusician/sompyler_procman.py` | Worker lifecycle: DB access, subprocess management, status parsing |
| `neusician/arbitextonotes.py` | Pseudo-random melody generation from seed phrase |
| `neusician/markov_util.py` | Markov chain parsing and validation |
| `neusician/sompyler_yaml.py` | Converts plain tone notation to Sompyler YAML |
| `neusician/split_rhythmel.py` | Trinary number → Sompyler note-chain conversion |
| `neusician/smart_indent.py` | YAML indentation helpers (`expand` / `unindent_from`) |
| `neusician/schema.sql` | SQLite schema: `user`, `worker` tables, views, triggers |
| `neusician/routines.sql` | Maintenance SQL (run periodically, not on startup) |
| `neusician/single-sompyler-procman.sh` | Shell script wrapping a Sompyler synthesis run per worker |

### Worker Scheduling

The entire worker-assignment algorithm lives in SQLite (`schema.sql`) — views (`stake`, `waiting_users`, `available_workers`) and triggers (`assign_worker`, `update_lpm_request_worker`, `resets_on_successful_worker_assignment`). Python only calls `procman.get_status()` and reads the result. Do not move scheduling logic to Python.

`sompyler_procman.py` holds a module-level SQLite connection (`con`) that is opened per request in `init_db()` and closed in the `teardown_request` hook.

### Authentication

HTTP Basic Auth via `flask-httpauth`. Self-registration: if a password starts with `NEUSICIAN_NEW_USER_REG_PREFIX`, a new account is created on first use. There is no separate sign-up form.

### Sompyler Synthesis Flow

1. User POSTs YAML score to `/sompyle` or `/sompyle/reserved-a-worker-for-tests`
2. `procman.initialize_sompyler()` writes the score to the user's worker directory
3. `procman.get_status()` invokes `single-sompyler-procman.sh` as a subprocess
4. The shell script runs `sompyle` (the Sompyler CLI) and writes progress to `$WORKERDIR/status`
5. `/sompyle/status.json` polls this status and is called by the client every 2 s (or at centile intervals of the ETA when progress is 0–20%)
6. On completion, `/sompyle/result.mp3` serves the rendered audio

### Templates

Jinja2 templates use `.tmpl` extension. All extend `base.tmpl` (not committed; copy from `base.tmpl.stub`). Template filters: `fsup` (format fractional numbers as HTML superscript).

## Rules for `score-editors/`

- Each score editor is a self-contained Flask Blueprint.
- The root file must be `__init__.py` containing a `flask.Blueprint()` instance — no Neusician or Sompyler core code inside.
- Blueprint is mounted at `/sompyle/score-editor` via the `SCORE_EDITOR_BLUEPRINT` config key.
- The Blueprint's root endpoint accepts `?import=1` (GET), which fetches `/sompyle/astlog` to validate that the imported Neusik score is renderable.
- To export generated Neusik code, the Blueprint's static JS opens `/sompyle` or `/sompyle/reserved-a-worker-for-tests` and inserts the score into the textarea. No CORS issues arise when running on the same domain as Neusician.
- Status polling: call `/sompyle/status.json` every 2 s, or at centile-of-ETA intervals when progress is 0–20%.
