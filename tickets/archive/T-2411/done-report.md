## Done report

Changed:
src/frob/gates/__init__.py::_ALL_GATES (added "capability_conformance")
src/frob/gates/__init__.py::_CANONICAL_GATE_ORDER (added "capability_conformance")
src/frob/gates/__init__.py::_CACHEABLE_GATES (added "capability_conformance")
src/frob/gates/__init__.py::_cacheable_gate_factories (added "capability_conformance" entry)
src/frob/gates/__init__.py::_build_thread_jobs (added "capability_conformance" entry)
src/frob/gates/__init__.py::__all__ (added "capability_conformance_gate")
src/frob/check/__init__.py::_STAGE_GROUPS["gates-fast"] (added "capability_conformance")
tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring (new)

Evidence:
tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring::test_capability_conformance_is_registered_in_all_gates
tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring::test_capability_conformance_fires_through_real_gate_dispatch

Filed: none

Gates: frob check --ticket T-2411 shows 0 errors attributable to any
touched file (src/frob/gates/__init__.py, src/frob/check/__init__.py,
tests/test_lang_conformance_gate.py) -- verified by filtering the JSON
diagnostics. Total repo-wide error count (65, text-mode run: 60) is
concurrent fleet activity, unrelated to this diff. gate:LANG itself:
0 errors, 3 warnings (all pre-existing LANG003 known-gap entries).
frob ticket sweep T-2411 re-run clean.

Summary: wired LANG004 (capability_conformance_gate, built under T-2365)
into frob check's job table, mirroring lang_conformance/
lang_project_conformance's existing wiring exactly (same 5-site pattern:
_ALL_GATES, _CANONICAL_GATE_ORDER, _CACHEABLE_GATES, the cacheable-gate
factory dict, and the thread-job dict). Also added it to
src/frob/check/__init__.py's _STAGE_GROUPS["gates-fast"] (scope widened
via `frob ticket scope --add`, with a reason) -- this file was NOT in
T-2365's or T-2411's original declared scope, but omitting it would have
reproduced the exact "registered in _ALL_GATES but unreachable via
--only <group>" defect class this file's own comment names (the T-1044/
T-1340 lesson), one of this session's three repeated inert-detection
findings (T-2387/T-2438/T-2448) the coordinator flagged.

CONFIRMED FIRING, not just registered: (1) capability_conformance=0.00s
appears in a real `frob check --only gates-fast` run's gate-summary
timing breakdown, proving the job dispatched; (2) direct invocation of
capability_conformance_gate() shows it genuinely parses 7 real language
fixtures (C/C++/Kotlin/Python/Rust/TypeScript/strata) and reports 0
violations -- clean, not absent; (3) added a positive-control wiring
test (test_capability_conformance_fires_through_real_gate_dispatch)
that monkeypatches the python fixture to a broken shape (the SAME broken
continuation shape the gate-level positive control already proves LANG004
catches) and asserts a real end-to-end `run_gates()` dispatch (no --only
filter) surfaces a LANG004 violation -- proving the wiring is live
through the actual default dispatch path, not just present in a set.

Found and fixed in passing (same diff, not a separate ticket): my first
attempt at the _STAGE_GROUPS comment used `# frob:ticket T-2411: LANG004,
...` -- the colon after the ticket id was parsed by the directive scanner
as malformed attribute syntax (WARNING: malformed directive). Restructured
to put `# frob:ticket T-2411` alone on its own line, per every other
directive in the file.

No new capabilities scope widening beyond src/frob/check/__init__.py and
tests/test_lang_conformance_gate.py (both added via `frob ticket scope
--add` with stated reasons, per T-2405's own scope-closure -- consider-
adding warnings noted but not chased for docs/commands/check.md, since no
public symbol in check/__init__.py's own frob:doc-carrying surface was
touched, only a private dict-literal member added).

Per the coordinator's disclosed caution (T-2365): only 4 of 7 capabilities
get real behavioral exercise via LANG004 (call_graph/import_graph/
test_discovery remain structural-only, LANG001's job). This ticket does
not widen that -- confirmed by reading capability_conformance_gate's own
docstring and _BEHAVIORALLY_CHECKED_CAPABILITIES; the disclosure remains
accurate and untouched.

Note: hit the T-2484 hazard (`frob check --json` emitting a
human-readable advisory line to stdout before its JSON body under
concurrent fleet load) on the FIRST several `--ticket T-2411 --json`
attempts. Did not work around it by stripping the prefix in any
production path; used the plain-text `frob check --ticket T-2411`
(unaffected -- the hazard is --json-specific) for the authoritative
human-readable read, and only inspected a raw captured JSON file
directly (skip-leading-line, read-only, manual diagnosis, not a script)
to confirm zero errors against touched files specifically.

### Changed
```
 tickets/T-2411/ticket.md | 23 ++++++++++++++++++++++-
 1 file changed, 22 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring::test_capability_conformance_is_registered_in_all_gates` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring::test_capability_conformance_fires_through_real_gate_dispatch` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
