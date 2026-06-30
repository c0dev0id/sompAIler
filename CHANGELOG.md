# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
