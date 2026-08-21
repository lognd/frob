---
id: T-2771
title: retarget OVER_BROAD_LITERAL_GLOBS off hardcoded src/frob/ literal in tickets/_models.py
state: queued
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: T-2384
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
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
Child of T-2384 (source-root retarget half, group N).

tickets/_models.py:556-557 OVER_BROAD_LITERAL_GLOBS hardcodes the literal
strings "src/frob/**" and "src/frob/" as two of the over-broad-scope
nudge globs large_glob_warnings flags unconditionally. In a sibling repo
whose package is e.g. src/lograder/, a ticket that declares scope
src/lograder/** never gets this nudge -- the exact silent-pass shape T-2384
cites ("22 files" example), just one level up in ticket tooling rather than
a gate.

Fix: derive the package-prefix entries of OVER_BROAD_LITERAL_GLOBS from
frob.lang.declared_source_prefixes(root) (T-2195/T-2389's promoted
resolver) instead of the two hardcoded literals; keep tests/** and docs/**
literal (those are convention-wide, not package-name-derived). Do not add
a second resolver -- import the existing one.

Verification (non-negotiable, both directions):
- must-now-fire fixture: a src-layout project whose package is NOT named
  frob, with a ticket scope of src/<theirpkg>/** or src/<theirpkg>/,
  where large_glob_warnings previously returned nothing for that glob and
  must now flag it.
- must-still-pass control: this repo's own large_glob_warnings finding
  count for src/frob/**-shaped scopes is unchanged after the retarget.

Deliberately excluded (do not touch in this scope): tests/**, tests/,
docs/, docs/** entries in the same frozenset -- those are repo-convention
literals, not project-identity literals, and are correctly frob-agnostic
as-is.