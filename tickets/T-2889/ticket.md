---
id: T-2889
title: frob ticket work should refuse (not auto-merge) a worktree far behind main
  -- one of 3 silent-stale-code mechanisms this session
state: queued
kind: feature
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

`frob ticket work` currently has no defense against starting/continuing
work in a worktree whose branch is far behind main. T-2886's audit
measured 30 of 39 fleet worktrees lacking T-2849's forkserver-leak fix
in their own checked-out src/frob/process/_reap.py -- any agent running
frob check from one of those 30 silently re-introduces the exact leak
T-2849 fixed, because each worktree has its OWN editable install
pointing at its OWN src/, not main's.

This is one instance of a THREE-INSTANCE family measured this session,
all with the same consequence -- a landed fix silently not in effect
for some caller:

1. Stale worktrees (this ticket's origin): a worktree's own src/ is
   frozen at whatever commit it last merged main at; every land after
   that point is invisible to code running from that worktree.
2. The bare `frob` on PATH: measured tonight to be running a stale
   build whose own reported version string (0.530.0) matches the dev
   checkout's version, so version parity masked the staleness -- an
   agent trusting `frob --version` agreement between the two builds
   would wrongly conclude they run the same code.
3. T-2884's content-blind daemon version-skew check: the daemon
   self-heal compares version STRINGS, not source content, so a
   source-only change with no version bump is invisible to the skew
   check -- the daemon can keep serving pre-fix code indefinitely
   without ever detecting it should restart.

## Plan (this ticket: the worktree-staleness instance only)

Recommendation from T-2886's audit, to be implemented here: `frob
ticket work` should REFUSE (not silently auto-merge) when a worktree's
branch is more than N commits behind main, and surface the fix as an
explicit suggested command (`git -C <wt> merge main`, followed by the
existing `git diff main -- tickets.md` verification step already
documented in the agent playbook).

Auto-merging on every `ticket work` invocation is the WRONG shape: it
risks the exact collision class T-1868/T-1093 already documented (a
silent merge near ticket-ledger reporting can resurrect a dropped draft
or drop a just-landed sibling's evidence/Done-report). The playbook's
existing "merge main is fine at warm-up, corrupting near reporting"
doctrine argues for refuse-and-suggest over auto-merge: put the merge
decision (and its own verification step) in the agent's hands, at a
point they are prepared to verify it, rather than folding it silently
into a command whose job is "start work."

Concretely:
- Add a commits-behind-main threshold check to `frob ticket work`
  (reuse whatever `fleet_status.py`/staleness-age logic already exists
  rather than re-deriving it).
- On breach, refuse with a message naming the exact `git -C <wt> merge
  main` command and the post-merge `git diff main -- tickets.md`
  verification step from the playbook.
- Do NOT auto-merge. Do NOT build this as a blanket age-based check
  only -- commits-behind is the direct measure of code staleness,
  age is a proxy that can be wrong for a worktree with few commits
  merged but touched recently.
- Mention the frob/daemon/worktree three-instance family (above) in
  the docs describing this check, so a future reader recognizes the
  pattern rather than treating each instance as unrelated.

## Failure log

(none yet)
- 2026-08-22 attempt 1: COORDINATOR MEASUREMENT, confirming instance 2 of this family with hard evidence. The globally-installed uv tool at /home/logan/.local/share/uv/tools/frob/ was installed 2026-08-22 04:34:58. T-2849 landed at 04:45:16 -- ELEVEN MINUTES LATER. Verified directly: the global copy's site-packages/frob/process/_reap.py does NOT contain arm_parent_death_signal, i.e. it lacks the forkserver-leak fix. Both the global tool and the dev checkout report 'frob 0.530.0'. So the version string is byte-identical while the code differs, which is precisely why a version-string comparison cannot detect this (same defect T-2884 documents for the daemon). CONSEQUENCE: any invocation of bare 'frob' rather than 'uv run frob' runs pre-fix code and leaks forkservers, and nothing signals it. This is the strongest lead for T-2888's LANG004 finding, which that agent characterized as execution-context-dependent rather than flapping -- in-process reproductions of the gate logic reliably PASS while the CLI reliably FAILS, twice, including with the gate cache cleared. Note the project CLAUDE.md instructs invoking bare 'frob' directly because it is installed as a uv tool; that instruction is unsafe whenever the tool lags the checkout, which is most of the time in an active repo since landing does not bump the package version. Worth deciding deliberately: either the tool must be refreshed on every land, or guidance should standardise on 'uv run frob', or frob should self-detect the skew by content rather than version. I did not refresh the tool -- that is a user-environment change outside this ticket. CAVEAT on my own measurement: I also grepped the global dsl.py for 'callee-raises' and got a hit, but that string can appear in a docstring or verb list without being in _RESERVED_MARKER_VERBS, so I am NOT claiming the global has T-2875's fix; only the _reap.py result is reliable.