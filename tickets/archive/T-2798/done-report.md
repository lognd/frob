## Done report

Changed:
- src/frob/vet/_capability_python.py::_python_binding_capabilities
- src/frob/vet/_capability_python.py::_python_local_wrapper_capabilities
- src/frob/vet/_capability_python.py::_python_resolved_candidates (docstring only, sizing note)
- src/frob/vet/_capability_scan.py::scan_file_capabilities
- docs/modules/vet.md#one-hop-public-cross-file-wrapper-resolution-t-2223
- tests/unit/test_capability_native.py::TestResolvedCandidatesThreading (new)

Decision (the ticket's real deliverable): a cross-invocation, content-hash
disk cache for `scan_file_capabilities`'s python path was SIZED AND
DECLINED. Two findings drove this:

1. Profiling (cProfile over an isolated `scan_file_capabilities` sweep of
   this repo's 1224 python files) showed `_python_resolved_candidates`
   at 2448 calls / 1224 files -- called TWICE per file, once from
   `_python_binding_capabilities`, once from `_python_local_wrapper_
   capabilities` -- and it is a PURE function of the file's own content
   only (`raw_tree(path)` is its only I/O). The dominant redundancy the
   parent investigation flagged is intra-process call duplication, not
   missing cross-run caching.

2. A naive content-hash cache keyed on `path` alone would be UNSOUND:
   `_python_local_wrapper_capabilities` reads a SIBLING file's content
   (`_wrapper_function_capabilities` on the one-hop-resolved import
   target) -- a sibling's own change (e.g. a previously-benign wrapper
   function starts calling `os.system`) would silently miss under a
   path-content-only key, exactly the "silent zero" class this repo
   treats as its dominant bug class. A sound version is possible (key on
   path content + every same-directory .py sibling's content, since the
   honest-limit note already bounds the dependency set to that
   directory) but needs new directory-listing I/O and key-construction
   machinery this ticket's own profile does not show is worth building
   yet.

My first fix attempt (`@memoize_per_run` on `_python_resolved_
candidates`, reusing `frob.check._memo`) was WRONG and reverted before
landing: importing `frob.check._memo` from `frob.vet` creates a
`vet -> checker` edge that does not exist in `design/frob.strata` today,
and the file itself documents (line ~2052) that the ABSENCE of that edge
is what lets `assume "weakness:CWE-78:checker" noflow registry ->
checker` be "provably true, not merely assumed" -- adding the edge would
have refuted a security proof to save time on a lint gate. Caught by
SYS003 on a full `frob check` run, not by inspection -- worth noting for
anyone tempted to memoize across a component boundary here again.

The LANDED fix instead: `scan_file_capabilities` now computes
`_python_resolved_candidates(path)` ONCE and threads the tuple into both
`_python_binding_capabilities` and `_python_local_wrapper_capabilities`
via a new optional `candidates` parameter (`None` on every other/
existing caller recomputes exactly as before -- zero behavior change for
anyone not on this one call path). No new cache layer, no cross-run
staleness surface, no cross-component import.

Measured effect (isolated `scan_file_capabilities` sweep over this
repo's 1224 python files, fleet-contended, LOAD 3.6-7.4 throughout --
flagged explicitly, not averaged silently):
- run 1: 20.88s -> 13.15s (37% reduction)
- run 2: 23.90s -> 16.75s (30% reduction)
An earlier cProfile-instrumented measurement showed 85% of this sweep's
time inside the duplicated call; the real (uninstrumented) win is much
smaller than that because cProfile's per-call overhead is itself
proportional to call count and this function makes millions of recursive
sub-calls -- flagging this explicitly since the cProfile number would
otherwise overstate the real-world effect. This lands as a real, safe,
small win on one sub-component of `sys`, not the large win T-2790's
"largest raw stage" framing might suggest -- the ticket's own framing
(least de-risked of the four) is confirmed correct.

Finding-set check: `frob check --ticket T-2798 --json` (unbudgeted, real
`gate-summary` present) before and after this diff shows the SAME set of
(rule, file) identities not touching the two changed source files or
this ticket's own test additions -- the only NEW findings my diff
produced (SYS003 cross-component import, ARCH001 line-count, AFFECT001
stale doc, COV002 missing frob:ticket edge, SCOPE001 out-of-scope test
file) were all fixed in this same change (revert the memo import,
trim the function under 60 lines, update docs/modules/vet.md, add
frob:ticket to the new test class, extend ticket scope to cover the test
file and the doc). Remaining errors on both runs are pre-existing fleet
noise (CLAUDE001 config drift, DOC/DRIFT/TICK ledger churn from other
agents, etc.) with no relation to `_capability_scan.py`/
`_capability_python.py`.

Positive controls (both directions, per T-2798's hard requirement):
- HIT-equivalence: `test_binding_capabilities_with_and_without_
  precomputed_candidates_agree` / `test_local_wrapper_capabilities_
  with_and_without_precomputed_candidates_agree` assert the threaded-
  candidates result equals the internally-recomputed result byte-for-
  byte, on a real exec-shaped fixture.
- MISS/still-detects: `test_scan_file_capabilities_still_resolves_
  cross_file_wrapper` proves the one-hop sibling-wrapper case (the one a
  naive content cache would break) still fires end-to-end.
- Genuine change is seen: `test_scan_file_capabilities_sees_a_genuine_
  sibling_change` writes a benign sibling, scans, then makes the sibling
  genuinely dangerous and scans again -- the second scan sees the new
  capability, proving there is no accidental caching anywhere on this
  path.

Evidence: 4 new tests in tests/unit/test_capability_native.py::
TestResolvedCandidatesThreading, bound via `frob ticket evidence`.

Filed: none -- no out-of-scope work discovered. The sound disk-cache
design (path content + same-directory sibling contents) is documented
above and in `_python_resolved_candidates`'s docstring for a future
ticket if profiling later shows the smaller win here is insufficient;
not filed as a new ticket since T-2798's own disposition already covers
it and a fresh ticket would just restate this Done report.

Gates: `frob check --ticket T-2798` unbudgeted run clean of any
finding touching the changed files (SYS003/ARCH001/AFFECT001/COV002/
SCOPE001 all resolved in this same change, verified by re-running after
each fix); pre-work sweep refreshed via `frob ticket sweep T-2798`.

### Changed
```
 docs/modules/vet.md                  |  9 ++++
 src/frob/vet/_capability_python.py   | 71 ++++++++++++++++++++------
 src/frob/vet/_capability_scan.py     | 20 +++++++-
 tests/unit/test_capability_native.py | 98 ++++++++++++++++++++++++++++++++++++
 tickets/T-2798/ticket.md             | 21 +++++++-
 5 files changed, 202 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/unit/test_capability_native.py::TestResolvedCandidatesThreading::test_binding_capabilities_with_and_without_precomputed_candidates_agree` (pytest node id, verified passing when recorded)
- `tests/unit/test_capability_native.py::TestResolvedCandidatesThreading::test_local_wrapper_capabilities_with_and_without_precomputed_candidates_agree` (pytest node id, verified passing when recorded)
- `tests/unit/test_capability_native.py::TestResolvedCandidatesThreading::test_scan_file_capabilities_still_resolves_cross_file_wrapper` (pytest node id, verified passing when recorded)
- `tests/unit/test_capability_native.py::TestResolvedCandidatesThreading::test_scan_file_capabilities_sees_a_genuine_sibling_change` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 21 error(s), 1274 warning(s), 714 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
