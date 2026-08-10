---
id: T-2012
title: 'SCOPE002 closure gap: _coverage_sites.py''s docs/gates.md and _arch.py test
  citations were never in T-1921''s declared scope'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_arch.py
- src/frob/gates/_coverage_sites.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/modules/gates.md
  reason: gates.md is a giant shared hub doc (310 closure warnings) -- do not lease
    it just to file this residue ticket; investigation and fix belong to whoever works
    this ticket
  actor: logan
  at: '2026-08-10'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Found while working T-1943 (extend per-site examined-sites coverage to
strata/perf/graph/vet). frob check --only gates --ticket T-1943 surfaces
SCOPE002 (scope-closure) findings that are PRE-EXISTING, not caused by
T-1943's own diff:

  - src/frob/gates/_coverage_sites.py::attach_examined_sites/
    is_family_instrumented/site_examined all carry a
    frob:doc docs/modules/gates.md#data-models target -- that file was
    never added to T-1921's (or T-1943's) declared scope.
  - tests/unit/gates/test_examined_sites.py's pre-existing archgate tests
    (test_archgate_examined_sites_include_a_real_python_file,
    test_archgate_examined_sites_exclude_an_unparseable_file) carry a
    frob:tests src/frob/gates/_arch.py::arch_examined_sites target --
    also never added to scope.

Confirmed these are pre-existing by reverting T-1943's scope to its
ORIGINAL declared value (src/frob/gates/_coverage_sites.py only, no
edits): the same 3 gates.md SCOPE002 findings fire against a ticket
whose diff hasn't touched anything yet -- this is a scope-declaration
gap left over from T-1921, not something T-1943 introduced.

Could not fix directly from T-1943: docs/modules/gates.md is under a
live cross-worktree lease (T-2001) at investigation time, and adding
src/frob/gates/_arch.py to scope to close the OTHER edge cascades into
arch_gate's own full test surface (tests/test_arch_gate.py,
tests/unit/test_arch_srp.py -- 16 further scope-closure warnings),
disproportionate to a coverage-family-extension ticket.

Fix: once T-2001 lands and its lease clears, add docs/modules/gates.md
to T-1921's already-closed scope retroactively is not possible (T-1921
is done) -- this needs its own ticket that adds docs/modules/gates.md
(data-models anchor) and, separately, decides whether
arch_examined_sites's frob:tests citation of a src/frob/gates/_arch.py
symbol from this test file is even the right shape (it may be cleaner
to move those two archgate-specific tests into a file already scoped
alongside _arch.py, closing the edge by relocation instead of by
widening scope).