---
id: T-4278
title: 'five remaining windows failures with no owner: worktree-guard stdout purity,
  clipboard attach, two shared-identifier-counter cases, and the claude-config stale
  guard'
state: in-progress
kind: bug
origin: human
created: '2026-09-07'
priority: high
parent: T-4236
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_worktree_guard.py
- tests/unit/test_app_runners_batch7.py
- tests/unit/test_process_lock.py
- tests/unit/test_sync_claude_config_stale_guard_t3408.py
- .claude/hooks/sync-claude-config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/sync-claude-config.py
  reason: T-4278's claude-config stale-guard failure is a genuine production bug in
    the hook itself (main()'s dest_rel = str(dest.relative_to(_HOME_CLAUDE)) uses
    the native separator, backslash on Windows, while dest_to_source is keyed by MANAGED's
    forward-slash strings -- the lookup misses on Windows so the stale-skip branch
    never triggers), not a test-only fix; adding the hook file to scope to fix it
    directly, the same class of separator bug T-4155 just fixed in frob.excludes
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
acceptance:
- text: given the windows runner, when these five cases run, then all five pass and
    each failure was measured on real windows before and after its fix
  evidence: []
- text: given the two cases adjacent to the terminal-detection helper landed today,
    when they are fixed, then the existing shared helper is reused or extended rather
    than a second similar helper being introduced
  evidence: []
- text: given the shared-identifier-counter pair, when they are resolved, then the
    report states explicitly whether the allocation guarantee genuinely fails on this
    platform or the tests premise does not hold there
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FIVE REMAINING WINDOWS FAILURES WITH NO OWNER. Taken from the integration run's
own failure list on the current tree, after today's three Windows tickets landed.
That run reported eleven failures on the windows leg; three belong to a ticket in
flight, two belong to the path-shape mechanism ticket, one belongs to the
scaffold console-script ticket, and these five had nobody.

  The worktree guard's stdout-purity case, asserting a bare evaluation succeeds
  with no filtering.
  The clipboard-attach-on-new case in the app runners suite.
  Two shared-identifier-counter cases in the process lock suite: one asserting
  two checkouts with divergent views never collide, and one asserting that a
  platform with no lock primitive refuses loudly.
  The stale-managed-sources guard case in the claude-config sync suite.

TWO OF THESE SIT DIRECTLY NEXT TO WORK THAT JUST LANDED, AND THAT IS THE FIRST
THING TO CHECK. A ticket landed today fixing interactive-terminal detection on
this platform, because the standard check reports a terminal even when input is
redirected from the null device, and it introduced a shared helper used by the
attach path and the new-ticket clipboard offer. The clipboard case here is in
that same area, and the worktree-guard case is in the same file that ticket also
touched. So either its fix did not reach these call sites, or these have a
different cause that resembles it. Determine which before writing anything: a
second, subtly different helper would be worse than the original defect.

THE SHARED IDENTIFIER COUNTER PAIR IS THE MOST INTERESTING AND SHOULD BE TREATED
AS POSSIBLY SERIOUS. One case asserts that two checkouts with divergent views
never allocate the same identifier, and the other asserts that a platform lacking
a lock primitive refuses loudly rather than proceeding. Those are correctness
properties about allocation under concurrency, not cosmetic platform details, and
this project has already measured a duplicate identifier being produced in the
window between one process reading the taken set and writing its own. If the
locking primitive these rely on is absent or behaves differently here, then
identifier allocation on this platform may be silently unsafe rather than merely
untested. Establish which of "the test's premise is wrong here" and "the
guarantee genuinely does not hold here" is true, and say so explicitly.

MEASURE ON REAL WINDOWS. The mirror harness runs commands natively on this
platform, so reproduce each failure there before changing anything and re-measure
after. Do not reason about behaviour from a linux shell; three separate premises
were corrected that way today, including one in a ticket body I wrote myself.
Two known traps: a bare interpreter name resolves to an application-execution
stub and exits with a distinctive code rather than running anything, and the
virtual environment places its executables in a different directory than on
posix.

DO NOT ASSUME THESE ARE FIVE SEPARATE DEFECTS, AND DO NOT ASSUME THEY ARE ONE.
Report which they turned out to be.
