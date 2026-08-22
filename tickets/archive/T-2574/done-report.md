## Done report

M1 of the T-2573 milestone epic: `milestone: str | None = None` on both
`Ticket` and `TicketSpec`, a real semver total order (packaging.version.
Version, already a project dependency), and the CLI surface
(`frob ticket milestone <id> <value>` mirroring `set_runs_last`,
`--milestone` on `frob ticket new`).

Invalid milestone strings are refused at WRITE time via `validate_
milestone` (frob.tickets._models), called from both write sites
(`set_milestone` in _setters.py, `_validate_new_ticket_spec` in
_new_renumber.py) -- never sorted arbitrarily at read time. `Ticket`
itself stays lenient on load (same T-1132 posture as blocked_by/parent),
so extra="allow"/frozen=True is undisturbed and a ledger written by a
newer binary still loads on this one.

The "1.10.0 > 1.9.0" ordering case (the one a lexical string compare
gets wrong) is explicitly tested in TestValidateMilestone.
test_ordering_is_numeric_not_lexical, with a positive-control assertion
that plain string comparison DOES get it wrong ("1.10.0" < "1.9.0" as
strings) immediately before the real Version-based assertion.

CLI wiring required touching files outside the ticket's originally
declared scope -- the argparse tree for `frob ticket new`/`frob ticket
milestone` lives in src/frob/_cli_parsers/_ticket/ (_new.py, _metadata.py,
__init__.py), the argparse-Namespace-to-kwargs copy lives in
src/frob/app/_config_external.py, TicketSpec construction for `new` lives
in src/frob/app/ticket_runner/_new.py, and the set_milestone re-export
lives in src/frob/tickets/__init__.py -- none of which the implicit
T-0446/T-1848 CLI-wiring grant (__main__.py/app/config.py/ticket_runner/
__init__.py) actually covers. Widened via `frob ticket scope --add
--reason` (the sanctioned mechanism, ScopeChangeEntry-audited) rather
than touched silently.

Do NOT scope: doable ordering, runs_last, MILE00x gates, or REL001 are
all left completely untouched, per the ticket's own explicit exclusion.

### Changed
```
 tickets/T-2574/ticket.md | 98 +++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 97 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets.py::TestValidateMilestone::test_valid_semver_accepted` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestValidateMilestone::test_invalid_string_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestValidateMilestone::test_ordering_is_numeric_not_lexical` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestSetMilestone::test_valid_semver_sets_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestSetMilestone::test_invalid_semver_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestNewTicketMilestone::test_new_ticket_with_valid_milestone` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestNewTicketMilestone::test_new_ticket_with_invalid_milestone_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestNewTicketMilestone::test_new_ticket_without_milestone_is_unmilestoned` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC006@tickets/T-2570/ticket.md, DOC007@src/frob/tickets/_models.py, DOC007@src/frob/tickets/_setters.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/tickets/_models.py, DRIFT002@src/frob/tickets/_setters.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2574/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2574/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2574/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2574, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
