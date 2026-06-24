# Development Journal

## Software Stack

- **Backend**: Flask (Neusician), Python 3, SQLite (worker scheduling via SQL triggers)
- **Synthesis**: Sompyler (`sompyle` CLI), managed by shell script per worker
- **Score Editor**: Vue3 SPA (no build step; CDN ESM via import map), pure `h()` render functions
- **Auth**: Flask-HTTPAuth, HTTP Basic Auth; self-registration via password prefix
- **Deployment**: gunicorn / flask dev server; Blueprint mounted at `/sompyle/score-editor`

## Key Decisions

### No build step for Vue3 frontend
Vue3 is loaded from CDN via an import map (`<script type="importmap">`). All JS is native ESM. `h()` render functions are used instead of SFC templates to avoid `unsafe-eval` CSP issues. This means no Vite/Webpack, no node_modules, no compilation step — files are served directly as static assets by Flask's Blueprint.

### Template-based YAML export (no YAML library)
The exporter serializes instrument blocks using string templates with `#N` placeholders rather than a YAML library. This keeps the dependency surface minimal and gives precise control over indentation and flow vs. block style choices that match the Sompyler YAML format exactly. v1 scope: only instrument blocks are re-serialized; the rest of the score is patched from the raw text fetched via `GET /sompyle/score.spls`.

### Two-pass AST parser
The AST log parser does a first pass to build a generic depth-stack tree, then a second pass to promote known slot types to typed model objects. Unknown slots become generic nodes (never discarded). This means new slot types in future Sompyler versions degrade gracefully to raw display rather than breaking the parser.

### Worker scheduling in SQLite
All worker assignment logic lives in SQL views and triggers (`neusician/schema.sql`). Python only calls `procman.get_status()` and reads results. Do not move scheduling logic to Python — the SQL approach handles concurrency correctly via SQLite's transaction semantics.

### Fork workflow
This repo is a fork of [upstream neusician](https://gitlab.com/flowdy/neusician) (remote: `upstream`). Development happens here; the upstream author cherry-picks commits back. Fetch `upstream` periodically and merge/rebase to stay in sync. `PLAN/` submodules are read-only references — never commit changes to them.

### Blueprint registration (server.py:66–72) — resolved
Two bugs were fixed: `"score-editors"` → `"score_editors"` (hyphens not valid as Python identifiers in importable paths), and `.blueprint` moved outside `import_module(...)` so it is called on the module object, not the string. `SCORE_EDITOR_BLUEPRINT` config value must match `[A-Za-z]\w+`.

### Bar export via YAML document stream
Sompyler score files are YAML document streams: bars are separated by `\n---\n`, each a standalone YAML document with `_id:` and `_meta:` keys followed by voice note lines. The exporter splits on `\n---\n`, patches only dirty bar documents by regenerating the `_meta:` block in-place, and preserves voice note content verbatim. This avoids any need to re-serialize the note notation format.

### Undo chain for linked instrument discard
Mutations to shape coords happen in-place before `onChange` fires. To support discarding the first edit to a linked instrument, each mutating component (`ShapeEditor`, `EnvelopeEditor`) passes `{ undo }` to `onChange`. The undo callback is stored in `pendingEdit` and called if the user chooses discard in the modal.

### AM modulation reuses FM serializer
AM and FM modulation share identical syntax per RFC §3.2.1.1.6-7. A single `serializeModulation()` function handles both. The parser captures both under `fmModulations` / `amModulations` arrays at both the instrument level and inside `basic_properties`.

## Core Features

- HTTP Basic Auth with self-registration (password prefix = `NEUSICIAN_NEW_USER_REG_PREFIX`)
- Sompyler synthesis job queue via SQLite triggers; one active job per worker
- Score submission via POST to `/sompyle`, polling via `/sompyle/status.json`
- Vue3 score editor Blueprint: import AST log → edit instrument envelopes → export patched YAML → synthesize
