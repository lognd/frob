---
id: T-draft-5eb5b6d8
title: frob refactor split moves symbol bodies without carrying their own needed imports
state: queued
kind: bug
origin: agent
created: '2026-08-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/_scan.py
- src/frob/refactor/_split.py
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
MEASURED 2026-08-27, T-3086 attempt 4 (after T-3066/T-3105/T-3109 all
landed). Ran the exact split from T-3086's brief:

    frob refactor split frob.gates._models \
      --symbols Severity,WaiverRef,DebtEntry,Violation \
      --into frob.findings

The split applied cleanly (140 ops across 131 files), committed as
`wip(refactor): split frob.gates._models -> frob.findings (...)`, and
its own `import_resolution` verify step passed (it only checks
call-site imports and local-name resolution against the destination
module's own top-level defs, not the destination file's OWN
free-standing type-name dependencies). The split's `run_check_delta`
step (`frob check --delta`, invoked via the stale global `frob` tool
per its own subprocess call, not `uv run frob`) then timed out at 100s
and the CLI errored out mid-dispatch -- but by that point the commit
had already landed in the worktree, so the corruption below is real,
not an artifact of the timeout.

ROOT CAUSE: `frob.findings` (`run_split`'s destination module) contains
the four moved class bodies verbatim -- `class Severity(StrEnum):`,
`class WaiverRef(BaseModel):`, `class DebtEntry(BaseModel):`, `class
Violation(BaseModel):` -- with ZERO import statements. `StrEnum`,
`BaseModel`, and `ConfigDict` are all undefined names in the new
module. `import frob.findings` (and therefore
`import frob.gates._models`, transitively) raises
`NameError: name 'StrEnum' is not defined` immediately.

The split's move-definition logic (wherever it slices `_models.py`'s
source for the moved symbols' own text) never re-derives or copies
forward the subset of `_models.py`'s own top-level imports that the
moved symbols' bodies/base-classes/annotations actually reference. It
moves the symbol text; it does not move (or add) what that text needs
to run.

CONFIRMED BY: `uv run python -c "import frob.findings"` on the
committed split output ->
`NameError: name 'StrEnum' is not defined`.

Per the standing per-attempt directive, this was NOT hand-edited
around: the worktree was reset (`git reset --hard` to the pre-split
commit) and this ticket filed instead. T-3086 itself is failed with
this as the blocking finding -- do not retry it until this lands.

This is the FOURTH distinct, independent `frob refactor split` defect
found by one real extraction attempt in 2026-08-27 (after T-3066/
T-3105/T-3109), reinforcing T-3110's own finding: the verb had never
been exercised at real scale before this drive, and every new shape
still finds a new way it breaks.
