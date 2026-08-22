---
id: T-2793
title: stale natives make frob check fast-exit in 14s, and the rapid sweep records
  that 2-finding abort as the rolling baseline -- verification reports GREEN having
  run zero gates
state: done
kind: bug
origin: agent
created: '2026-08-21'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/app/ticket_runner/_verify.py
- tests/unit/test_ticket_runner_gate_findings.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: T-2793's root cause (a fast-exit abort produces no gate-summary tool result,
    and _parse_error_findings_from_json has no positive check for that absence) lives
    in _verify.py's shared parser, not in _rapid_sweep.py itself; _rapid_sweep.py
    only consumes the frozenset that parser already decided was measured. Widening
    to the true fix location plus its existing test file rather than duplicating the
    check inside _rapid_sweep.py, which would violate NO DUPLICATION and could not
    see the raw JSON at all (_land_cmd._unscoped_error_findings only returns the parsed
    frozenset).
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: T-2793's root cause (a fast-exit abort produces no gate-summary tool result,
    and _parse_error_findings_from_json has no positive check for that absence) lives
    in _verify.py's shared parser, not in _rapid_sweep.py itself; _rapid_sweep.py
    only consumes the frozenset that parser already decided was measured. Widening
    to the true fix location plus its existing test file rather than duplicating the
    check inside _rapid_sweep.py, which would violate NO DUPLICATION and could not
    see the raw JSON at all (_land_cmd._unscoped_error_findings only returns the parsed
    frozenset).
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: T-2793's fix adds a new completeness check to _verify.py::_parse_error_findings_from_json;
    docs/modules/tickets-landing.md already documents that function's T-1703/T-2456/T-2713
    evolution in a running series of 'how this parser's None contract grew' sections
    -- adding this ticket's section there (not a new doc file) keeps the one true
    home for that contract instead of forking it
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: T-2793's fix adds a new completeness check to _verify.py::_parse_error_findings_from_json;
    docs/modules/tickets-landing.md already documents that function's T-1703/T-2456/T-2713
    evolution in a running series of 'how this parser's None contract grew' sections
    -- adding this ticket's section there (not a new doc file) keeps the one true
    home for that contract instead of forking it
  actor: logan
  at: '2026-08-21'
evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_native_staleness_abort_yields_none_not_the_abort_findings
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_other_pre_gate_abort_also_yields_none_not_only_native001
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_ty_and_gate_error_both_appear_in_parsed_set
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_budget_truncated_run_yields_none_not_a_partial_set
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_resume_narrowed_run_yields_none_not_a_partial_set
designated_repro_test: tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_native_staleness_abort_yields_none_not_the_abort_findings
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 34537a21dda9724d46050b991c86711c2e812d29
---
## Measured, live on main right now

`.frob/rapid-sweep-baseline.json` currently holds exactly TWO findings:

    ['CLAUDE001', '.claude/hooks/sync-claude-config.py']
    ['NATIVE001', '.']

Those are not a real finding set. They are the two findings a `frob check`
emits when it FAST-EXITS on stale native extensions before running any gate.

Reproduced directly on the shared root, 2026-08-21:

    frob check --json   ->  rc=1, 14 seconds, 3152 bytes

A genuine unbudgeted check on this repo takes ~274s (measured today in
T-2782). Inspecting that JSON:

    top-level keys: ['path', 'results']
    result entries: 2
    gate-summary present: False
    budget key: None

No `gate-summary`, no `budget` block, two result entries. The gates never
executed. The run measured nothing.

Meanwhile `frob verify status` reports watermark age 63s, unverified depth
0, quarantine clear -- i.e. verification believes it is healthy and current.

## Why this is critical

This is the SAME false-green class T-2713/T-2715 closed, reintroduced by a
different route.

T-2713 made the sweep refuse to advance or record a baseline on an
UNMEASURABLE run, by reading `data["budget"]["skipped_groups"]` -- a signal
that exists only on the BUDGET path (`src/frob/app/_check_chunking.py`).
A native-staleness fast-exit is a different kind of truncation: it produces
no `budget` key at all, so a guard that inspects `budget.skipped_groups`
cannot fire. The run is not budget-truncated; it is aborted.

`src/frob/app/ticket_runner/_rapid_sweep.py:36` states the baseline "is
rewritten to the freshly measured set on EVERY sweep". So an aborted run's
2 findings become the rolling baseline unconditionally.

Three consequences, all live:

1. VERIFICATION REPORTS GREEN WHILE MEASURING NOTHING. The watermark
   advances across commits no gate ever examined. Every land verified in
   this state is unverified in fact.
2. THE NEXT SWEEP'S DIFF IS FICTION. Diffing a real finding set against a
   2-entry baseline makes essentially the whole floor look "new from this
   land". That is exactly the mechanism behind the T-2381/T-2474/T-2525/
   T-2560 false-regression tickets (155 identities, 2 genuine) which were
   all dropped as false positives.
3. THE ERROR FLOOR IS CURRENTLY UNKNOWN, not zero. I could not measure it
   because the check will not run to completion on this tree.

## Root cause to fix

The sweep must treat "the gates did not run" as UNMEASURABLE, exactly as it
now treats a budget-truncated run -- and refuse to record a baseline or
advance the watermark.

The durable fix is a POSITIVE completeness signal rather than enumerating
failure modes. `_check_chunking.py:543` already documents `complete` as "a
positive `skipped_groups == []` flag so a consumer never has to infer
completeness from an absence". Apply that same principle here: a check
result should assert that it RAN, and every consumer should require that
assertion. Absence of a `gate-summary` must never read as "gates ran and
found nothing".

Enumerating aborts one at a time (budget, natives, next quarter's new one)
is how this bug came back. Fix the shape, not the instance.

## Positive controls, both directions

- A check that fast-exits on NATIVE001 must be recorded as UNMEASURABLE:
  no baseline write, no watermark advance, and a LOUD report saying the
  run did not measure. Plant it by deliberately staling the natives.
- A check that fast-exits for any OTHER pre-gate reason must behave the
  same way -- assert on the positive "gates ran" signal, not on NATIVE001
  specifically.
- A genuine complete run must STILL record its baseline and advance the
  watermark exactly as today. Without this control the fix is
  indistinguishable from disabling verification entirely.
- A budget-truncated run must still be caught (T-2713 must not regress).

## Immediate operational note

The root's natives are stale, so `frob check` currently cannot complete
there at all. That is both the trigger for this bug and a separate
availability problem: `frob check` in the shared root is presently useless
until the natives are rebuilt. Rebuilding is the mitigation; it is NOT the
fix, because the next stale-native window silently reopens the same hole.

Related: [[T-2713]], [[T-2715]] closed the budget variant. T-2036 normalized
identities. This ticket is the abort variant.