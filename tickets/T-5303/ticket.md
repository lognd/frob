---
id: T-5303
title: Wire CSS/SCSS grammar into frob.lang (contrast/target-size/hidden-text substrate)
state: done
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5140
tier: ticket
sprint: ''
runs_last: false
milestone: 0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/__init__.py
- src/frob/lang/_walk_css.py
- docs/modules/lang.md
- tests/fixtures/lang/sample.css
- tests/fixtures/lang/sample.scss
- src/frob/lang/_extract.py
- tests/test_lang_css.py
- src/frob/lang/_support.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/lang/**
  reason: narrow to the two new fixtures this ticket adds
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/fixtures/lang/sample.css
  reason: narrow to the two new fixtures this ticket adds
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/fixtures/lang/sample.scss
  reason: narrow to the two new fixtures this ticket adds
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/lang/_extract.py
  reason: CSS/SCSS walkers must be wired into the shared _WALKERS/COMMENT_TYPES dispatch
    tables alongside _EXTENSION_TABLE
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/test_lang_css.py
  reason: positive-control unit tests for the CSS/SCSS walker, in a dedicated file
    to avoid colliding with T-5300 editing tests/test_lang.py concurrently
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/lang/_support.py
  reason: register the disclosed capability/dup/docblock FACETS KNOWN_GAP for css/scss,
    the same one-line registry entry zig/T-3513 made, so LANG003 does not flag the
    new languages as an unsound gap
  actor: logan
  at: '2026-09-23'
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
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.534.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.534.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.534.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.534.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.534.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.534.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.534.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.534.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.534.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
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
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/test_lang_css.py::TestCss::test_css_is_a_supported_language
- tests/test_lang_css.py::TestCss::test_parse_css_sample
- tests/test_lang_css.py::TestCss::test_positive_control_raw_tree_is_non_empty
- tests/test_lang_css.py::TestCss::test_top_level_rule_set_is_a_class_symbol
- tests/test_lang_css.py::TestCss::test_nested_rule_inside_media_is_not_a_top_level_symbol
- tests/test_lang_css.py::TestScss::test_scss_is_a_supported_language
- tests/test_lang_css.py::TestScss::test_parse_scss_sample
- tests/test_lang_css.py::TestScss::test_positive_control_raw_tree_is_non_empty_nested_selector
- tests/test_lang_css.py::TestScss::test_dollar_variable_is_a_const_symbol
- tests/test_lang_css.py::TestScss::test_top_level_rule_set_is_a_class_symbol
- tests/test_lang_css.py::TestScss::test_line_comment_is_recognized
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5303
branch: t-5303
---
NEW leaf (owner-added): A11Y (T-5146-3, T-5146-4) and SEO (T-5147-3) need a real CSS/SCSS grammar for contrast-ratio computation, outline:none detection, target-size box computation, and hidden-text (color==background/font-size:0/opacity:0) detection -- confirm tree-sitter-language-pack's css grammar covers SCSS syntax or pin a dedicated tree-sitter-scss grammar if not. Wire .css/.scss into _EXTENSION_TABLE the same way WEBSUB-1 wires html/js/jsx/vue; write a thin _walk_css.py walker. Positive-control fixture: tests/fixtures/lang/sample.{css,scss}. T-5146-3, T-5146-4, and T-5147-3 block on this leaf.