---
id: T-4133
title: 'frob check: flag a setuptools package-data glob that matches zero files'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/_python.py
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
Found while working T-4132 (py.typed declared in package-data but the file
did not exist, so the declaration matched zero files and the built wheel
silently shipped without it).

Setuptools' package-data does not error on a glob pattern that matches no
file under a package -- it just includes nothing. This is a general defect
class: any package-data entry can silently rot to zero matches (a renamed
file, a moved directory, a typo) and nothing in this repo's own gates would
catch it. frob check already enforces type discipline and doc/test
coverage on itself; an unenforced packaging claim is the same class of
silent-zero this repo has flagged elsewhere.

WHAT TO DO
  Add a check (in src/frob/check, wired into the standard gate set) that:
  1. Parses [tool.setuptools.package-data] from pyproject.toml.
  2. For each declared package and glob pattern, resolves it against the
     actual package source tree (the root setuptools would use, e.g.
     src/<package>/).
  3. Fails the gate if any pattern matches zero files.

ACCEPTANCE
- A synthetic package-data entry with a pattern matching zero files fails
  the new check (MUST-FIRE).
- This repo's own current package-data entries (py.typed,
  scaffold/data/**/*.j2, scaffold/data/**/*.toml, logging/config.toml) all
  pass once T-4132 lands (MUST-STAY-QUIET).
- Wired into `frob check`'s standard gate set with a rule id and doc entry.
