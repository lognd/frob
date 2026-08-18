## Done report

Added the empty-scope hard gate at `frob ticket start` plus the declared-
no-scope escape hatch (T-2394).

Implementation: `no_scope_declared`/`no_scope_declared_reason` fields on
`Ticket` and `TicketSpec` (src/frob/tickets/_models.py),
`set_no_scope_declared` (src/frob/tickets/_setters.py),
`_refuse_empty_scope_on_start` wired into `_start`
(src/frob/app/ticket_runner/_lifecycle.py) -- the hard, unconditional
refusal at the point a lease is actually needed, mirroring
`_refuse_over_broad_scope_on_start`'s T-1866 placement for the opposite
problem. `_warn_empty_scope_on_new` (src/frob/tickets/_new_renumber.py)
adds the filing-time WARN (never a refusal there, same T-2123 posture).
CLI: `frob ticket scope <id> --declare-no-scope --reason TEXT`
(src/frob/_cli_parsers/_ticket/_metadata.py,
src/frob/app/ticket_runner/_mutate.py). Wired end-to-end through
src/frob/app/config.py and src/frob/app/_config_external.py (no
pre-existing lease blocked this file this time) -- confirmed via a real
argv-through-the-real-parser test
(TestScopeCliDeclareNoScope::test_flag_survives_real_argv_parsing) and
the existing find_dropped_cli_flags static check.

Blast radius from the new hard refusal, measured with `frob test --base
main` (touched-set): 3 pre-existing unrelated failures (confirmed
byte-identical against main -- a removed bulk-renumber CLI verb and a
fake `deadbeef` sha never being an ancestor of main, neither touching
scope) plus 5 genuine regressions, all confined to
tests/unit/test_app_runners_batch7.py (already this ticket's own scope):
fixtures that created a ticket with an empty scope for reasons unrelated
to scope itself (testing requeue/close/archive/land dispatch). Fixed by
giving each a real one-file scope; re-ran the touched set clean
afterward. Also found and filed T-draft-b08172a8 (out of scope: the
related-title duplicate detector false-positiving "holder"/"collider" at
71%, breaking a pre-existing TestTicketStart test unrelated to T-2394).

BUG002: repro test committed alone first (ef41d2680), confirmed
FAILED_AT_PARENT, fix committed on top, --designate-repro validated
against ef41d2680 as base-ref.

### Changed
```
 docs/modules/tickets-lifecycle.md          |  36 +++++
 src/frob/_cli_parsers/_ticket/_metadata.py |  10 ++
 src/frob/app/_config_external.py           |   2 +
 src/frob/app/config.py                     |   5 +
 src/frob/app/ticket_runner/_lifecycle.py   |  47 ++++++
 src/frob/app/ticket_runner/_mutate.py      |  19 ++-
 src/frob/tickets/__init__.py               |   2 +
 src/frob/tickets/_models.py                |  37 +++++
 src/frob/tickets/_new_renumber.py          |  41 ++++++
 src/frob/tickets/_setters.py               |  49 +++++++
 tests/test_tickets_no_scope.py             | 225 +++++++++++++++++++++++++++++
 tests/unit/test_app_runners_batch7.py      |   7 +
 tickets/T-2394/ticket.md                   | 115 ++++++++++++++-
 tickets/T-draft-b08172a8/ticket.md         |  46 ++++++
 14 files changed, 636 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_tickets_no_scope.py::TestSetNoScopeDeclared::test_sets_both_fields` (pytest node id, verified passing when recorded)
- `tests/test_tickets_no_scope.py::TestSetNoScopeDeclared::test_reason_missing_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_empty_scope_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_declared_no_scope_starts_cleanly` (pytest node id, verified passing when recorded)
- `tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_nonempty_scope_starts_cleanly` (pytest node id, verified passing when recorded)
- `tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_full_start_cli_refuses_on_empty_undeclared_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets_no_scope.py::TestRefuseEmptyScopeOnStart::test_full_start_cli_succeeds_once_declared` (pytest node id, verified passing when recorded)
- `tests/test_tickets_no_scope.py::TestWarnEmptyScopeOnNew::test_empty_scope_warns_at_filing_time` (pytest node id, verified passing when recorded)
- `tests/test_tickets_no_scope.py::TestWarnEmptyScopeOnNew::test_declared_no_scope_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_tickets_no_scope.py::TestWarnEmptyScopeOnNew::test_nonempty_scope_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_tickets_no_scope.py::TestScopeCliDeclareNoScope::test_flag_survives_real_argv_parsing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/tickets/_new_renumber.py, E501@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2394, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
## Merge resolution note (added post-Done-report, pre-land)

Merging main required resolving a real content conflict in
`_lifecycle.py::_start`: T-2446's `_apply_scope_breadth_ack_on_start`
(setter, must run first) collided at the same insertion point with this
ticket's `_refuse_empty_scope_on_start` (refusal, different condition).
Resolved per coordinator content decision: keep both calls, breadth-ack
first, then the over-broad and empty-scope refusals in sequence.

Verified explicitly, not assumed: `_refuse_empty_scope_on_start` reads
`ticket.scope`/`ticket.no_scope_declared` directly and never consults
`scope_breadth_ack` -- the ack cannot short-circuit past it regardless
of call ordering. Pinned with a new test,
`TestRefuseEmptyScopeOnStart::test_scope_breadth_ack_does_not_satisfy_empty_scope_refusal`:
a ticket with an EMPTY scope PLUS a breadth ack is still refused at
start through the real `_start` dispatch function. 13/13 tests in
tests/test_tickets_no_scope.py pass (12 pre-existing + this one).

tickets/T-2390/ticket.md's conflict was the same children list under
two naming states (this branch's stale draft-id references vs main's
current real ids for the identical entries) -- resolved by taking
main's side entirely. The draft-rename conflicts
(T-2412/T-2413/T-draft-03cf93c1) were this branch's own byproduct of
the shared renumbering allocator racing concurrent T-2390
epic-decomposition lands; resolved by taking main's disposition. One
mechanical slip along the way: an initial `git checkout --theirs` on
tickets/T-2436/ticket.md left stray conflict markers mixed with the
WRONG source ticket's content (T-2412's) -- caught by validating every
one of the 559 ticket.md files' YAML frontmatter parses cleanly before
committing, fixed by replacing the file with main's real blob directly.
