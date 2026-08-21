---
id: T-2763
title: Coverage data is 14 days stale because the refresh OOMs in parallel and overruns
  serially, leaving TEST005 silently unmeasurable
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/check_summary.py
- tests/unit/test_coordinator_scripts.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: scripts/check_summary.py
  reason: 'legibility fix: surface TEST006 stale/missing coverage stamp distinctly
    in check_summary output'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: 'legibility fix: surface TEST006 stale/missing coverage stamp distinctly
    in check_summary output'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: doc target for check_summary.py symbols touched
  actor: logan
  at: '2026-08-20'
body_changes:
- mode: append
  reason: 'correct two falsified premises: worker count already derives from MemAvailable
    (the gap is single-snapshot sizing), and TEST005 delegates absent-coverage to
    TEST006 which already fires at ERROR (the gap is legibility)'
  actor: logan
  at: '2026-08-20'
  old_length: 3577
  new_length: 6221
evidence:
- tests/unit/test_coordinator_scripts.py::TestFindTest006::test_finds_test006_diagnostics
- tests/unit/test_coordinator_scripts.py::TestFindTest006::test_empty_when_no_test006
- tests/unit/test_coordinator_scripts.py::TestCheckSummaryMain::test_test006_banner_leads_output_when_present
- tests/unit/test_coordinator_scripts.py::TestCheckSummaryMain::test_no_banner_when_test006_absent
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 760420fa5e9a66629532cb85e4b4d9ad379accb1
---
## TEST005/TEST006 have been silently unmeasurable for 14 days

`.frob/coverage.partial.xml` is dated **Aug 6**. The committed
`frob-coverage.lock.json` is Aug 19. There is no `coverage.xml` anywhere
in the repo or in any worktree. Today is Aug 20, and hundreds of tickets
have landed in that window.

TWO INDEPENDENT AGENTS hit this today and both correctly refused to
report a number:
- one ran an unscoped `frob check --only test --no-cache` and got 54
  `gate:TEST` diagnostics of which **ZERO** were TEST005 -- the present
  ones were TEST014(32)/TEST003(20)/TEST001(1)/TEST006(1), all rules that
  do not need coverage data
- the other confirmed the same and cited playbook 6c: TEST005 SILENTLY
  SKIPS any file with no coverage data, so an absent `coverage.xml` reads
  as "nothing to flag", not "clean"

That is the silent-zero shape exactly: the gate reports nothing because
it cannot see, and nothing distinguishes that from a clean tree.

## The refresh cannot complete

`make coverage` is `frob ticket reconcile --apply && frob doctor &&
frob coverage --full`, and the playbook (3c/6b) makes it coordinator-only,
so no dispatched agent can run it. I ran it myself. Measured:

    coverage_refresh: explicit --full -- running the full suite
    ERROR: pytest --cov=src/frob --cov-report= -n 12 exited 3 and matched
    the xdist worker-crash signature (T-1672: a worker process was killed,
    most often OOM) -- retrying ONCE serially (-p no:xdist)
    coverage_refresh: neutralizing xdist token(s) ... for the serial retry

The parallel run OOMs at `-n 12`. The serial fallback then exceeds a
580s budget and was killed (exit 124). No `coverage.xml` was produced;
the root was left clean, so there is no residue -- but there is also no
measurement.

So the only path to refreshing coverage is one that OOMs in parallel and
overruns serially. That is why the data is 14 days old: not neglect, an
unrunnable step.

## Why this matters beyond one stale file

TEST005 is a RATCHET. T-1953 (held by owner decision) exists to raise its
floors. A ratchet whose input is 14 days stale cannot be raised safely,
and a ratchet that silently passes on absent data is not a ratchet at
all -- it is a gate that reports success when it has nothing to check.

## What to determine

1. Why does `-n 12` OOM? The T-1672 signature is already recognised in
   code, so the crash is expected -- but the worker count appears not to
   adapt. Consider deriving it from available memory rather than CPU
   count, the same way T-2715 made the sweep budget derive from measured
   stage timings instead of a frozen constant.
2. What does a serial full-coverage run actually cost? Measure it before
   choosing a strategy; nobody currently knows.
3. Should TEST005 REFUSE rather than skip when coverage data is absent or
   older than some threshold? A loud "cannot measure" is worth more than
   a silent pass, and this repo has spent the day fixing exactly that
   class of defect (T-2713, T-2715, T-2744).

## Positive controls, both directions

- with fresh coverage present, TEST005 fires on a genuinely uncovered
  file and does not fire on a covered one
- with coverage ABSENT or stale beyond threshold, the gate reports
  UNMEASURED/refuses -- it must not report zero findings
- the refresh completes on this machine without OOM, and its cost is
  stated

## Note

Do not "fix" this by lowering the coverage bar or by making the refresh
sample fewer tests. The measurement being expensive is not the bug; the
bug is that failing to measure is indistinguishable from measuring clean.




## CORRECTION (coordinator): TWO premises in this ticket were WRONG

An investigation pass read the code and falsified both. I verified each
myself before recording this.

### 1. The worker count DOES adapt to memory

I wrote that "the worker count appears not to adapt". It does.
`_compute_worker_count()` at `src/frob/testing/_coverage_refresh.py:716`
(landed under T-1672) reads /proc/meminfo's `MemAvailable` and caps at
`available_mb // _DEFAULT_PER_WORKER_MEM_MB` (1536MB, line 629). It is
wired into the real `--full` path. Measured live: on this box it computes
**10** workers, not 12.

So my suggested remedy -- "derive it from memory rather than CPU count"
-- was proposing something already implemented.

THE REAL GAP IS SHARPER: sizing is a SINGLE SNAPSHOT taken at start, and
is never re-checked as sibling agent processes grow during a multi-minute
run. The `-n 12` OOM I quoted almost certainly came from a snapshot taken
before concurrent fleet load (dozens of agent worktrees and venvs) drove
memory down mid-run. That is a re-check problem, not a missing heuristic,
and the fix is different.

### 2. TEST005's skip is BY DESIGN and already has a loud counterpart

I framed the absent-coverage skip as a silent zero. It is not.
TEST005's own docstring (T-0557) explicitly delegates "file has no
coverage data at all" to TEST006 as a measurement gap rather than
evidence the symbol is uncovered. TEST006 (`_test006_missing` /
`_test006_stale`, `src/frob/gates/__init__.py:4932-4948`) fires at ERROR
when the stamp is missing or stale -- and it DID fire in both agents'
runs today. `.frob/coverage-stamp` is dated Aug 6.

So the loud refusal I asked for already exists. I looked at zero TEST005
findings and concluded silence, without noticing the TEST006 ERROR that
was the signal.

### What the real defect is

LEGIBILITY, not missing logic. One TEST006 ERROR line inside 54 mixed
findings is easy to lose, so "zero TEST005 findings" reads exactly like a
clean measurement even though the warning was present. Two agents and I
all read it that way today.

Preferred remedy, narrowed: surface TEST006 DISTINCTLY -- e.g. have
`scripts/check_summary.py` lead with "coverage is N days stale; TEST005
findings below are NOT a clean measurement" -- rather than adding refusal
logic to TEST005, which would duplicate a rule that is already correct.

### What still stands

The serial full-coverage cost is genuinely UNMEASURED. One run was killed
at a 580s watchdog. It needs a deliberate measurement with a longer
watchdog during a quiet window, not a piecemeal attempt by whichever
agent hits it. That remains the open question.