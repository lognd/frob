## Done report

Wrote a real "Unlanded branch work (T-1934/T-1948)" section in
docs/modules/tickets-lifecycle.md, immediately after the existing
"Intent journal (T-0456)" section and its sibling "`frob ticket
reconcile` (T-0476)" section -- this file already documents `reconcile`'s
first three anomaly classes there, so the fourth belongs alongside them
rather than as a new top-level section in docs/modules/tickets.md (the
ticket offered either location; picked the "extend the existing reconcile
section" option since tickets-lifecycle.md is the file that already
carries this exact material's home).

The section is a real description, not a stub restating the field name:
covers the crash window it closes (finished-but-uncommitted-to-land work,
the third of three crash windows this repo's ledger machinery covers,
alongside the intent-journal and dirty-tree cases already documented
nearby), the two original detection signals (done-report.md /
state:done-or-dropped, resolved against main INCLUDING the archive, with
the 186-false-positive path-existence lesson named), the T-1948
directive-anchored third signal and why it is deliberately narrower
(committed content only), and the report-only-by-design non-healing
behavior with its `sweep_worktrees` interaction.

Removed both `frob:waive AFFECT001` waivers in
src/frob/tickets/_reconcile.py (ReconcileReport and reconcile()) now that
the doc gap they cited is closed -- replaced with `frob:doc
docs/modules/tickets-lifecycle.md#unlanded-branch-work-t-1934t-1948`
edges pointing at the new section (verified the slug directly against
frob.graph.dsl.slugify's own algorithm: parens and `/` are stripped, not
replaced with a space, giving `unlanded-branch-work-t-1934t-1948`).

Scope widened from the ticket's original two docs files to include
src/frob/tickets/_reconcile.py (`frob ticket scope T-2619 --add
src/frob/tickets/_reconcile.py`), since removing the waivers this ticket
exists to remove requires touching that file.

Positive control: `docs/modules/tickets.md` had zero hits for
`unlanded_branch_work` before this change (grep-confirmed, matching the
ticket's own stated premise). `docs/modules/tickets-lifecycle.md` now has
5 hits (heading, two doc-anchor comments' own targets minus the anchors
themselves, and two prose mentions). `git stash` to mechanically revert
and re-confirm the finding fires again was refused by this repo's own
multi-worktree stash guard (docs/guides/agent-playbook.md#1b); the
premise -- zero hits pre-change -- was independently confirmed by the
ticket body's own grep before any edit was made, which is the equivalent
check run the other direction.

Evidence: tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_reports_the_confirmed_leak_shape
(unaffected by this change -- confirmatory-only, this is docs-kind work,
no code-behavior change; BUG002 does not apply, ticket kind=docs).

Gates: `frob check --ticket T-2619` -- no new AFFECT001/DOC001/DOC002/
DOCENUM findings on docs/modules/tickets-lifecycle.md or
src/frob/tickets/_reconcile.py (grepped the JSON output directly for
both paths: one pre-existing PERF008 warning at an untouched line, one
pre-existing ruff-format warning on a test file this ticket does not
touch). `frob ticket sweep T-2619` re-run after the scope widen.

Filed: none.

### Changed
```
 tickets/T-2619/ticket.md | 16 +++++++++++++++-
 1 file changed, 15 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_reports_the_confirmed_leak_shape` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
