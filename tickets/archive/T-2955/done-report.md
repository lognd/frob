## Done report

Re-measured unscoped (uv run frob check --json --only static, tool==
"frob-dup", filter every fragment starting with "tests/") before
starting work: 479 unaccounted groups (out of 553 repo-wide, 5
waived), matching the parent ticket's ~490 estimate.

This ticket is a triage/decision record, not a code-change ticket --
no production files touched. Disposition: DETECTOR-NARROWING,
recommended and evidenced, not applied here (real detector-design work
belongs in its own ticket, not forced into a triage pass). See the
ticket body's "TRIAGE DECISION" section for the 4 spot-checked groups
(tests/unit/test_arch.py x2, tests/unit/strata/test_litmus_waive.py
vs test_litmus_waive_store.py, tests/test_gates.py, tests/test_dup.py)
and the explicit argument against both blanket exclusion and 479
individual waivers.

Filed: T-2967 (frob-dup: narrow the tests/ renamed-detector threshold
or add a fixture-shape heuristic, with a positive-control check) --
carries the two candidate narrowings, the 4 spot-check samples, and
the positive-control requirement before it can land.

NOT reached zero -- 479 groups remain unaccounted, all deferred to
T-2967's detector-level fix. T-2957 is NOT unblocked by this ticket:
this is the dominant share of the whole family's unaccounted count
(479 of 553 unscoped, 27 of which were T-2956's src/frob/gates
cluster, now down to 23 residue there too).

Evidence: no new/changed code, so per the playbook's docs-only
guidance (sec 5) this cites the existing CLI-dispatch integration
test: tests/integration/test_interfaces.py::TestInterfaces::
test_main_cli_dispatches (1 collected, 0 failed).

Gates: N/A production change; frob check --only static re-run to
produce the re-measured counts above (exit 1 expected, findings
present as before this ticket).

### Changed
```
 tickets/T-2955/ticket.md           | 119 ++++++++++++++++++++++++++++++++++++-
 tickets/T-2970/ticket.md |  77 ++++++++++++++++++++++++
 2 files changed, 194 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 27 error(s), 472 warning(s), 854 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2962/ticket.md, DOC008@docs/commands/check.md, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
