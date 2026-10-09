+++
id = "01M3DG64ECQN5RFA286F6YXYRZ"
title = "frob check --ticket: refuse a second concurrent full check for the same worktree (per-worktree lock), --allow-concurrent to override, so stacked agent checks cannot starve the shared host"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-10-09T20:42:59Z"
aliases = ["T-6604"]
labels = ["v1-cluster:C1b", "triage:accepted"]
scope = ["src/frob/app/check_runner.py", "src/frob/process/", "src/frob/_cli_parsers/_check.py", "docs/modules/check.md", "docs/design/rules.md"]
+++

Measured twice on 2026-09-26 (14:00 and 23:05 local): implementer agents
in crunk worktrees stacked two to four concurrent `frob check --ticket`
processes per worktree (17 frob check processes host-wide, load average
46-79), and frob's single-threaded land drain produced no output for
four hours until the load fell. Briefing agents to run one check at a
time worked only until the next dispatch; the crunk coordinator asked
for a frob-side guard.

Owner directive (systematize friction: a repeated friction becomes a
refusal with one override flag; tiered safety: guaranteed-safe runs
automatically). Deliver: (1) `frob check --ticket <id>` (and any full,
unscoped `frob check`) takes a per-worktree lock under .frob/ keyed by
the resolved root; a second invocation while the first is alive refuses
within one second naming the holder pid, its start time and its argv,
exit code distinct from a gate failure; a dead holder's lock is
reclaimed automatically (pid liveness, same probe TICK015 uses); (2)
`--allow-concurrent` overrides for a genuinely intended parallel run and
is recorded in the run log; scoped `--files`/`--only lint` runs are not
locked; (3) `frob coord status` (T-5784) lists live full checks per
worktree so a coordinator sees stacking at a glance; (4) docs/modules/
check.md documents the lock and the override tier. Positive control: a
test that holds the lock with a fake live pid and asserts the second run
refuses naming that pid, and that a stale lock from a dead pid is
reclaimed and the run proceeds.
