---
id: T-1596
title: Residual xdist-order pollution (2nd wave) + full-suite runs truncating before
  the summary line
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tests/**
- src/frob/lang/**
- src/frob/tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_prints_greppable_line_at_any_verbosity
- tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_skips_on_xdist_worker
designated_repro_test: null
threat: null
component: null
---
T-1591 fixed the confirmed, root-caused pollution source (frob.lang's
persistent parse-artifact-cache env var leaking across tests in the same
xdist worker -- see T-1591's Done report) plus several deterministic
(non-pollution) bugs found along the way. Two classes of suite-red items
remain UNRESOLVED after that work and need a fresh investigation:

1. From T-1591's ORIGINAL confirmed-member list, still red under a full
   `pytest tests/ -n auto --dist=loadgroup` run but PASS in isolation and
   in every smaller combination tried:
   - tests/unit/test_app_runners.py::TestMapRunner (both tests)
   - tests/unit/test_app_runners.py::TestOutlineRunner::test_directory_target_falls_back_to_map
     (caplog.records is empty when INFO logging is expected -- looks like
     a logger-level or propagate=False leak from an unidentified earlier
     test, but tests/unit/test_app_runners.py alone and combined with
     tests/unit/test_main_entry.py both pass)
   - tests/test_lang.py::TestParseCache::test_second_call_same_content_is_a_hit
     (hits/misses counter assertion off by one -- possibly a second,
     still-undiscovered process-lifetime cache/counter beyond the
     artifact-cache env var already fixed)
   - tests/test_ticket_land.py::TestClaimDivergencePostMerge -- passed in
     every isolated/combined repro attempt, never reproduced the failure
     directly; only ever observed in a full-suite run's short summary.

2. NEWLY OBSERVED under a full run with `-n 4` (different worker count/
   grouping than `-n auto`) -- not in the original T-1591 list, each
   passes cleanly in isolation and combined with the other three, so
   these are genuinely worker-assignment-sensitive, not something a
   smaller repro caught:
   - tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_captured_from_real_callables
   - tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice
   - tests/test_ticket_reverify.py::TestReverifyCli::test_surfaces_now_failing_evidence_loudly
   - tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_new_file_under_broad_lease_is_exempt

Also worth investigating as its own thing: three separate full,
unscoped `pytest tests/` background runs during T-1591's investigation
(two at -n auto, one at -n 4) each terminated WITHOUT printing pytest's
own final "N passed, M failed in Ts" summary line -- the run stops right
after the "short test summary info" FAILED list with no crash traceback,
no INTERNALERROR, no visible OOM message in the captured log. This
repo's own memory notes an earlier WSL OOM session-kill history
(cap agents at 3-4, .wslconfig); this may be the same class of issue
recurring specifically for a genuinely full, all-tests run, independent
of concurrent agent count -- worth a dedicated investigation with
`/usr/bin/time -v` or dmesg correlation before trusting ANY future
"clean full suite" claim in this repo without independently confirming
the trailing summary line is actually present in the captured log.