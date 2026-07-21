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

### Blueprint registration (server.py:66–72) — resolved
Two bugs were fixed: `"score-editors"` → `"score_editors"` (hyphens not valid as Python identifiers in importable paths), and `.blueprint` moved outside `import_module(...)` so it is called on the module object, not the string. `SCORE_EDITOR_BLUEPRINT` config value must match `[A-Za-z]\w+`.

### Bar export via YAML document stream
Sompyler score files are YAML document streams: bars are separated by `\n---\n`, each a standalone YAML document with `_id:` and `_meta:` keys followed by voice note lines. The exporter splits on `\n---\n`, patches only dirty bar documents by regenerating the `_meta:` block in-place, and preserves voice note content verbatim. This avoids any need to re-serialize the note notation format.

### Undo chain for linked instrument discard
Mutations to shape coords happen in-place before `onChange` fires. To support discarding the first edit to a linked instrument, each mutating component (`ShapeEditor`, `EnvelopeEditor`) passes `{ undo }` to `onChange`. The undo callback is stored in `pendingEdit` and called if the user chooses discard in the modal.

### AM modulation reuses FM serializer
AM and FM modulation share identical syntax per RFC §3.2.1.1.6-7. A single `serializeModulation()` function handles both. The parser captures both under `fmModulations` / `amModulations` arrays at both the instrument level and inside `basic_properties`.

### Multi-pane Sub-objects driven by SLOT of SLOT.SUBTYPE
The bottom handle bar is dynamic: fixed CP + FO handles, then one per kind of sub-object the focused node has. "Kind" is the SLOT part of the AST's SLOT.SUBTYPE namespace. Sub-objects sharing a SLOT (e.g. `line.stem_note` + `line.motif`, or `articles.defaults` + future `articles.<other>`) collapse into one pane; different SLOTs split. `subobject-kinds.js` produces the ordered group list per node type; `PaneSubObjects` is parameterized by `kind` and renders one group. This generalizes the previous single Sub-objects pane and naturally extends to any entity (variation gets LA + SV when it has both, voice gets MO + OF, etc.).

### Articles keyed by label, scope per property
An article is a (label, property-set) pair. Sompyler emits the same label twice when both `articles.defaults '<label>'` and (future) `articles.overwrites '<label>'` exist, with disjoint property sets. The parser merges these into one model entry keyed by label, with each property carrying its originating scope:

```js
{ name: 'f', properties: [{ name: 'add_stress', value: 3, scope: 'defaults' }, ...] }
```

The Article FO pane renders a `(O-) default` / `(-O) overwrite` toggle per property — the ASCII glyph mimics a physical toggle switch position so the active scope is visible at a glance. Click flips. Mutation marks the score dirty even though the YAML exporter doesn't roundtrip articles yet (v1 scope is instrument blocks only) — the model is correct for when exporter support lands.

### Edit-state outside domain objects (Phase 4 refactor)
Domain objects (instruments, bars, stem notes) carry no lifecycle flags. The exporter traverses the current object tree on demand — absent nodes are naturally skipped.

Two targeted lifecycle markers remain, prefixed with `_` to signal non-domain state:
- `instr._modified = true` — set on a linked instrument when first edited; tells the exporter to re-serialize rather than pass through.
- `bar._isNew = true` — set on a bar object at creation; tells the exporter to append it as a new YAML document.

Deletions splice the node from its parent array immediately (`_spliceNode` helper in PaneSubObjects). The exporter sees only surviving nodes. No `deleted` flag, no Set tracking.

`store.isDirty` (boolean) is the only edit-state signal. `store.markDirty()` sets it. `store.resetEditState()` resets `isDirty`, `focusPath`, and `exportLog` on import. Articles are re-serialized unconditionally on every export — no `articlesModified` flag.

### Delete and add for sub-object entities
Instruments, articles, variations, label specs, and bars are all deletable from the Sub-objects pane. All deletions call `_spliceNode(arr, node, store)` which splices from the parent array and calls `store.markDirty()`.

New bars are created with `{ ..., _isNew: true }` and appended to `model.bars`. Their ID is preset by incrementing the trailing digit run of the last bar in the group or globally. The ID field is editable in the FO pane when `bar._isNew`. On export they are appended as new YAML documents after all existing bar documents.

### Stage voice cleanup reads raw score text
The AST log `stage.voice` slot carries only `direction` and `distance` — no instrument reference. `_patchStageSection` in the exporter therefore reads the raw score header text to determine which instrument each voice references: explicit `instrument:` key in mapping form, or voice name as the implicit instrument name in string form (`voicename: LEFT|RIGHT DIST [instrument]` — instrument is the optional third token). Voices whose resolved instrument name is absent from the current model are removed from the exported stage block. `_space:` (orchestra cone) is always kept.

### NOT_CHANGED_SINCE always written on export
Sompyler's AST log emits this field as a float Unix epoch; the score YAML requires `YYYY-MM-DD HH:MM:SS`. On every export: unmodified linked instruments (`isLinked && !_modified`) get the stored epoch converted to ISO via `_epochToISO`; all re-serialized instruments get the current timestamp via `_nowISO()`. Never omitted.

### Synthesis errors displayed in PaneCP
`StatusPoller` is unmounted when `synthesisStatus.frozen = true`, so errors from `status.json` never reached the poller path after synthesis completed. PaneCP now reads `store.synthesisStatus.errors` directly when frozen and renders them alongside import/export errors.

### Bar ID grouping heuristic in BA pane
Bar IDs are opaque. For display purposes only, the BA sub-objects pane groups bars by stripping the final maximal run of same-class characters (all-digits or all-non-digits) from the ID tail — the remainder is the group key. This is a pure string operation with no knowledge of P/L/M structure. If IDs share a common prefix up to that final run, they appear on the same row as inline chips; otherwise each bar is its own singleton row. Do not add structural pattern matching here; bar IDs remain opaque for all purposes.

### Preamble un-nesting in buildModel
Sompyler's AST trace emits `articles.<subtype>`, `stage.cone`, and `stage.voice` at depth 01 via `with deeper_level("articles"):` / `deeper_level("stage"):` — implicit containers with no depth-00 header line. The generic depth-stack parser therefore nests them under the preceding `00 tuning`. `buildModel()` un-nests them by walking the `tuning` node's children and re-attributing any child whose `parentSlot ≠ 'tuning'` to the score-level top-level list. This is targeted (only tuning gets flattened) because other entities like `instrument` legitimately use implicit containers (`character`, `VOLUMES`, `TIMBRE`, `FM`, `AM`) for their real children.

## Core Features

- HTTP Basic Auth with self-registration (password prefix = `NEUSICIAN_NEW_USER_REG_PREFIX`)
- Sompyler synthesis job queue via SQLite triggers; one active job per worker
- Score submission via POST to `/sompyle`, polling via `/sompyle/status.json`
- Vue3 score editor Blueprint: import AST log → edit instrument envelopes → export patched YAML → synthesize
