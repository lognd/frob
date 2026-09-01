## Done report

LARGE001: .claude/hooks/root-write-guard.py was 834 lines. Split the
entry point (main/_handle_bash/_handle_file_write/_deny plus the
entry-coupled constants _GUARDED_TOOLS/REASON) from every pure
target-resolution/shell-tokenization/worktree-fact helper, moved
verbatim into a new .claude/hooks/_root_write_guard_lib.py, imported
via the sys.path.insert + bare-module-name pattern frob-suggest.py/
root-cleanliness-detector.py already use for _shellscan/_agent_context.
Entry contract (stdin JSON in, deny payload on stdout, silent allow
otherwise) is byte-for-byte unchanged. root-write-guard.py shrank from
834 to 256 lines.

Added the new lib module to sync-claude-config.py's MANAGED list (it
must materialize to ~/.claude/hooks alongside the entry point that
imports it) and repointed/extended docs/guides/claude-hooks.md.
Removed the repeated per-symbol frob:doc anchor from the new lib
module's helpers (COV007: doc anchors normally cover only the public
API surface; the entry point file already carries the frob:tests
citation) and waived DUP001 on _git/_worktree_paths (pre-existing
narrow duplicates of _agent_context.py's own copies, unchanged by the
move -- present verbatim in root-write-guard.py before this split too).

Verified BOTH directions by direct stdin invocation: a benign write
inside a worktree is allowed (no output, exit 0); a write targeting
the primary checkout root is refused (permissionDecision: deny, same
REASON text). Ran tests/test_hook_root_write_guard.py 3x with zero
flakes (39/39 each run), both before and after the post-rebase state.
`frob claude sync --check` correctly reports both changed hook files
as drifted against the currently-materialized ~/.claude/hooks/ copy --
expected pre-land (the source only reaches main once this ticket
lands; materializing ~/.claude/ from an unlanded worktree mid-fleet
would affect every other live agent's hook copy, so the actual sync
is deliberately NOT run here).

Evidence: tests/test_hook_root_write_guard.py (existing suite, 39
tests, re-run 3x against the split code, 0 failures each run).

Filed: none.

Gates: frob check --ticket T-3626 shows zero LARGE001/ARCH102/ARCH103
findings attributable to this ticket's files. Remaining 14 scoped
errors are pre-existing/out-of-scope (ARCH102 on _lock.py/
_land_squash.py -- later ticket in this series; COV/DEPR/OPAQUE/REL/
TEST/WAIVE items in unrelated files) plus the two expected
claude-config-drift findings explained above.

### Changed
```
 .claude/hooks/_root_write_guard_lib.py | 613 ++++++++++++++++++++++++++++++++
 .claude/hooks/root-write-guard.py      | 624 ++-------------------------------
 .claude/hooks/sync-claude-config.py    |   4 +
 docs/guides/claude-hooks.md            |   9 +
 tickets/T-3626/done-report.md          |  63 ++++
 tickets/T-3626/ticket.md               |   6 +-
 6 files changed, 717 insertions(+), 602 deletions(-)
```

### Evidence
- `tests/test_hook_root_write_guard.py::test_no_marker_write_to_root_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_write_inside_a_real_worktree_is_allowed_with_no_markers` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_redirect_into_primary_with_no_marker_is_refused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 10 error(s), 4175 warning(s), 903 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, OPAQUE001@src/frob/app/_config_external.py, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
