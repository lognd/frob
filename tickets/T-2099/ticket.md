---
id: T-2099
title: The heaviest test files are unrunnable under the default -n auto but pass serially,
  so agents land land-path changes with their test file unrun
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given tests/test_ticket_land.py, when run through the repo default invocation
    with no manual -o addopts override, then it completes and reports a pass/fail
    summary within the 540s foreground budget -- this test MUST fail against current
    main, where it exceeds 540s and never reports
  evidence: []
- text: given tests/test_ticket_leases.py, when run the same way, then it completes
    and reports a summary rather than requiring a hand-picked subset
  evidence: []
- text: given the remaining ~9000 tests, when measured before and after, then total
    wall-clock has not materially regressed -- xdist is not disabled globally
  evidence: []
threat: null
component: testing
anchor: false
anchor_reason: null
---
## The measured inversion

`tests/test_ticket_land.py` (275 tests) is the repo's highest-traffic test
file and covers `frob ticket land`, the most safety-critical path here.

  SERIAL   (`-o addopts=""`, which drops `-n auto --dist=loadgroup`):
           275 passed in 420.18s -- I ran this myself, full summary line.
  PARALLEL (repo default `addopts = "-q -n auto --dist=loadgroup ..."`):
           exceeds 540s and never reports; the suite-measurement agent
           listed all 275 as UNMEASURED.

So the repo's DEFAULT execution mode is slower than serial on its heaviest
file -- slow enough to be unrunnable -- while serial finishes comfortably
inside a normal budget. These tests spawn real `git` and real subprocesses,
so xdist workers contend rather than parallelise.

Same pattern, reported independently:
- `tests/test_ticket_leases.py` (130 tests): T-2079's agent -- "would not
  complete in ANY foreground timeout tried"; it ran a 21-test write-path
  subset instead and said so honestly.
- `tests/test_coverage.py` (44 tests): stalls at test 5 (separate root
  cause, T-2098).

## The consequence, which is the reason this is not just friction

Agents edit `_land.py`, `_leases.py` and `_rapid_sweep.py` constantly -- most
of this session's criticals were in exactly those files -- and they CANNOT
run the tests that cover them. Every one of them did the honest thing and
ran a named subset while disclosing the gap. That is correct behaviour and
it is the best available under current tooling, but the net effect is that
the repo's most safety-critical code lands with its own test file unrun.

This is not hypothetical: the full-suite sweep found 32 failures and 3 hangs
at a ZERO unscoped gate-error floor. Gate-clean says nothing about these
files.

## Existing mechanisms that do NOT cover it

`frob test` has no serial / heavy-file / per-file-strategy option (checked
`--help`: `--all`, `--fuzz`, `--collect`, `--wait-coverage`, `--base`,
`--lang`, `--fallback`, `--json`). The playbook's answer is "run a subset",
which is a workaround for the symptom.

Note also `pytest -p no:xdist` does NOT work here -- `addopts` still injects
`-n auto --dist=loadgroup` and then nothing parses them (that gap is
T-2068). The only working incantation today is `-o addopts=""`, which is
undocumented folklore that every agent has to be told individually. I have
had to put it in every dispatch brief this session.

## DO NOT FIX IT THIS WAY

- **Do not just document `-o addopts=""` in the playbook.** Every agent has
  been told individually already; a rule that must be remembered before the
  tool works is not enforcement. This is exactly the case the standing audit
  rule names.
- **Do not globally disable xdist.** The other ~9,000 tests genuinely
  benefit; a repo-wide serial run would be far worse overall. The fix is
  per-file or per-group strategy, not a global switch.
- **Do not mark these files slow/skip by default.** They cover the land
  path. Making them easier to not run is the opposite of the goal.
- **Do not raise the foreground timeout and call it fixed.** 540s is a
  harness constraint agents cannot change; the work must fit it, or be
  runnable in a supported out-of-band way.
- **Do not assume `--dist=loadgroup` grouping already handles this.** It is
  configured today and the file still times out -- verify what the groups
  actually are before relying on them.

## Direction

Make the correct strategy automatic rather than remembered: a per-file (or
xdist-group) execution strategy so that files spawning real git/subprocesses
run serially while the rest stay parallel, reachable through `frob test`
without an undocumented `-o addopts=""`. Measure before and after: the
acceptance is a wall-clock number for the whole file, not a green subset.
