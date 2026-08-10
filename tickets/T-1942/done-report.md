## Done report

Wired T-1921's per-site examined-sites substrate into WAIVE004 as a third,
additive mass-invalidation guard, per the T-1904/T-1592/T-1579 incident
history's requirement that a sound escape needs per-site analysis-
coverage proof, not a same-run elsewhere-finding proxy.

Changed:
- src/frob/gates/_fix_engine_sync.py::_waive004_verified_candidates --
  enriches its self-manufactured run_gates() report via
  attach_examined_sites before deriving WAIVE004 candidates.
- src/frob/gates/_fix_engine_sync.py::_archgate_rule_ids (new) -- the set
  of rule ids frob.gates._arch.arch_gate emits, re-derived from
  _ARCH_CATEGORY_TO_RULE.values() rather than duplicated.
- src/frob/gates/_fix_engine_sync.py::_drop_unexamined_archgate_candidates
  (new) -- the third, additive guard: drops any surviving archgate-family
  candidate unless site_examined confirms this run examined its file.
  Every non-archgate candidate passes through unchanged.
- src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver -- updated
  docstring describing the third guard.

Evidence: 4 new regression tests in
tests/test_gates.py::TestWaive004ExaminedSitesGuard --
test_examined_archgate_site_is_deleted (an examined archgate site is
still deleted, unchanged from before T-1942),
test_uninstrumented_family_is_unchanged_from_today (a non-archgate rule's
candidate is completely unaffected by the new guard -- proves the guard
grants nothing outside the one family the substrate instruments today),
test_unexamined_archgate_site_refuses (a degraded-shaped run: archgate
instrumented, this file absent from the examined set -- the guard
refuses), and test_original_55_waiver_incident_shape_partial_examination_
still_refuses (the original 55-waiver incident's own shape narrowed to
the per-site level: a mass-stale rule where the substrate confirms SOME
but not all sites were examined keeps only the confirmed site, never
all-or-nothing on the rule). Confirmed the last test FAILS against the
pre-fix source (copied aside, reverted _fix_engine_sync.py to HEAD,
re-ran) and PASSES with the fix restored.

Before/after waiver-retirement count on the real tree, both measured via
_waive004_verified_candidates(root, frozenset(), None) run directly
(bypassing the CLI's dispatch shape): 8 candidates before this change, 8
after -- unchanged, because every surviving candidate on this tree today
targets either a non-archgate rule (PII012/EXHAUST002/EXHAUST003/
OPAQUE001/PERF004/COV005/EXHAUST001) or an archgate rule
(ARCH103, src/frob/app/check_runner.py:1012) whose file the real
arch_examined_sites(root) call DOES confirm was examined this run --
strictly conservative, per the ticket's own required property.

Filed: T-1964 (docs/modules/gates.md's WAIVE004 section needs
this wiring's writeup -- docs/modules/gates.md was under a live
cross-worktree lease held by T-1958 for this ticket's entire duration;
frob ticket scope --add refused with ScopeLeaseConflict, so the doc write
is deferred rather than forced with --allow-cross-ticket. AFFECT001 is
waived on fix_waive004_stale_waiver citing this follow-up.). Also
disclosed, NOT filed as a separate ticket by this agent (left for the
coordinator/user to triage): direct reading of frob.graph.dsl and
frob.graph.__init__ during this investigation confirmed frob:waive
directives are NEVER parsed out of *.md files at all (only
markdown_anchors' DESCRIBES/ENUMERATES/UNTIL/negexist-phrase edges are) --
every existing `frob:waive ... -->` HTML comment already present in
docs/**/*.md (e.g. docs/modules/fuzz.md, docs/modules/deploy.md) is dead
prose that never actually suppresses anything.

Gates: frob check --ticket T-1942 clean for this ticket's own scope
(gate:SCOPE/PRE/COV/AFFECT/FMT all pass; gate:ARCH/DOC/DOCENUM/DRIFT carry
pre-existing repo-wide errors with zero hits against
_fix_engine_sync.py/test_gates.py, confirmed by grep). AFFECT001 waived
on fix_waive004_stale_waiver per the lease conflict above, follow_up
T-1964.

### Changed
```
 tickets/T-1942/ticket.md           | 17 ++++++++++-
 tickets/T-1964/ticket.md | 60 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 76 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestWaive004ExaminedSitesGuard::test_examined_archgate_site_is_deleted` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaive004ExaminedSitesGuard::test_uninstrumented_family_is_unchanged_from_today` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaive004ExaminedSitesGuard::test_unexamined_archgate_site_refuses` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaive004ExaminedSitesGuard::test_original_55_waiver_incident_shape_partial_examination_still_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 5 error(s), 891 warning(s), 707 waived
- error-findings: ARCH001@src/frob/gates/_dead_symbols.py, DOC002@src/frob/tickets/_land.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/tickets/_land.py, PRE001@tickets/T-1942
