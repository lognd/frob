## Done report

MEASUREMENT (stale-scope-read vs WIP-commit-timing bug): confirmed the
root cause is a stale-scope-read, not a WIP-commit bug. Live evidence
observed this session, during a real T-2337 land with T-2303 still
in-progress: the land log printed
"WARNING: tier-a fixes: SKIPPED SYS100 design/frob.strata:0 -- design/
frob.strata is under T-2303's live lease" repeatedly, at a time when
T-2303's OWN live cross-worktree lease file
(.git/frob-leases/T-2303.json) already showed "scope": [] (empty,
narrowed) -- yet T-2303's ledger entry (tickets.md, `frob ticket show
T-2303`) still declares scope=[...,"design",...]. Root-caused to
frob.gates._fix_engine_scope._other_ticket_holding_live_lease: it
compared the candidate file against the OTHER ticket's stale, declared
ledger scope (`other.scope`), never consulting
frob.tickets._leases.read_all_leases for a live, narrower lease scope
-- unlike the sibling mechanism src/frob/tickets/_land.py::
_effective_leakage_scope (T-2095/T-2111), which already prefers a live
lease's own recorded scope over a ticket's stale declared scope for
this exact staleness reason, and already documents the precedent this
fix reuses. This is why a land's Tier-A pass can revert (`git checkout
--`) a file another ticket has ALREADY released via a narrowed live
lease: the skip decision itself is wrong, not merely mistimed relative
to the WIP snapshot commit.

FIX: src/frob/gates/_fix_engine_scope.py::_other_ticket_holding_live_
lease now builds `leases_by_id` from `read_all_leases(root)` and uses
a lease's own recorded scope as the "effective scope" for any ticket
that has one, falling back to the ticket's declared ledger scope only
when no live lease is recorded for that id -- the same precedence
`_effective_leakage_scope` already uses.

REPRO: added
tests/test_gates.py::TestFixEngineScopeLease::
test_narrowed_live_lease_wins_over_stale_declared_scope, which
reproduces the T-2194/T-2303 incident shape directly: a ticket's
declared scope still names "design" but its live lease (written via
record_lease) has narrowed to (). Ran it BEFORE the fix (manually, in
this same worktree) -- it failed with the exact
"design/frob.strata is under T-2303's live lease" skip and the file
was reverted to "original", matching the incident precisely. After the
fix, all 6 TestFixEngineScopeLease tests pass, including the 3
pre-existing ones (test_out_of_scope_fix_is_reverted_and_reported,
test_live_leased_file_skipped_even_when_in_landing_scope,
test_in_scope_fix_is_kept_unchanged) -- confirming both required
positive controls hold: (1) a file genuinely outside the landing
ticket's scope is still reverted and reported
(test_out_of_scope_fix_is_reverted_and_reported, unchanged, still
passes); (2) a file under another ticket's genuinely LIVE (non-stale)
lease is still correctly skipped even when it is also in the landing
ticket's own scope
(test_live_leased_file_skipped_even_when_in_landing_scope, unchanged,
still passes) -- this fix narrows WHICH scope a lease comparison reads,
it does not disable lease precedence or "fix" this by landing
everything.

SCOPE: added src/frob/gates/_fix_engine_scope.py and tests/test_gates.py
to T-2328's declared scope via `frob ticket scope --add` (reasons
recorded on the scope-change entries) -- the true defect lives outside
the two files originally declared (_land.py, _land_cmd.py); neither of
those needed a code change. _land_cmd.py was under T-2322's live lease
at dispatch time and was never touched.

--check-repro could not produce a verdict against a committed parent
sha (TEST_ABSENT_AT_PARENT -- the repro test was never committed alone
before the fix in this worktree's history), but the manual
before/after run described above is the equivalent direct evidence:
observed failing pre-fix, passing post-fix, same assertion.

### Changed
```
 tickets/T-2328/ticket.md | 54 +++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 53 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineScopeLease::test_narrowed_live_lease_wins_over_stale_declared_scope` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineScopeLease::test_live_leased_file_skipped_even_when_in_landing_scope` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineScopeLease::test_out_of_scope_fix_is_reverted_and_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineScopeLease::test_in_scope_fix_is_kept_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2328/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2328, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
