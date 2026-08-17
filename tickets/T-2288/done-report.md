## Done report

<!-- frob:waive BUG002 reason="T-2288 is a recovery/reconciliation ticket, not a code defect -- the finding is that three branches' work either already reached main under a DIFFERENT ticket's own land commit (legs 1-2) or was legitimately superseded by different already-landed work (leg 3); there is no code path to write a fail-at-parent/pass-at-fix repro against, per playbook 5's docs-only-ticket precedent" -->

All three legs investigated by direct git plumbing (ancestry + content
diff), per playbook measurement discipline -- never assumed from `frob
ticket reconcile`'s own directive-anchored report, which this ticket's own
MISATTRIBUTION NOTE already flagged as pointing at the wrong id.

Leg 1 (T-2097, branch `t-2097`): ALREADY LANDED, not stranded.
`git merge-base --is-ancestor b6cf2c234 main` is true; `git show --stat
b6cf2c234` shows the real land commit "fix(tickets): land T-2097 ..."
touching tests/unit/test_app_runners.py and tests/unit/test_check_budget.py
-- exactly the branch's own fix content. Confirmed the actual test bodies
on main use `caplog`, not `capsys` (T-2097's own fix), and both are bound
to T-2097 by a `# frob:ticket T-2097` directive. The `t-2097` branch's own
work already reached main under its own commit; the branch itself is
stale residue from the same land, not evidence of a leak. DROPPED as
already-resolved, no action needed.

Leg 2 (T-1479, branch `t1539-series`): ALREADY LANDED, not stranded.
`git merge-base --is-ancestor 5b03f2668 main` is true; `git show --stat`
shows src/frob/app/map_runner.py, src/frob/serve/_socketd.py,
src/frob/serve/_tools.py, tests/test_app_daemon_proxy.py all touched.
Confirmed `_try_map_via_daemon` (the `frob map --json` daemon-proxy
wiring the ticket describes) is present in map_runner.py on main, bound
by a `# frob:ticket T-1479` directive. DROPPED as already-resolved.

Leg 3 (T-1238 explore slice, commit 532799aca): the COMMIT is genuinely
not an ancestor of main (confirmed), but its WORK is superseded, not
missing. `frob explore --help` on main already lists map/outline/xref/
docs-search -- landed under a DIFFERENT ticket, T-1271 (commit
bb7f37766, "fix(tickets): land T-1271 cli hygiene..."), which touched
src/frob/_cli_parsers/_explore.py, src/frob/app/explore_runner.py,
docs/design/cli-regrouping.md -- the same deliverable T-1238's own Done
report describes, just landed under T-1271's id instead of T-1238's.
T-1238's acceptance[0] (help-surface rework) was separately deferred to
five child tickets (T-1567 quality, T-1568 design, T-1569 ops, T-1570
naming, T-1571 help-surface) -- all five read `state: done` on main
today. So T-1238's real work is complete; only its OWN ticket-ledger
`state:` field (still `queued`) is stale, a bookkeeping gap left when its
close-attempt branch was superseded before ever landing. Per this
ticket's own constraint ("do NOT force it -- record that finding and
drop that leg"), 532799aca is DROPPED as superseded; the stale ledger
state is filed as a narrowly-scoped follow-up (T-1238's own broad
epic-tier scope makes a same-session close risky under current fleet
contention) rather than force-closed here.

Filed: T-2318 (T-1238 epic ledger state is stale) -- scope
`tickets/T-1238/**` only, ledger-only fix, safe to dispatch independently
of T-1238's own broad declared scope.

No code was landed under T-2288 -- all recovery was verification-only;
the three branches' actual work either already reached main (legs 1-2)
or was legitimately superseded by different, already-landed work (leg
3). `frob ticket reconcile`'s misattribution (naming T-1238 for all
three) is exactly what T-2287 already tracks.

### Changed
```
 tickets/T-2288/done-report.md | 69 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2288/ticket.md      | 28 ++++++++++++++----
 2 files changed, 91 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md
