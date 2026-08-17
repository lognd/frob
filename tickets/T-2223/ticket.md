---
id: T-2223
title: Capability scan misses cross-file call indirection (wrapper laundering across
  node boundary)
state: done
kind: security
origin: human
created: '2026-08-16'
priority: critical
parent: T-1623
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/vet/_capability.py
- src/frob/vet/_capability_scan.py
- src/frob/vet/_capability_core.py
- docs/modules/vet.md
- src/frob/vet/_capability_python.py
- tests/test_vet.py
evidence_scope:
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/vet.md
  reason: 'close scope-closure warning: vet capability functions'' frob:doc target
    lives here'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/vet/_capability_python.py
  reason: 'MEASURED: _python_resolved_candidates (the binding machinery the ticket
    names for extension) is defined in _capability_python.py, not in the three files
    originally scoped -- _capability.py/_capability_scan.py/_capability_core.py only
    call it, they do not define per-language binding candidate resolution'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_vet.py
  reason: test evidence for T-2223's public cross-file wrapper capability fix
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_vet.py::TestCapabilityScan::test_public_sibling_wrapper_exec_is_resolved_one_hop
- tests/test_vet.py::TestCapabilityScan::test_wrapper_with_no_dangerous_body_resolves_nothing
- tests/test_vet.py::TestCapabilityScan::test_wrapper_two_hops_away_is_not_followed
- tests/test_vet.py::TestCapabilityScan::test_sibling_in_a_different_directory_is_not_followed
- tests/test_vet.py::TestCapabilityScan::test_wrapper_capabilities_resolve_cross_file_via_call_graph
- tests/test_vet.py::TestCapabilityScan::test_wrapper_capabilities_ignore_unrelated_cross_file_calls
designated_repro_test: tests/test_vet.py::TestCapabilityScan::test_public_sibling_wrapper_exec_is_resolved_one_hop
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured (T-1623 premise check): scan_file_capabilities is strictly per-file with no cross-file call resolution. Positive control: file A defines run(cmd) calling os.system(cmd) (scans as exec, correctly); file B does 'from a import run; run(x)' and calls nothing else dangerous directly -- scan_file_capabilities(B) returns frozenset() on current main. Any node whose code= binds only file B therefore shows zero observed capabilities even though its code exercises exec through A's wrapper, so SYS100/THREAT004 never flags B for an undeclared exec grant and a reviewer auditing B's node sees a clean capability surface. This is the concrete instance of T-1623's 'capability detection is lexical rather than symbol-resolved' claim -- not fixable by adding more substring needles (token/grammar directive: no re.search escape hatch). Acceptance: a regression test with the two-file fixture above MUST fail on current main (asserting B's resolved capability set includes exec, or that the selfconform join surfaces it for B's node) and must pass after the fix. The fix must follow same-package local-import call edges to at least one hop (extend the existing _python_resolved_candidates/binding machinery already used for import aliasing rather than inventing a parallel path) -- do not special-case the fixture's function name. Do NOT attempt full points-to/whole-program resolution; state explicitly in the module docstring what hop-depth is covered and what remains an honest limit, same style as the existing T-0209/T-0244 gap statements in _capability.py.

## Done report

Threat closed: a project-local capability node whose declared code=
binds only a PUBLIC-wrapper caller file (never the file that actually
performs the dangerous operation) showed a clean SYS100/THREAT004
capability surface while genuinely executing an undeclared capability
through that wrapper -- an auditor reviewing that node's own capability
diff would see nothing wrong. Confirmed live with the planner's own
positive control: a.py defines def run(cmd): os.system(cmd) (public,
scans as exec on its own); b.py does from a import run; run(x) and
calls nothing else dangerous directly.
scan_file_capabilities(b.py) returned frozenset() on main.

Root cause, measured directly (not guessed): T-1752 already closed the
PRIVATE-callee cross-file wrapper shape via a real call-graph edge
(frob.graph.callgraph). That graph, by its own T-0841 design rule,
records an edge ONLY for a private (underscore-prefixed) callee.
Confirmed by direct invocation: _build_wrapper_call_graph(root, [...])
against the exact fixture returns graph.calls == {} (empty) because
run() is public -- no edge is ever recorded, so _python_wrapper_
capabilities(b.py, ...) returns set() too. T-1752's own docstring
already names this as "a disclosed remaining gap, not a false
accusation" for the call-graph path.

Fix: a SECOND, narrower resolver (_python_local_wrapper_capabilities,
src/frob/vet/_capability_python.py), not a widening of T-1752's call
graph (which would risk false attribution against public symbols
generally, T-0841's own concern). Reuses the EXACT SAME import/binding
machinery _python_resolved_candidates already builds for ordinary
intra-file resolution (_py_import_table, _build_py_alias_table,
_collect_py_candidates) -- extended, not a new substring needle
anywhere. One hop: when a resolved call target's module part is a bare
(non-dotted) top-level import name that resolves to a file in the SAME
DIRECTORY, that file's named function body is walked with the identical
resolver, scoped to just that one function -- the hop stops there by
construction.

Honest limits, each with its own regression test proving the gap is
real (not merely undocumented, matching the module's own "documented,
not hidden" posture):
- test_wrapper_two_hops_away_is_not_followed -- a wrapper forwarding to
  a second wrapper in a third file is NOT followed (chain, not a single
  indirection).
- test_sibling_in_a_different_directory_is_not_followed -- a package-
  qualified import (from pkg.a import run) is NOT resolved; only a
  same-directory sibling.
- test_wrapper_with_no_dangerous_body_resolves_nothing -- must-still-
  pass control: an ordinary public helper with no dangerous call in its
  own body is never falsely attributed a capability.

Repro: test_public_sibling_wrapper_exec_is_resolved_one_hop committed
alone at be2ef8c4a, confirmed FAILED_AT_PARENT via `frob ticket
evidence --check-repro ... --base-ref be2ef8c4a`. Fix committed
separately at 936899c2c; doc/gate follow-up at a348d6139.

Tests: 36 passed in tests/test_vet.py::TestCapabilityScan (was 32
before this ticket), `uv run pytest tests/test_vet.py::TestCapabilityScan
-o addopts="" -q` -- "36 passed". Full touched file
(`tests/test_vet.py`, 461 tests total): `uv run pytest tests/test_vet.py
-o addopts="" -q` -- "461 passed in 99.25s", including T-1752's own two
wrapper-attribution tests unchanged (must-still-pass: private-callee
attribution still works, this fix does not touch or narrow it).

`frob check --ticket T-2223`: 0 errors attributable to
src/frob/vet/_capability.py, _capability_python.py, tests/test_vet.py,
or docs/modules/vet.md (checked directly against the JSON diagnostics
for each path). 33 pre-existing repo-wide errors remain, none in these
four files (ARCH001 line-count thresholds on unrelated functions,
DOC011 stale ticket-id citations, TICK004 ticket-rot, ruff E501 on
unrelated files, frob-cycle import cycles).

Scope widened beyond the declared three files: src/frob/vet/
_capability_python.py (measured -- _python_resolved_candidates, the
binding machinery the ticket names for extension, is defined there, not
in _capability.py/_capability_scan.py/_capability_core.py, which only
call it) and tests/test_vet.py (test evidence).

Cut: frob.graph.callgraph's private-callee-only rule (T-0841) is
untouched -- this fix does not widen it, by design (widening it would
risk false attribution against public symbols generally, a different
and much larger-blast-radius change). A wrapper chain of more than one
hop, or a package-qualified cross-directory import, remains a disclosed
gap (each has its own regression test proving it, per above) -- not
fixed here, consistent with the ticket's explicit "do NOT attempt full
points-to/whole-program resolution" instruction.

### Changed
```
 docs/modules/vet.md                |  46 ++++++++++++++
 src/frob/vet/_capability.py        |   8 +++
 src/frob/vet/_capability_python.py | 126 +++++++++++++++++++++++++++++++++++++
 tests/test_vet.py                  |  86 +++++++++++++++++++++++++
 tickets/T-2223/ticket.md           |  28 ++++++++-
 5 files changed, 292 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScan::test_public_sibling_wrapper_exec_is_resolved_one_hop` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_wrapper_with_no_dangerous_body_resolves_nothing` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_wrapper_two_hops_away_is_not_followed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_sibling_in_a_different_directory_is_not_followed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_wrapper_capabilities_resolve_cross_file_via_call_graph` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_wrapper_capabilities_ignore_unrelated_cross_file_calls` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2223/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2223/tests/test_ticket_work_and_land_finish.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
