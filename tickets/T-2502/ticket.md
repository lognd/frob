---
id: T-2502
title: 'strata fragments: imports that cannot break a system apart'
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: T-2501
tier: ticket
sprint: null
runs_last: false
scope:
- strata-core/src/parse/
- src/frob/strata/_parse.py
- src/frob/strata/_ast.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/
  reason: 'over-broad: 1915 closure warnings would lease most of the strata package;
    the grammar+loader change lives in the parser and the two parse-layer modules'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/strata/_parse.py
  reason: the .strata loader entrypoint the fragment/glob logic changes
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/strata/_ast.py
  reason: fragment node types (part-of / extend) enter the AST here
  actor: logan
  at: '2026-08-18'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`design/frob.strata` is 2276 lines / 188KB and there is exactly one of
it. Three single lines exceed 5KB (the testsuite node's exec / fs.read /
fs.write via-lists; the largest is 13,479 characters), so every agent
that adds a test file edits the same enormous line. That is a merge
conflict generator and the source of the recurring SELFAUDIT001 ratchet
bumps.

The grammar has NO include/import today (checked: no such keyword in
strata-core/src/parse/). Add one, with the explicit constraint that it
must be IMPOSSIBLE to break a system into pieces that stand alone:

- ONE CLOSURE ROOT. `module frob { ... }` may be declared in exactly one
  file. That declaration IS the system boundary; everything provable is
  proved against it.
- FRAGMENTS EXTEND, THEY DO NOT STAND ALONE. Another file says
  `part of frob` and may only EXTEND declared nodes
  (`extend node testsuite { ... }`). It may not declare a module, may not
  introduce a node the root does not know about, and is meaningless when
  loaded by itself.
- THE LOADER GLOBS, IT DOES NOT INCLUDE. `design/**/*.strata` is read as
  one unit. Exactly one root must exist; a fragment naming a nonexistent
  root is a hard error. There is no textual include, so no one can
  assemble a DIFFERENT system by including different files.

This is Rust's `mod` (files are organizational, the crate is the unit),
not C's `#include` (textual, no closure).

HARD CONSTRAINT: a fragment must never be able to WEAKEN a root
declaration. Extend-only, never override. Otherwise a fragment becomes a
place to quietly grant a capability the root refused -- the
exemption-that-disables-the-guard failure this repo has already paid for
once (T-1967).

Do not mandate modularity: the root may stay whole for anyone who wants
it whole. The point is that mechanically-accumulated content can move out
of the hand-authored design.
