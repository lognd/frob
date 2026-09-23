---
id: T-5391
title: 'frob-exports: frob.lang._walk_css.walk_scss missing from src/frob/lang export
  policy'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-5382 on dev tip (T-5303 landed the CSS/SCSS walker since): tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols fails for src/frob/lang with ['lang._walk_css.walk_scss'] -- walk_css passes only by accident (the '_walk_css' module-name comment substring-matches 'walk_css'), but 'walk_scss' has no textual mention anywhere in src/frob/lang/__init__.py. Add a mention of walk_scss (e.g. extend the existing _walk_css comment) so frob-exports stops flagging it. Out of T-5382's scope (doctor.py-only) and could not be fixed directly: src/frob/lang/__init__.py is leased by in-progress T-5300.