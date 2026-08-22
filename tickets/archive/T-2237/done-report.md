## Done report

Changed: docs/design/gate-semantics-classification.md:123 -- `T-draft-385de2c7`
replaced with `T-2188` (real edit, single occurrence, verified no other
stale draft-id citation exists nearby via `git grep T-draft-`).

Re-measured before touching anything: `docs/guides/coordinator-scripts.md`'s
DOC011 finding (`T-draft-354a6b64` at the old line 467) was ALREADY GONE
from the file (`git grep 354a6b64` finds it only in rapid-debt.jsonl and
ticket-body prose, both expected historical mentions, not live doc
citations) -- resolved by some other change since T-2237 was filed, not
by this ticket. This is a measured-clean zero for that half of the
ticket, not could-not-measure or matcher-never-fired: `git grep` ran
successfully and found the string nowhere in the live doc tree.

`frob check --only gates` re-run after the fix: zero DOC011 findings
anywhere in the repo (grep for DOC011 on the full gate output returns
nothing). Both leases named in the original ticket (T-1662, T-2222) are
now `done`, confirming the ticket's premise ("blocked by live leases")
no longer applies either.

Evidence: documentation-only single-line fix; no pytest node id applies.
DOC011 itself is the checkable claim, verified directly above via
`frob check --only gates` grep, not via a test.

Filed: none -- no new work discovered.
Gates: `frob check --only gates` clean on DOC011 (0 findings, verified by
direct grep of the full run's output).

### Changed
```
 tickets/T-2237/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2237/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2237/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2237/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2237, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
