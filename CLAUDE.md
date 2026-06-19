# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

- The repository **root contains the Neusician code** (the `neusician/` Flask package, `wsgi.py`, helper scripts).
- `PLAN/` is **reference only — never modify it**. It holds two git submodules:
  - `PLAN/sompyler` — the upstream Sompyler synthesis engine.
  - `PLAN/vue3js-app-proposal-for-sdk-claude` — notes about a planned implementation.
- Information in this file **supersedes** code-location references inside the `PLAN/vue3js-app-proposal-for-sdk-claude` documents. Assume any `git pull` instructions there are already done; the code is current.

## What Neusician is

A small Flask web app with two largely independent features (either can be ignored), both aimed at teaching the Sompyler/YAML music language interactively:

1. **Pseudo-random melody generator** — deterministically turns a seed phrase + a "probabilistic fingerprint" (tone scale + Markov chains) into a plain-text melody.
2. **Online Sompyler score & instrument editor** — converts melodies into Sompyler YAML note-chain syntax and (for authenticated users) renders audio by shelling out to a separate Sompyler installation.

Neusician itself only *generates and edits* Sompyler code and *orchestrates* rendering; it does **not** contain the Sompyler/Neusician synthesis core. Rendering is delegated to an external Sompyler install.

## Running the app

There is no `requirements.txt` / `setup.py` and no test suite. Dependencies are `flask`, `flask_httpauth`, `werkzeug`, and `pyyaml` (`yaml`).

- Entry point: `wsgi.py` → `neusician.server.create_app()` (Flask app-factory pattern, `instance_relative_config=True`).
- Dev run: `FLASK_APP=wsgi flask run`, or any WSGI server pointed at `wsgi:app`.
- Configuration lives in `instance/config.py` (git-ignored, **must be created**). Keys read by the code:
  - Required: `SOMPYLER` (path to Sompyler install), `MIDIEXP` (path to MIDI-export install), `TMPDIR`, `DATABASE`, `NEUSICIAN_NEW_USER_REG_PREFIX`.
  - Optional: `SOMPYLER_LIMITS` (colon-separated; the `total_samples_max` field is filled in per-user at runtime), `WORKERS_PER_USER`, `EXT_PUBLISH_CMD`, `SCORE_EDITOR_BLUEPRINT`.
- Templates: copy `neusician/templates/base.tmpl.stub` → `base.tmpl` and customize before serving.
- `clean-orphan-oggs.sh <OUT-dir>` is a cron helper that prunes rendered audio for users no longer in the DB.

Note: `venv/` here is **not** a Python virtualenv — it is a small set of wrapper scripts (`call_sompyler_prog`, `pre2midi`, `analyze-tone`, `render-shapes`) that `cd` into `$SOMPYLER` / `$MIDIEXP` and activate *their* virtualenvs to invoke the real Sompyler tools.

## Architecture

### Flask layer — `neusician/server.py` (~710 lines)
The single app factory `create_app()` defines every route. Notable groups:
- Public: `/`, `/randomelody` (melody generator), `/chainfromnumbers`, `/chaintool`, `/info`, `/sompyle` (public YAML acceptor).
- Auth-gated (HTTP Basic via `flask_httpauth`): everything under `/sompyle/...` — `status`, `status.json`, `analyze`, `score.spls`, `result.mp3`, `midi`, `astlog`, `render-shapes`, tone analysis, `publish`, plus `/change-password`, `/logout-user`.
- If `SCORE_EDITOR_BLUEPRINT` is set, a blueprint from `score-editors/` is imported and mounted at `/sompyle/score-editor` (see *score-editors rules* below).

### Worker / quota system — `neusician/sompyler_procman.py` + `schema.sql` + `routines.sql`
Rendering is resource-heavy, so access is mediated by a SQLite-backed **worker reservation** model. The interesting logic lives in SQL (`schema.sql`): `user` and `worker` tables plus the `stake`, `waiting_users`, and `available_workers` views and several triggers implement a fairness/queueing scheme (`expires_not_before`, `needs_worker_since`, `tried_times`, `given_resources`/quota). Read the heavily-commented `schema.sql` to understand reservation, expiry, and quota bonuses before touching this area. `sompyler_procman.py` wraps the DB and launches renders.

### Render orchestration — `neusician/single-sompyler-procman.sh`
`sompyler_procman.get_status(...)` builds an environment (`SOMPYLER_LIMITS`, `W0MODE`, `WORKERS_PER_USER`, `ONLY_MEASURES`, `SKIP_KNOWN_LINES`, `SOMPYLER_REFRESH_EMBEDDED_CACHED_INSTR`, ...) and runs `single-sompyler-procman.sh <worker-dir> <user>`. That script (re)starts the Sompyler process per worker directory under `TMPDIR`, tails `OUT.log` with `awk` to parse progress/ETA into a `status` file, and reports back. `W0MODE` selects the mode: normal render, `check-only`, `reverb[:room]`, or `midi`.

### Melody generation & code transforms (pure-Python, no external deps)
- `arbitextonotes.py` — seed phrase → big integer (base64url alphabet) → tone sequence; the deterministic core of the generator.
- `arbitrarygrooves.py` — derives rhythm/groove from the same big-number stream.
- `markov_util.py` — Markov-chain tone selection from the fingerprint spec (`MarkovSpecError`).
- `ranged_permutation_picker.py` — distributes integers summing to a total (used for rhythm shares).
- `harmonisation.py`, `restricted_88keys.py` — scale/harmony helpers and piano-key range mapping.
- `sompyler_yaml.py` — `make_yaml_code(...)` renders tones/beats into Sompyler YAML; `code_analyzer` inspects submitted code.
- `smart_indent.py` — `expand` / `unindent_from` convert between Neusician's terse numeric-indent notation and real YAML indentation.
- `split_rhythmel.py` — parses trinary rhythm patterns (e.g. `1(2:111)21`).
- `input_error.py` — `ScoreInputError` + `LineTracer` for mapping preprocessed lines back to user input.

## Rules for `score-editors/` blueprints
`score-editors/` is git-ignored; it holds **only** blueprint plugin code, never the Neusician or Sompyler core. A blueprint:
- Root file is `__init__.py` exposing a `flask.Blueprint()` instance, imported via the `SCORE_EDITOR_BLUEPRINT` config key.
- Accepts `?import=1` at its root endpoint; uses `GET sompyle/astlog` to verify an imported Neusik score is renderable by the real Sompyler core.
- For export, the static client opens `/sompyle` (or `/sompyle/reserved-a-worker-for-tests`) and injects generated Neusik code into the text-area via JS. Running on the same domain as the Neusician instance avoids CORS issues.
- May poll `sompyle/status.json` to track rendering (auto-click "update status" every ~2s, or at centiles of ETA during 0–20% progress). Upstream will not add automatic polling.

## Contribution conventions (from CONTRIBUTING.md)
Upstream is **hostile to obvious LLM output**: merge/pull requests and issues that read as machine-generated may be closed without comment. Keep prose in individual, understandable English with a human final touch.
