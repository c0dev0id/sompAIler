# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- vue3js-app: `NOT_CHANGED_SINCE` now correctly written on every export — float epoch converted to ISO date for unmodified linked instruments, current timestamp for re-serialized instruments
- vue3js-app: synthesis errors from `status.json` now displayed in the CP pane after the synthesis run completes
- vue3js-app: deleting an instrument now also removes its corresponding `stage:` voice entry from the exported score

### Changed

- vue3js-app: extracted shared utilities `coerce` and `stressorToString` into `static/util.js`; extracted breadcrumb projection `shortView` into `static/node-views.js`
- vue3js-app: renamed `rawChildren` → `unknownSlots` on all model objects; renamed `Offset.motifs` → `Offset.motifRefs` to distinguish invocation references from full Motif objects
- vue3js-app: underscore-prefixed all non-exported functions across `ast-parser.js`, `exporter.js`, and component helpers
- vue3js-app: removed WHAT-comments throughout; kept RFC section references and non-obvious WHY constraints
- vue3js-app: converted imperative loops in `exporter.js` and `subobject-kinds.js` to `.map()`, `.flatMap()`, `.filter()`, `.forEach()`; deduplicated `newBars` filter in `patchScore`

### Added

- `score_editors/vue3_neusik/` — Vue3 SPA score editor deployed as a Flask Blueprint
  - AST log parser (`ast-parser.js`): two-pass parser building a typed score model from Sompyler's numbered AST log format; handles all known slot types, skips DEBUG lines, generic fallback for unknown slots
  - Vue3 reactive store (`store.js`): score model, focus path, credentials, dirty flag
  - API fetch wrappers (`api.js`): `/sompyle/astlog`, `/sompyle/score.spls`, `/sompyle/status.json`
  - Template-based YAML exporter (`exporter.js`): instrument-block serializer; patches only dirty instrument sections into the raw score text; bar `_meta:` block patching via YAML document stream splitting
  - 3-pane layout with tab bar (Position / Object / Sub-objects)
  - Import dialog with Basic Auth credential prompt
  - ShapeEditor with cascade x-shift and SVG preview
  - EnvelopeEditor with A/S/R co-dependence rules (Attack ending at y=0 disables S/R; absent S disables R)
  - ETA-aware StatusPoller using `currently_rendered_notes` / `notes_in_total` fields from `status.json`
  - `?import=1` query param opens import dialog automatically on load
  - Full bar navigation: voices and offsets are browsable and their sub-nodes (stem notes, clusters) are displayed in the FO pane
  - Editable bar properties: BPM, stress pattern, upper/lower stress bounds, tempo shape
  - Linked instrument modal with undo on discard — first edit to a linked instrument prompts embed-or-discard; discarding restores the original value
  - Any label click in CP or SubObjects panes switches the active tab to the FO pane
  - AM modulation parsed and exported symmetrically with FM modulation
  - Voice motif definitions and offset stem notes fully parsed with clause/note/pause/stack bodies
  - Static motifs (all absolute-pitched stem notes) navigable in Sub-objects pane; dynamic motifs shown inline in Voice FO summary
  - Stem note FO pane with editable pitch, length, weight, adj_stress, and chain text fields
  - Motif invocations (`line.motif`) at tick positions stored in `offset.motifs[]` and shown in Tick FO pane
  - `stem_note.writeToName` captured for static motif storage name
  - Parser updated for sompyler slot renames: `line.stem_note`, `seq.note/pause/stack`, `stem_note.chain` as real hierarchy node
  - Multi-pane Sub-objects: handle bar now lists one pane per kind of sub-object the focused node has (e.g. score node shows TU, ST, IN, AR, BA — tuning, stage, instruments, articles, bars). Handles are 2-letter labels, intended as alt-text for icons in a later release.
  - Parser support for sompyler 10cad1f preamble: `stage.cone` and `stage.voice` (replacing `stage_voice`), `articles.<subtype>` (replacing `article`; first subtype is `defaults`), `tuning.frequency_factors` slot with `label` (e.g. `just5lim`)
  - Articles are keyed by label across subtypes: `articles.defaults 'f'` and (future) `articles.overwrites 'f'` merge into one entry. Properties carry their scope individually (`defaults` | `overwrites`).
  - Article FO pane lists properties with a `(O-) default` / `(-O) overwrite` toggle per row — click to flip the scope.
  - Article entries in the CP path list show the article label (was just "article"), with a property count in the meta column.
  - Article properties in the FO pane are now fully editable: key, value (type-coerced on input), scope, and per-row remove button; a "+ add property" button appends new entries.
  - Article changes are now exported to the score: dirty articles replace the `articles:` block in the score header; clean articles are passed through verbatim.
  - Scope toggle for article properties switched to Bootstrap `form-check form-switch`; hand-rolled CSS pill removed.
  - Export log shown in CP pane after each export: one line per changed entity (path) and one summary line for bar documents passed through unchanged.
  - BA (bar) sub-objects pane now groups bars by the `P?L?` section key extracted from their IDs, displaying each group as a row of compact inline-block chips; groups are separated by a line break. Clicking a chip focuses the bar as before.
  - Custom auth dialog removed; credentials are now handled entirely by the browser's native Basic Auth prompt on 401 responses. The `→ Import` button triggers a direct fetch; `?import=1` auto-imports on page load.
  - Delete buttons (red ×) on all logically removable entities: instruments, articles, variations, label specs (via Sub-objects pane ObjectShort rows); bars (via chip × button). Article deletion sets `articlesModified` so the articles block is re-serialized even when no remaining article is dirty. Instrument deletion skips the block in export. Bar deletion filters the YAML document. Variation/label-spec deletion splices from the parent and marks the instrument dirty.
  - Bar add buttons: each group in the BA pane has a "+ add" button that presets the new bar ID by incrementing the trailing digit run of the last bar in that group; a global "+ add bar" at the end uses the last bar overall. New bar ID is editable in the FO pane. New bars are appended as YAML documents on export.
  - `patchScore` accepts a `flags` object (6th argument) with `articlesModified: true` to force article block re-serialization independent of per-article dirty state.

### Changed (architecture cleanup — phases 4–6)

- vue3js-app: article model reworked for sompyler's new two-level structure: `stage.article 'label'` and `voice.article 'label'` with `article.defaults`, `article.overwrites`, and `article.definite` children; `voice.article` now stores full article objects instead of label strings
- vue3js-app: article exporter emits `-important:` YAML list for overwrite-scope properties; articles block always re-serialized on export (no per-article dirty tracking)
- vue3js-app: `stem_note` model gains `weight` and `articulatory` fields; `article.definite` properties from child slots are flattened directly onto the stem note as siblings of `pitch` and `chain`
- vue3js-app: edit-state flags (`isDirty`, `deleted`, `isNew`) removed from all domain model objects; exporter now traverses the current object tree on demand — absent nodes are naturally skipped; `_modified` (linked instruments) and `_isNew` (new bars) replace the removed flags with minimal, targeted lifecycle markers
- vue3js-app: `_spliceNode` helper extracted from 5× duplicated indexOf+splice+markDirty pattern in PaneSubObjects; bar and article deletion now splice from the array immediately rather than setting flags
- vue3js-app: `store.resetEditState()` added; used on import to reset dirty flag, focus path, and export log in one call; `patchScore` `flags` argument dropped
