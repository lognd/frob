---
id: T-5300
title: Wire html/js/jsx/vue grammars into frob.lang
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5140
tier: ticket
sprint: ''
runs_last: false
milestone: 0.535.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/__init__.py
- src/frob/lang/_walk_html.py
- src/frob/lang/_walk_javascript.py
- src/frob/lang/_walk_vue.py
- tests/fixtures/lang/**
- docs/modules/lang.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: null
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: v0.535.0
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Wire html/javascript/jsx/vue grammars into frob.lang (T-5140 substrate).

Scope: src/frob/lang/__init__.py, src/frob/lang/_walk_html.py (new),
src/frob/lang/_walk_javascript.py (new, .js/.jsx alongside the existing
_walk_typescript.py's .ts/.tsx), src/frob/lang/_walk_vue.py (new, SFC-shell
walk only).

tree-sitter-language-pack (already pinned, pyproject.toml) bundles html,
javascript, and vue grammars under those names but none are wired into
_EXTENSION_TABLE today -- confirm via
`from tree_sitter_language_pack import get_parser; get_parser("html")`
etc. before writing any walker. Extend _EXTENSION_TABLE with
.html->("html","html"), .js->("javascript","javascript"),
.jsx->("javascript","javascript") (mirroring .tsx/.ts split), .vue->
("vue","vue"); add matching entries to _SUPPORTED_LANGUAGES/
_TREE_SITTER_EXTENSIONS; write minimal walkers following
_walk_typescript.py's shape (symbol kinds, publicness, comment
extraction) -- thin is fine, most rules in this epic query raw nodes,
not frob.graph symbols; the walker's real job is making parse_file/
raw_tree/symbol_tree not return UnsupportedLanguage for these four
extensions.

Jinja/Django/ERB/Blade templates have NO usable tree-sitter grammar in
language-pack -- sinks inside those templates stay regex/line-scan rules
in the stories that need them, not this leaf's problem.

Positive-control fixture: tests/fixtures/lang/sample.html, sample.jsx,
sample.vue each with one identifiable top-level construct -- assert
frob.lang.parse_file returns Ok and raw_tree is non-empty.

Doc: docs/modules/lang.md's extension table.
