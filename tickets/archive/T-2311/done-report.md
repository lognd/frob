## Done report

Investigated the 10 DOC006 findings this ticket's body listed as
remaining in the docs/modules/tickets-*.md family
(tickets-data-storage.md:189,927; tickets-landing.md:173,527,1460,1466,
1603; tickets-lifecycle.md:435,450; tickets-verify-sweep.md:524).

Result: NOT REPRODUCIBLE against the current tree. Ran `frob check
--ticket T-2311 --only docblocks --only prework` (gate:docblocks is the
family DOC006 lives under, and is repo-wide/unscoped even under
`--ticket`, per the run's own scope-note) -- 0 DOC006 findings anywhere
in the docs/modules/tickets-*.md family. The only DOC006 error the run
produced is unrelated to this ticket: a bad symbol citation
(`frob.app._check_chunking._run_gate_chunks_stamping_progress`, which
does not exist -- the real name is `_run_baseline_chunks`) in
tickets/T-2684/ticket.md, my own follow-up ticket filed while
investigating T-2134 earlier in this same series. That file is outside
this ticket's declared scope (docs/modules/tickets-*.md only) and outside
T-2311's own charter, so left unfixed here and disclosed rather than
silently patched -- flagged in this series' final report for the
coordinator/T-2684's own eventual worker to correct.

Spot-checked the two findings T-2311's own body flagged as likely
already fixed and confirmed both ARE: `docs/modules/tickets-landing.md`'s
`frob sys sync-interface` mention already carries a `frob:waive DOC006`
(historical-context waiver, matching the pattern
docs/guides/agent-playbook.md and docs/modules/strata.md already use),
and `docs/modules/tickets-verify-sweep.md`'s `frob graph select-batch-
tests` mention already carries its own `frob:waive DOC006` (not-yet-
registered-subparser waiver). Read all 10 originally-cited line numbers
directly (`sed -n` around each) -- none of the surrounding prose still
carries an unresolved bare pointer; whatever fixed them (most likely
T-2135's own broader pass, per this ticket's own body noting "several
findings are the same shape T-2135 already fixed elsewhere") landed
before this ticket was picked up.

No code/doc change made -- there is nothing left to fix in this family
as of this investigation. Re-open (or file fresh) if `frob check --only
docblocks` shows a live DOC006 against any docs/modules/tickets-*.md
file again; attach the fresh command output, since this write-up could
not reproduce one.

Changed: none (investigation-only; symptom no longer reproduces)
Evidence: tests/test_docptr_gate.py::TestDoc006Symbol::test_real_symbol_passes, tests/test_docptr_gate.py::TestDoc006DocAnchor::test_real_anchor_passes
Filed: none (the one adjacent defect found -- T-2684's own bad symbol
citation -- is pre-existing residue from this series' own earlier
ticket, not new work; disclosed above rather than filed separately)

### Changed
```
 rapid-debt.jsonl              |  1 +
 tickets/T-2128/done-report.md | 73 ++++++++++++++++++++++++++++++++++
 tickets/T-2128/ticket.md      | 28 +++++++++++--
 tickets/T-2134/done-report.md | 63 +++++++++++++++++++++++++++++
 tickets/T-2134/ticket.md      | 26 +++++++++++-
 tickets/T-2311/ticket.md      |  7 +++-
 tickets/T-2684/ticket.md      | 92 +++++++++++++++++++++++++++++++++++++++++++
 7 files changed, 284 insertions(+), 6 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 38 error(s), 1076 warning(s), 697 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2684/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
