---
id: T-3415
title: Extend DOC010/docmake_gate to scaffold .j2 template pairs
state: queued
kind: docs
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docstatus.py
- src/frob/scaffold/data/**
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
T-3410 found and fixed a real regression: T-3400 trimmed
shared/python/Makefile.j2's targets but left shared/python/docs/index.md.j2
citing the deleted make targets (check/test/lint/typecheck), so a
scaffolded project's FIRST doc a new user reads instructed commands that
fail with "No rule to make target". Nothing caught this at land time.

DOC010 (docmake_gate, src/frob/gates/_docstatus.py) already does exactly
this check -- resolves `make <target>` citations in obligated docs
against the nearest Makefile (T-2705's walk-up-then-root-fallback) -- but
it structurally cannot cover this case:

1. _obligated_docs only considers real, frob:doc-obligated markdown files.
   Scaffold templates (*.md.j2) are data/template source, not obligated
   docs, so they are never in its scan set at all.
2. _makefiles_for_doc resolves by directory-nearest-Makefile walk. Scaffold
   templates need MANIFEST-based resolution instead: which Makefile.j2 a
   given .md.j2 pairs with is decided by src/frob/scaffold/project.py's
   per-type _ManifestEntry composition (shared/python/docs/index.md.j2
   pairs with shared/python/Makefile.j2 for python-library, but
   types/python-tool/docs/index.md.j2 -- a sibling directory, not an
   ancestor -- pairs with the SAME shared/python/Makefile.j2 for
   python-tool). Directory-nearest walking cannot express this; at least
   4 types override Makefile.j2 independently of whether they override the
   README/docs template (T-3400/T-3410's own finding), so a naive
   extension would silently mis-pair or miss overrides.

PROPOSAL: a scaffold-specific check (either a new DOC01x rule or a
generalization of docmake_gate behind a scaffold-aware resolver) that:
  - renders/parses each type's manifest via project.py's own
    _ManifestEntry tables to get the EFFECTIVE (doc, Makefile) pairing
    per type, not filesystem proximity
  - reuses _MAKE_TARGET_CITATION_RE/_makefile_targets's existing parsing
    (do not reinvent the make-target regex or target-name extraction)
  - fires when a *.md.j2's `make <target>` citation names a target absent
    from its type's effective Makefile.j2

MUST-FIRE: a scaffold doc referencing a make target absent from its own
type's shipped Makefile.j2 (T-3410's exact regression, reproducible as a
fixture).
MUST-STAY-QUIET: cpp/web-app/pyo3/pybind11 doc references to targets
their own Makefile.j2 really has.

Filed per T-3410's gate-rule question (owner directive): the incident is
real and this rule would have caught it at land time, but building it
is real design work (manifest-aware resolution, not a directory walk),
not a same-ticket fix -- filed as its own ticket rather than silent scope
creep on T-3410.