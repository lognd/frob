---
id: T-4018
title: Cache reads guard fetchone() with 'is not None' but get an empty tuple, so
  row[0] raises IndexError and aborts a gate run (5 sites)
state: in-progress
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/cache.py
- src/frob/dup/_cache.py
- tests/unit/test_graph_cache.py
- tests/unit/test_dup_cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_graph_cache.py
  reason: 'scope closure: T-4018 fixtures live in these test files, whose bound frob:doc/frob:tests
    edges require these paths in scope'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_dup_cache.py
  reason: 'scope closure: T-4018 fixtures live in these test files, whose bound frob:doc/frob:tests
    edges require these paths in scope'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: docs/modules/dup.md
  reason: 'scope closure: T-4018 fixtures live in these test files, whose bound frob:doc/frob:tests
    edges require these paths in scope'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: docs/modules/graph.md
  reason: 'scope closure: T-4018 fixtures live in these test files, whose bound frob:doc/frob:tests
    edges require these paths in scope'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/test_graph.py
  reason: 'scope closure: T-4018 fixtures live in these test files, whose bound frob:doc/frob:tests
    edges require these paths in scope'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/test_graph_lock.py
  reason: 'scope closure: T-4018 fixtures live in these test files, whose bound frob:doc/frob:tests
    edges require these paths in scope'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_graph_build_lock.py
  reason: 'scope closure: T-4018 fixtures live in these test files, whose bound frob:doc/frob:tests
    edges require these paths in scope'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: docs/modules/dup.md
  reason: 'revert: whole-module docs pulled in transitive closure across unrelated
    files far beyond T-4018''s actual change; the frob:doc directive on the touched
    symbols was pre-existing before this ticket, not introduced by it'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: docs/modules/graph.md
  reason: 'revert: whole-module docs pulled in transitive closure across unrelated
    files far beyond T-4018''s actual change; the frob:doc directive on the touched
    symbols was pre-existing before this ticket, not introduced by it'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/test_graph.py
  reason: 'revert: these wide-coverage test files carry frob:tests reverse-edges into
    dozens of unrelated modules (T-3914 precedent), pulling nearly the whole graph/dup
    subsystem into scope for a guard-only fix; waiving SCOPE002 for the resulting
    cross-file suggestions instead'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/test_graph_lock.py
  reason: 'revert: these wide-coverage test files carry frob:tests reverse-edges into
    dozens of unrelated modules (T-3914 precedent), pulling nearly the whole graph/dup
    subsystem into scope for a guard-only fix; waiving SCOPE002 for the resulting
    cross-file suggestions instead'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/unit/test_graph_build_lock.py
  reason: 'revert: these wide-coverage test files carry frob:tests reverse-edges into
    dozens of unrelated modules (T-3914 precedent), pulling nearly the whole graph/dup
    subsystem into scope for a guard-only fix; waiving SCOPE002 for the resulting
    cross-file suggestions instead'
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED IN CI, ubuntu leg of run 34019760758 (ca586645c). One test failure out
of 13502, and it is not a test defect -- it is a real crash in the cache layer:

    def _op(c: sqlite3.Connection) -> str | None:
        row = c.execute(
            "SELECT payload FROM parsed_artifacts "
            "WHERE content_hash = ? AND fingerprint = ?",
            (content_hash, fingerprint),
        ).fetchone()
    >   return row[0] if row is not None else None
    E   IndexError: tuple index out of range

THE GUARD CHECKS THE WRONG CONDITION. `fetchone()` returned an EMPTY TUPLE, not
None. `row is not None` is therefore True, and `row[0]` raises. The correct guard
for "no usable row" is truthiness -- `if row` -- which covers both None and ().
This is a one-character class of bug with a real consequence: an uncaught
IndexError out of the parse cache aborts whatever gate run is in flight.

IT IS NOT AN ISOLATED LINE. The identical construct appears at five sites:

    src/frob/graph/cache.py:811, 1679, 1721, 2016
    src/frob/dup/_cache.py:114

All five have the same latent failure. FIX ALL FIVE, and check whether other
fetchone() call sites in the codebase use a different-but-equally-wrong guard --
a sweep, not a point fix, because the reported line was only the one that
happened to be hit.

THE HARDER QUESTION, AND DO NOT SKIP IT: WHY WAS THE TUPLE EMPTY? A
`SELECT payload FROM ...` returning a zero-column row is not normal sqlite
behaviour. Fixing the guard makes the crash stop, and if the underlying cause is
cache corruption or a concurrency fault, the guard turns a loud crash into a
SILENT CACHE MISS -- which is strictly worse for diagnosis and is exactly the
silent-zero shape this queue exists to prevent. So:
  - Fix the guard (a crash is not an acceptable outcome either way), AND
  - LOG at WARNING when a row is present but empty, naming the table and the
    keys, so the underlying condition stays visible rather than being swallowed.
Candidate causes worth checking: concurrent access under xdist (this failed on
one worker while the same test passes standalone), a row_factory interaction, or
a partially-written row from an interrupted INSERT at cache.py:1978.

REPRODUCTION STATUS, stated honestly: the test passes locally when run alone
(`exitstatus=0 collected=1 failed=0`). It failed on gw1 under a full 13502-test
xdist run. So this is load- or concurrency-dependent and a single-test rerun is
NOT evidence it is fixed. Any fix must be argued from the code path, and the
must-fire fixture must construct the empty-row condition directly rather than
hoping to reproduce the race.

MUST-FIRE FIXTURE: a fetchone() returning () is handled as "no cached value", not
as a crash -- constructed directly, not raced.
MUST-STAY-QUIET: a genuine cached payload is still returned unchanged.
THIRD FIXTURE: the empty-row condition emits a warning naming table and keys, so
fixing the crash does not hide the cause.

ACCEPTANCE
- All five sites fixed, plus any others the sweep finds, each listed.
- Empty-but-present rows logged, not silently treated as a miss.
- A stated hypothesis for the underlying cause, with whatever evidence the code
  path supports -- or an explicit "not determined", never a silent assumption.
- All three fixtures committed.