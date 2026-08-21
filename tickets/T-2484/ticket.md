---
id: T-2484
title: T-2473's concurrent-check advisory writes to stdout, corrupting frob check
  --json under fleet load
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/__main__.py
evidence_scope:
- tests/unit/test_main_entry.py
- tests/unit/test_check_json_none_handling_t2484.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_writes_to_stderr_not_stdout
- tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_below_four_still_reaches_stderr
- tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_idle_machine_stays_quiet
- tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_dispatch_passes_force_stderr_only_for_json
- tests/unit/test_check_json_none_handling_t2484.py::TestParseCheckJsonReturnsNoneOnCorruption::test_corrupted_json_stdout_is_unparsable
- tests/unit/test_check_json_none_handling_t2484.py::TestBudgetDeferredGroupsFromStdoutOnNone::test_corrupted_stdout_yields_empty_tuple_not_a_false_claim
- tests/unit/test_check_json_none_handling_t2484.py::TestParseErrorFindingsFromStdoutOnCorruption::test_corrupted_json_stdout_is_unmeasured_not_empty
- tests/unit/test_check_json_none_handling_t2484.py::TestMatchingErrorDiagnosticsOnNone::test_none_data_returns_none_not_empty_list
designated_repro_test: null
acceptance:
- text: Given two or more concurrent frob check processes, when frob check --json
    runs, then its stdout parses as JSON with no prefix stripping and scripts/check_summary.py
    succeeds.
  evidence:
  - tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_writes_to_stderr_not_stdout
  - tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_dispatch_passes_force_stderr_only_for_json
- text: Given the same conditions, when the check runs, then the concurrency advisory
    still reaches the operator on stderr, proving the T-2473 feature was not deleted
    to fix the corruption.
  evidence:
  - tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_below_four_still_reaches_stderr
  - tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_dispatch_passes_force_stderr_only_for_json
- text: Given an idle machine, when frob check --json runs, then no advisory is emitted
    on any stream and output is unchanged.
  evidence:
  - tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_idle_machine_stays_quiet
- text: Given each caller of _parse_check_json, when it receives None from a decode
    failure, then it is documented whether that is treated as not-measured or as no-findings,
    and any caller treating it as no-findings is corrected.
  evidence:
  - tests/unit/test_check_json_none_handling_t2484.py::TestParseCheckJsonReturnsNoneOnCorruption::test_corrupted_json_stdout_is_unparsable
  - tests/unit/test_check_json_none_handling_t2484.py::TestBudgetDeferredGroupsFromStdoutOnNone::test_corrupted_stdout_yields_empty_tuple_not_a_false_claim
  - tests/unit/test_check_json_none_handling_t2484.py::TestParseErrorFindingsFromStdoutOnCorruption::test_corrupted_json_stdout_is_unmeasured_not_empty
  - tests/unit/test_check_json_none_handling_t2484.py::TestMatchingErrorDiagnosticsOnNone::test_none_data_returns_none_not_empty_list
threat: null
component: process
anchor: false
anchor_reason: null
land_commit: 1ff6bfde21f374f8d618792603babd8eee47eb18
---
T-2473 (landed minutes ago) added a concurrent-check advisory that
writes to STDOUT, corrupting `frob check --json`'s machine-readable
output.

REPRODUCED directly:

    $ frob check --json > out.json
    $ head -c 200 out.json
    frob check: 1 other check(s) already running on this host -- see
    `scripts/fleet_status.py` for swap/load before dispatching more
    (T-2473, advisory only -- this check is not deferred)
    {
      "path": ".",

    $ python3 scripts/check_summary.py out.json
    json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

Stripping the 183-byte prefix makes it parse cleanly (51 results), so
the payload itself is fine -- the advisory line is simply prepended to
stdout.

WHY THIS IS CRITICAL, AND WHY IT WILL NOT BE CAUGHT BY CASUAL TESTING:
the advisory fires ONLY when another check is already running. On an
idle machine it prints nothing and the JSON is valid. Under fleet load
it corrupts every `--json` invocation. So it passes when tested alone
and breaks exactly when the repo is busy -- which is also when its
output matters most.

KNOWN AFFECTED CONSUMERS:
  - `scripts/check_summary.py` -- the repo's own recommended way to
    measure the error floor, and the tool the `frob-suggest` hook
    actively steers people toward. Currently crashes.
  - `src/frob/app/ticket_runner/_verify.py::_parse_check_json` -- used
    by the LAND path. It returns `None` on a decode failure, and its
    own docstring describes itself as "the sole gate between 'trust
    this as a structured CheckResult' and 'fall back to nothing'".

That second one is why this is critical rather than merely annoying.
**The fixer must determine what each caller does with that `None`.** If
any treats it as "measured, nothing found" rather than "not measured",
then every land running while another check is active has been silently
unverified since T-2473 landed. Note T-1703 exists precisely because
post-land sweeps once reported CLEAN on a dirty tree by exactly this
route -- an unparsed result read as zero. Establish the answer by
reading the callers; do not assume either way, and report it explicitly
even if the answer is reassuring.

FIX (the immediate part is small):
  - Send the advisory to STDERR, not stdout. Diagnostics belong on
    stderr; stdout is the data channel. This is the whole fix for the
    corruption.
  - Then check whether any OTHER human-facing output in `frob check`
    reaches stdout when `--json` is set. The advisory is unlikely to be
    the only one, and a second instance would reintroduce this the next
    time load conditions change.
  - Consider whether `--json` should suppress non-JSON stdout writes
    structurally (a guard at the output boundary) rather than relying on
    every future author remembering the convention. That is the
    difference between fixing this instance and fixing the class.

Do NOT fix this by making consumers strip a prefix or hunt for the
first `{`. That would bless the corruption and make every downstream
parser responsible for it.

POSITIVE CONTROLS:
  - must-now-parse: with 2+ concurrent checks running, `frob check
    --json` output parses as JSON with no prefix stripping, and
    `check_summary.py` succeeds. This is the regression case -- test it
    WITH concurrency, not on an idle machine, or it proves nothing.
  - must-still-advise: the advisory still reaches the operator on
    stderr; the fix must not silently delete the T-2473 feature.
  - must-stay-quiet: an idle machine still produces no advisory at all
    and no added noise.