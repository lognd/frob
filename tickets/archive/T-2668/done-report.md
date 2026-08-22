## Done report

Root cause: T-1664 (self-audit/gate "unresolved" outcome kind) added a
4th term, "N unresolved,", to frob.check._python._gates_summary's
rendered gate-summary line -- "N errors, M warnings, K unresolved, W
waived" -- but the two regexes in app/ticket_runner/_verify.py that
parse that line for done-report/land captures (_GATE_SUMMARY_COUNTS_RE,
_GATE_SUMMARY_COUNTS_ONLY_RE) were never updated: both required the
literal word "waived" immediately after the warnings count, which the
"K unresolved," term now always sits in front of. Verified directly:
the regex fails to match even a trivial "0 errors, 0 warnings, 0
unresolved, 0 waived" string. This means EVERY real frob check --json
run has produced a gate-summary line this parser cannot read, since
T-1664 landed -- not a rare, contention-only failure. The separate
## Errors identity parse (_parse_error_findings_from_json, reading
diagnostics/severity fields directly) was never affected, which is
exactly the asymmetry T-2503's Done report showed (error-findings
populated, gates: unmeasured recorded next to it).

This is NOT the T-0627/FROB_AGENT spawn-refusal mechanism (T-2076
already fixed that, unconditionally passing FROB_ALLOW_FULL_CHECK=1 in
_shared_check_spawn_fn) -- confirmed by reading that code path, which
already runs to completion under FROB_AGENT. It is a distinct, later
regression: a formatter (_gates_summary) and its consumer regex drifted
out of sync and nothing caught it because every existing test fixture
for this regex was still hand-written in the pre-T-1664 3-term shape,
never against the real renderer's output.

Fix (three parts, all closing the same asymmetry from a different
angle):
  1. Name the unresolved term explicitly in both regexes so they match
     the real, current 4-term shape again -- this alone recovers a
     measured gate-state claim for the overwhelming majority of runs.
  2. Drop the leading anchor on the counts-only regex: it also failed
     to match a summary line under two other real, by-design prefixes
     -- T-2585's replay label ("[REPLAY age=Ns, unchanged tree]  ",
     prepended on every cache-hit gate-summary reprint) and --delta's
     "N/M new  " prefix. Both are common under fleet contention (a
     replay hit is the expected outcome of repeatedly checking an
     unchanged tree), so this was a second live contributor, not just
     theoretical resilience.
  3. When the aggregate gate-summary line still fails to parse (e.g.
     it is missing from results entirely) but the ## Errors identity
     set DID parse, use it rather than discard it:
     _check_gates_summary_fn now returns (real_error_count, None, None)
     instead of None outright, and _land_verify.py's
     _reverify_gate_state_claim tries the identity-based comparison
     FIRST, before the claims.gate_errors is None skip, so a captured
     error_findings set is used even when the count half of the same
     claim is unmeasured. This is the literal "use the findings you
     already have" fix on the land side, mirroring what done-report
     capture already did for error_findings independently of
     gate_errors.

check_gates' Callable return type widens from tuple[int, int, int] to
tuple[int, int | None, int | None] across _reporting.py, _land.py, and
_land_verify.py to carry part 3. DoneReportClaims' fields were already
individually int | None (T-0832), so no schema/render change was
needed there -- the existing "unmeasured" marker vs a real int count
already gives a human-readable third state once gate_errors carries a
real (possibly findings-only) value.

Positive controls:
  - A land whose check produces a real finding: the T-2668 repro test
    (real 4-term gate-summary text plus one real SELFAUDIT001-shaped
    finding) now returns (1, 0, 0) instead of None -- the finding
    reaches the gate-state claim, not just the raw error-findings list.
  - A clean run still returns a real, measured (0, 0, 0), not
    "unmeasured" -- proven by the existing
    test_unparsable_errors_section_falls_back_to_raw_summary_count
    (fixed for the same fixture-shape drift) and by
    test_scoped_run_flaky_rule_excluded_from_error_count.
  - A genuinely unmeasurable run (unparsable JSON, budget-truncated,
    or a failed-and-silent tool) still returns None, unchanged --
    covered by the untouched TestParseErrorFindingsFromJson tests
    (all still green).
  - Land does not refuse on any unmeasured state that was not already
    refusing before this ticket -- the only behavior change on that
    axis is that MORE runs are now measured than before (correctly),
    never that an unmeasured run starts blocking.

Do NOT items honored: no refusal semantics were added; error_findings
is still recorded, not removed, from the Done report or LAND-PROOF's
claims_reverify path.

Filed: none -- both symptoms named in the ticket (T-2503's own gap and
T-2634's near-identical shape) trace to the exact same two regexes.

Time breakdown (rough): ~25 min reading the playbook/ticket and tracing
the call chain (_reporting.py -> _verify.py -> _land_verify.py/_land.py)
to find where check_gates/check_gate_findings actually diverge; ~15 min
confirming and ruling out the T-0627 prior art (already fixed by T-2076)
and the gate-replay-label theory before landing on the T-1664
regex/renderer drift as the real, empirically-confirmed root cause;
~10 min writing and confirming the repro test (FAILED_AT_PARENT); ~35
min implementing the fix across four files plus updating stale 3-term
fixtures in three existing test files that the new regex correctly
stopped accepting; ~15 min running scoped test suites and a --ticket
check to confirm zero new findings; remainder on this report and land.

### Changed
```
 src/frob/app/ticket_runner/_verify.py              | 102 ++++++++++++++++-----
 src/frob/tickets/_land.py                          |   4 +-
 src/frob/tickets/_land_verify.py                   |  66 ++++++++-----
 src/frob/tickets/_reporting.py                     |  17 +++-
 tests/unit/test_ticket_close_gate_claims_t1410.py  |   4 +-
 .../test_ticket_close_own_obligations_t1387.py     |   6 +-
 tests/unit/test_ticket_runner_gate_findings.py     |  57 +++++++++++-
 tickets/T-2668/ticket.md                           |  30 ++++++
 8 files changed, 229 insertions(+), 57 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_gate_findings.py::TestCheckGatesSummaryFn::test_real_gates_summary_shape_with_unresolved_term_is_measured` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 48 error(s), 991 warning(s), 700 waived
- error-findings: AFFECT001@src/frob/tickets/_land.py, AFFECT001@src/frob/tickets/_reporting.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2668, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md, invalid-argument-type@src/frob/tickets/_land.py
