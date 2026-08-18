---
id: T-2389
title: retarget hardcoded src/frob/ literal in _env_var_docs.py and _root_asset_dirs.py
  to the T-2195 source-root resolver
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_env_var_docs.py
- src/frob/gates/_root_asset_dirs.py
- tests/unit/gates/test_env_var_docs.py
- tests/unit/gates/test_root_asset_dirs.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-2384 (source-root retarget half, group 1 of N -- narrow scope
per epic sequencing instruction, not a giant single ticket).

_env_var_docs.py:72 skips every tracked path not starting "src/frob/" --
silent-pass off-repo (ENVDOC reports zero for a src/lograder/ package).
Also hardcodes the FROB_ env-var prefix (same class: derive from project
name, not a literal). _root_asset_dirs.py:112's _referenced_in_src scans
only src/frob/** -- false-positive off-repo (legitimately referenced dirs
reported unreferenced).

Fix: promote frob.lang._nodes._declared_python_source_roots (T-2195) to a
single public home with a repo-relative-prefix form suitable for these
startswith sites; retarget both literals to it; derive env-var prefix from
project name.

Verification: must-now-fire fixture (src-layout project, package name !=
frob, a real ENVDOC/asset-dir violation the gate previously missed) AND
must-still-pass control (this repo's own pre-change finding count
unchanged).