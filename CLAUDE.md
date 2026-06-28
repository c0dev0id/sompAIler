# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Critical Rules
- **Always** read the RFC (`sompyler/doc/rfc.md`) before making changes. RFC conformance is of utmost importance.
- **Always** treat the `sompyler/` and `neusician/` directories as read-only.
- **Never** check in any CLAUDE-related file (`.claude/`, `CLAUDE.md`, `CHANGELOG.md`, `.github/development-journal.md`) to a submodule repository. They live only in this root repository.
- **Always** perform fixture tests (see *Testing* below) after any implementation change.
- **Always** verify that changes don't break RFC conformance.
- **Never** add backward compatibility when changing code A to B. Code A must be removed; code B must be added. No dual support, no fallbacks, no OR conditions across old and new.
- **Never** act on user self-criticism. When the user owns a past mistake ("it's my fault", "I should have…"), treat it as a closing-the-loop signal — wait for a clear command. Do not preemptively fix, revert, or push an unnegotiated backward-compat shim, especially to `origin/master`.
- **Always** pull the latest commits from the main repository and all submodules before starting work on any user prompt or plan.
- When questions arise during development, you **must** stop and ask the user how to proceed. **Override global rule**: the rule to minimize interruptions and proceed automatically does **not** apply in this project.

## Repository Layout

This is a thin wrapper repository whose only active development area is `AddOns/score_editors/vue3js-app/` — a Flask Blueprint hosting a Vue 3 score-editor SPA.

| Path | Kind | Status |
|---|---|---|
| `sompyler/` | submodule | read-only; RFC at `sompyler/doc/rfc.md` |
| `neusician/` | submodule | read-only; Flask app source at `neusician/neusician/` |
| `AddOns/score_editors/vue3js-app/` | submodule | **the work area** for this fork |
| `sample_analysis/` | local | standalone Python utility with its own `requirements.txt` |
| `wsgi.py`, `clean-orphan-oggs.sh` | local | thin glue mirroring upstream neusician |
| `CHANGELOG.md`, `.github/development-journal.md` | local | maintained per global rules; never committed inside a submodule |

`neusician/AGENTS.md` and the sompyler upstream forbid AI-generated changes to those submodules. The score-editors area is the only sanctioned target for AI work. Bumping a submodule SHA after upstream releases changes is fine.

## Running the App

Copy `neusician/neusician/templates/base.tmpl.stub` to `…/base.tmpl` and customize it before first run.

Create `instance/config.py` (excluded from git) with at minimum:

```python
SECRET_KEY = 'change-me'
DATABASE = '/path/to/neusician.db'
NEUSICIAN_NEW_USER_REG_PREFIX = 'register:'
SOMPYLER = '/path/to/sompyler'
TMPDIR = '/tmp/neusician'
```

Run via the WSGI entry point:
```sh
flask --app wsgi run
# or in production:
gunicorn wsgi:app
```

Worker directories must exist as `$TMPDIR/NN/` (zero-padded two-digit IDs) before the DB is initialized. The output directory is `$TMPDIR/OUT/`.

Optional config keys: `SOMPYLER_LIMITS` (colon-separated ulimit string where index 2 is `total_samples_max`), `WORKERS_PER_USER`, `MIDIEXP`, `EXT_PUBLISH_CMD`, `SCORE_EDITOR_BLUEPRINT`.

### `SCORE_EDITOR_BLUEPRINT` gotcha
`neusician/neusician/server.py` does `importlib.import_module("score_editors." + <config value>)`. The value must therefore be a valid Python identifier (`[A-Za-z]\w+`). The submodule is checked out at `AddOns/score_editors/vue3js-app/` — the hyphen in the directory name is not importable as-is, so deployment requires a `score_editors/` directory on `sys.path` whose entry uses an underscore name. The Blueprint itself registers as `vue3_neusik`.

## Testing

There is no central test runner. The repository's primary regression check is the fixture-based parser/exporter test for the Vue3 score editor:

```sh
cd AddOns/score_editors/vue3js-app
node test-parser.mjs
```

It parses `fixtures/ast.log` (Beethoven *Pathétique*, 1st mov.) and round-trips shape data through `static/ast-parser.js` and `static/exporter.js`. Run it after any change to those files or to `store.js`. Per the Critical Rules, a fixture test is mandatory after implementation work.

Sompyler's own tests live under `sompyler/tests/` and are owned by the read-only submodule.

## Architecture — Neusician (Read-Only Reference)

The Flask application lives in the `neusician/` submodule (source at `neusician/neusician/`). Knowing it matters because the score-editor Blueprint integrates with its endpoints.

### Module map (paths relative to `neusician/neusician/`)
| Module | Responsibility |
|---|---|
| `server.py` | All Flask routes; thin layer delegating to domain modules |
| `sompyler_procman.py` | Worker lifecycle: DB access, subprocess management, status parsing |
| `arbitextonotes.py`, `arbitrarygrooves.py`, `harmonisation.py` | Pseudo-random melody generation from a seed phrase |
| `markov_util.py` | Markov chain parsing and validation |
| `sompyler_yaml.py` | Converts plain tone notation to Sompyler YAML |
| `split_rhythmel.py` | Trinary number → Sompyler note-chain conversion |
| `smart_indent.py` | YAML indentation helpers (`expand` / `unindent_from`) |
| `schema.sql`, `routines.sql` | SQLite schema (views + triggers); periodic maintenance SQL |
| `single-sompyler-procman.sh` | Shell wrapper running `sompyle` per worker |

### Worker scheduling lives in SQLite, not Python
The entire worker-assignment algorithm is SQL: views (`stake`, `waiting_users`, `available_workers`) and triggers (`assign_worker`, `update_lpm_request_worker`, `resets_on_successful_worker_assignment`) in `schema.sql`. Python only calls `procman.get_status()` and reads results. Do not propose moving scheduling logic into Python — concurrency safety relies on SQLite's transaction semantics.

`sompyler_procman.py` holds a module-level SQLite connection (`con`), opened per request in `init_db()` and closed in the `teardown_request` hook.

### Authentication
HTTP Basic Auth via `flask-httpauth`. Self-registration: a password beginning with `NEUSICIAN_NEW_USER_REG_PREFIX` creates the account on first use. There is no separate sign-up form.

### Synthesis flow
1. Client POSTs YAML score to `/sompyle` (or `/sompyle/reserved-a-worker-for-tests` for tests)
2. `procman.initialize_sompyler()` writes the score to the user's worker directory
3. `procman.get_status()` invokes `single-sompyler-procman.sh` as a subprocess
4. The shell script runs `sompyle` and writes progress to `$WORKERDIR/status`
5. `/sompyle/status.json` is polled every 2 s (or at centile-of-ETA intervals when progress is 0–20%)
6. On completion, `/sompyle/result.mp3` serves the rendered audio

### Templates
Jinja2 `.tmpl` files; all extend `base.tmpl` (not committed; copy from `base.tmpl.stub`). Template filter: `fsup` formats fractional numbers as HTML superscript.

## Score-editor Blueprint Contract

- Each editor is a self-contained Flask Blueprint.
- Root file is `__init__.py` containing a `flask.Blueprint()` instance — no Neusician or Sompyler core imports.
- Mounted at `/sompyle/score-editor` via `SCORE_EDITOR_BLUEPRINT`.
- The root endpoint accepts `?import=1` (GET) and fetches `/sompyle/astlog` to validate that the imported Neusik score is renderable.
- To export Neusik code, the Blueprint's static JS opens `/sompyle` (or `/sompyle/reserved-a-worker-for-tests`) and injects the score into the textarea. Same-origin — no CORS concerns.
- Status polling: `/sompyle/status.json` every 2 s, or centile-of-ETA when progress is 0–20%.

### Vue 3 SPA constraints (`AddOns/score_editors/vue3js-app/`)
Decisions and rationale are recorded in `.github/development-journal.md`. The non-obvious ones to respect:

- **No build step.** Vue 3 is loaded from CDN via `<script type="importmap">`; all JS is native ESM. Use `h()` render functions, never SFC templates (avoids `unsafe-eval` CSP issues). No `node_modules`, no Vite/Webpack.
- **No YAML library.** Instrument export is template-based with `#N` placeholders; the rest of the score is patched in-place from the raw text fetched via `GET /sompyle/score.spls`. Bar `_meta:` blocks are patched by splitting the YAML document stream on `\n---\n`.
- **Two-pass AST parser.** First pass builds a generic depth-stack tree; second pass promotes known slot types to typed model objects. Unknown slots fall back to generic nodes so future Sompyler slot additions degrade gracefully rather than breaking.
- **AM and FM modulation share one serializer.** Per RFC §3.2.1.1.6–7 they have identical syntax; `serializeModulation()` handles both.

## After a Task

Per global rules: update `CHANGELOG.md` (human-readable description; skip trivial entries) and `.github/development-journal.md` (decisions + rationale only — not commit summaries). Both live at the repo root and are never committed inside a submodule.
