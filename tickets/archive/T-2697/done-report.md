## Done report

Changed:
- tickets/T-2691/ticket.md (prose fix)
- tests/unit/test_ticket_2691_doc006.py (new regression test)

Measurement (per the dispatch instructions, both questions asked
separately before touching anything):

1. Does the finding REPRODUCE on current main? YES. Confirmed directly:
   `frob check` run against this worktree merged onto current main
   (58b41e1ac / 38c7d01c8) still reported
   `gate:DOC:DOC006 tickets/T-2691/ticket.md:50 ... 'frob land status'
   does not resolve`. This is NOT the T-2713 stale-rolling-baseline
   artifact class -- it is a real, live gate finding against the file's
   actual current content.

2. Did the blamed land actually TOUCH the file? YES.
   `git show --stat 8a27d7828` (the commit the sweep blamed, "land
   T-1549 Tier-A auto-fix: ClaimDivergence re-run via done-report
   recap") includes `tickets/T-2691/ticket.md | 58 +++++++` -- that
   commit created T-2691 with the offending prose, backtick-quoting a
   not-yet-implemented future verb ("`frob land status`") that DOC006's
   CLI-invocation-pointer check correctly reads as a real command that
   must resolve today. The symbolic-reachability attribution engine
   reported this specific finding UNATTRIBUTED because ticket-body prose
   is not a tracked SYMBOL its touched-symbol-set reachability analysis
   covers -- a known, separate limitation of that engine, not evidence
   the blame is wrong. File-level `git show --stat` confirms the blame.

Conclusion: this is real work, not T-2713 residue. Fixed by rephrasing
the prose so the future verb is described in plain quoted text ("a
future, not-yet-implemented \"frob land status\" verb") instead of
backticks, so DOC006 no longer parses it as a live CLI invocation. Did
NOT waive the finding -- the rewrite preserves the same meaning while
being the more honest fix (backticks are supposed to mean "this
resolves today").

A new regression test (tests/unit/test_ticket_2691_doc006.py) reproduces
the exact shape via `frob.gates._docptr.doc006_gate` against a synthetic
fixture (mirroring tests/test_docptr_gate.py's own pattern) AND against
the live tickets/T-2691/ticket.md content copied into a throwaway repo,
so the repro is tied to the real file rather than only a synthetic
stand-in. Reuses tests/test_docptr_gate.py's existing _git/_init_repo/
_write/_CLI_CONFIG helpers by import rather than adding a 14th
byte-identical copy (DUP001 fix).

Evidence:
- tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_backticked_future_verb_is_flagged
- tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_prose_description_of_future_verb_not_flagged
- tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_real_ticket_file_not_flagged (designated repro)

BUG002 repro verified via `frob ticket evidence --check-repro`:
test_real_ticket_file_not_flagged FAILED_AT_PARENT at the test-only
commit (30a9ab23f, before the ticket.md rewrite) -- a genuine repro.

Full new test file: 3 passed, 0 failed
(uv run pytest -q tests/unit/test_ticket_2691_doc006.py).

Filed: none

Gates: `frob check --ticket T-2697` clean of new findings against
tickets/T-2691/ticket.md and tests/unit/test_ticket_2691_doc006.py
(DOC006 cleared; DUP001 and DSL001 hit during development, both fixed
before landing). T-2713 (the rolling-baseline root-cause fix) is
unrelated to this specific finding -- it reproduces independently of
that bug, so no cross-reference to T-2713 is warranted here.

### Changed
```
 tests/unit/test_ticket_2691_doc006.py | 92 +++++++++++++++++++++++++++++++++++
 tickets/T-2691/ticket.md              |  5 +-
 tickets/T-2697/ticket.md              | 15 +++++-
 3 files changed, 108 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_backticked_future_verb_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_prose_description_of_future_verb_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_real_ticket_file_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 43 error(s), 865 warning(s), 679 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2703/ticket.md, DOC006@tickets/T-2705/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
