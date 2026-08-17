## Done report

Changed:
- src/frob/gates/_fix_engine_scope.py (new): SkippedFix, filter_fixes_by_scope_and_lease, _other_ticket_holding_live_lease, _revert_fix_file, _REPO_WIDE_EXEMPT_RULES
- src/frob/gates/_fix_engine.py::apply_tier_a_fixes (filters each handler's own return value through filter_fixes_by_scope_and_lease before counting it as applied; logs each skip at WARNING)
- docs/modules/gates.md (new "Scope/lease enforcement on Tier-A output (T-2284)" subsection under the existing Tier-A section, plus two new frob:describes anchors)

Precedence rule (acceptance[1]): a live lease always wins over declared
scope. A file under another ticket's live lease (is_effectively_in_progress)
is skipped even when the landing ticket's OWN scope also covers it. Reason:
a live lease is a real-time, measured fact -- another agent is actively
editing that file right now, in a different worktree, this instant. Declared
scope is a static intention recorded once and can legitimately overlap
between two tickets (T-2225's own worked example: a broad src/frob/** vs a
narrow src/frob/tickets/_land.py) without either being wrong to have written
it that way -- overlapping intentions are harmless until one is actually
acted on, which is exactly what a live lease signals.

Repo-wide handler (acceptance[4]): REL002/fix_rel002_release_sync writes
pyproject.toml/CHANGELOG.md/uv.lock -- files docs/guides/agent-playbook.md
section 4b already forbids any ticket from declaring in its own scope (they
are land-owned). A scope check against them would not catch a genuine leak,
it would revert REL002's own correct, load-bearing output on every land.
Answer: named, disclosed exemption (_REPO_WIDE_EXEMPT_RULES = {"REL002"}),
with the reasoning recorded at the exemption site in code and in
docs/modules/gates.md -- not a silent pass. Also checked (per the
coordinator's explicit ask): frob.gates._fix_engine_tier_b.py's Tier-B
engine (apply_tier_b_fixes) is called ONLY from frob.app.check_runner (the
`frob check --fix` CLI path), never from the land path at all -- it cannot
leak an out-of-scope edit into a land's committed changeset the way Tier-A
could, so it does not share this defect; left untouched.

MUST-STILL-PASS verified with a real case: the SYS111 capability-ratchet
bump handler, run through apply_tier_a_fixes's full dispatch (not the raw
handler) with a real landing ticket whose scope covers the lock file --
still applies and lands in `applied` unchanged
(test_sys111_ratchet_bump_still_applies_through_scope_lease_filter). A
land with ticket_id=None or nothing out of bounds is byte-identical: every
existing Tier-A/TierB test (55 pre-existing + this ticket's own 5 new ones,
56 total) passes unmodified.

Evidence:
- tests/test_gates.py::TestFixEngineScopeLease::test_out_of_scope_fix_is_reverted_and_reported (designated repro, FAILED_AT_PARENT verified against commit c5cde8b31 -- the repro-test-only commit, before the fix commit f2c3290ac)
- tests/test_gates.py::TestFixEngineScopeLease::test_live_leased_file_skipped_even_when_in_landing_scope
- tests/test_gates.py::TestFixEngineScopeLease::test_rel002_is_a_named_repo_wide_exemption_not_a_silent_pass
- tests/test_gates.py::TestFixEngineTierA::test_sys111_ratchet_bump_still_applies_through_scope_lease_filter

Gates: frob check --ticket T-2284 clean for every touched file (0 unwaived
errors); frob test --base main PASS (11 python test(s) recorded stable,
includes tests/test_gates.py's own integration test).

### Changed
```
 docs/modules/gates.md               |  58 ++++++++++
 src/frob/gates/_fix_engine.py       |  27 ++++-
 src/frob/gates/_fix_engine_scope.py | 218 ++++++++++++++++++++++++++++++++++
 tests/test_gates.py                 | 225 ++++++++++++++++++++++++++++++++++++
 tickets/T-2284/ticket.md            |  64 ++++++++--
 5 files changed, 583 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineScopeLease::test_out_of_scope_fix_is_reverted_and_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineScopeLease::test_live_leased_file_skipped_even_when_in_landing_scope` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineScopeLease::test_rel002_is_a_named_repo_wide_exemption_not_a_silent_pass` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_ratchet_bump_still_applies_through_scope_lease_filter` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2284/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2284/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2284/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2284/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2284/tests/test_ticket_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2284, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
