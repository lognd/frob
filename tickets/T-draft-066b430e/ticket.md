---
id: T-draft-066b430e
title: 'H3-10: a declaration glob matching zero files must be its own finding, distinct
  from capability-unobserved'
state: queued
kind: security
origin: human
created: '2026-09-06'
priority: critical
parent: T-4109
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_selfconform_kinds.py
- src/frob/strata/_selfconform_core_rules.py
- tests/unit/strata/test_selfconform_kinds.py
- tests/unit/strata/test_selfconform_core_rules.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: 'close scope-closure warning: shared frob:tests target for _selfconform_core_rules/_selfconform_kinds
    helpers'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/unit/strata/test_selfconform.py
  reason: 'revert: dragged in a 76-warning transitive closure across the whole selfconform
    test file; use a new dedicated test file instead'
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-307 H3-10 (verbatim, quoted at the bottom of T-4109's body). A "may" grant's
via/code= glob whose pattern matches zero files on the current branch is
accepted silently today; the only signal is SELFAUDIT001/SYS101's declared-but-
unobserved finding, which the standing T-0002 waivers then suppress. That
collapses two different facts into one waivable signal: "the code is here and
does not use the capability" versus "the code named by this glob is not here
at all" (a typo, a rename, a deleted file).

VERIFIED against code before filing: src/frob/strata/_selfconform_kinds.py's
_fully_excluded_node_ids already documents this exact gap in its own
docstring -- "a glob matching nothing at all is a different, pre-existing
case (e.g. a typo'd glob) left to fire SYS101 unchanged, since that is
genuine potential drift, not a structurally-unobservable node." That is the
epic's H3-10 claim, confirmed in the running code, not asserted from the
report alone.

VERIFIED shape of the fix: T-3985's subject-count primitive (src/frob/
process/parsers/common.py's enforcing_zero_subject_diagnostic, wired via
src/frob/check/_python.py's _SUBJECT_COUNT_PROBES) is a proof-of-concept for
ONE gate family (PROFILE001) at gate-family granularity: a probe counts total
subjects a gate examined across the whole run and flags zero as its own
finding, never conflated with "no rule migrated yet" (subject_count stays
None). H3-10 needs the same never-conflate-zero-with-unmeasured doctrine, but
at declaration granularity: per grant/per glob, not per gate run. Do not
reuse _SUBJECT_COUNT_PROBES's dict or its ToolResult.subject_count field
directly (wrong shape, wrong granularity) -- reuse the doctrine and, where the
diagnostic shape fits, the frob.process.parsers.common.Diagnostic construction
pattern that primitive follows. This is a natural sibling of SYS109's stale-
via-symbol check (src/frob/strata/_effects.py's check_stale_via_symbols),
which already fires for a symbol-form via resolving to zero matches; this
finding extends the same reasoning to plain glob-form via and to a node's
code= globs, giving it a distinct rule id (do not fold into SYS101 or SYS109).

Work:
- new rule id (suggest SYS110) fired when a node's may-grant via glob (or a
  node's own code= glob) matches zero real (skip-dir-filtered, non-excluded)
  files on the current branch
- distinct from SYS101 (declared-but-unobserved: glob matches real files,
  none exercise the capability) and from SYS109 (a symbol-form via entry
  resolves against >=1 candidate file but finds no matching symbol) -- SYS110
  fires only when the candidate-file count itself is zero
- must NOT fire for a node already covered by _fully_excluded_node_ids's
  graph-exclude carve-out (that is a different, legitimate zero)
- wire into frob check's gate set and docs/modules/gates.md's rule catalog

Fixtures (buildable in frob's own tree -- this is a strata self-model
mechanism, not backend-shaped):
- must-fire: a design node whose code= (or a grant's via=) names a glob for a
  file that does not exist in the fixture tree at all (e.g. a renamed
  module, glob left stale)
- must-stay-quiet (real zero-match, correctly distinct case): a node whose
  entire glob resolves only to graph-excluded paths (the existing
  _fully_excluded_node_ids carve-out) -- must NOT fire SYS110
- must-stay-quiet (already-covered case): a node whose glob matches >=1 real
  file with zero observed capability use -- fires SYS101 only, never SYS110
- third: a node whose glob matches >=1 real file that DOES exercise the
  capability -- clean, neither rule fires

frob:ticket T-4109