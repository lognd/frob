## Done report

Extracted the TODO00x/FMT001 family out of src/frob/gates/__init__.py
into a new src/frob/gates/_todo_fmt.py, following T-1072's WAIVE-family
sibling-module precedent exactly: _todo002_edges, _pyproject_version_at,
_todo003_long_deferred, _todo003_violation_for_edge, _todo001_bare,
_todo001_bare_comment, _todo001, _fmt001_touched_lines, _fmt001_file,
_fmt001_marker_entries, _fmt001_violations_for_runs, fmt_gate, and the
_TODO_RE constant, all moved verbatim with their frob:ticket/frob:tests/
frob:enforces/frob:doc/frob:waive directives intact.

src/frob/gates/__init__.py: 10164 -> ~9802 lines (chunked -- part of the
larger T-1077 remainder, does not by itself clear the large-file
threshold; residue refiled by the coordinator as T-1115 for the rest
after the original draft died at land).
New: src/frob/gates/_todo_fmt.py: 396 lines.

Three call sites (_todo002_edges's _site_from_edge_origin/_OPEN_STATES,
_todo003_long_deferred's _current_version, _todo003_violation_for_edge's
_blame_shas/_UNCOMMITTED_SHA/_site_from_edge_origin, _todo001_bare's
_touched_files, fmt_gate's _touched_files) needed lazy (call-time)
imports back from frob.gates to avoid an init-time circular import,
mirroring T-1072's _design_dir/_site_from_edge_origin lazy-import
pattern exactly -- all of those helpers stay defined in __init__.py
since many other still-resident gate families use them too.

__init__.py re-imports and re-exports only the three names other code
actually calls (_todo001, _todo003_long_deferred, fmt_gate -- verified
via repo-wide grep, no external module imports any of the other moved
private helpers directly), so every existing call site keeps working
unchanged. Dropped now-unused imports from __init__.py's own top-level
list (marker_for, read_line_length, fold_comment_runs -- confirmed via
ruff F401 after the move that nothing else in __init__.py used them).

No frob:tests/frob:doc directive needed a path fixup (DRIFT002/AFFECT001
clean): every TODO/FMT test binding already pointed at a test file path
(tests/test_gates.py::TestCoverageGate.* / TestFmt001Gate.*), not a
src/frob/gates/__init__.py::<symbol> source symref, so the physical
move did not break any existing directive.

git diff main --diff-filter=D --stat: empty (no unintended deletions).
Full tests/test_gates.py: 508 passed (FROB_WORKTREE/FROB_AGENT unset
per playbook 5b -- with them set, 7 unrelated pre-existing tests fail on
worktree-guard/lease env leak into tmp_path repos, a known artifact, not
a regression from this change).
frob check --ticket T-1077 --only drift: gate:DRIFT 0 errors, 0 warnings,
2 waived (both pre-existing T-0453 waivers, unrelated); gate:WAIVE 0
errors, 403 warnings (all WAIVE004 "0 findings in this --only-scoped run"
noise, expected per the gate's own known-flaky note), 0 waived.
frob check --ticket T-1077 --only arch: 0 errors (18 pre-existing
warnings + 232 suggestions, none introduced by this change -- confirmed
none reference src/frob/gates/_todo_fmt.py's own new abstraction shape
beyond the pattern-recommendation noise already present repo-wide).

Filed: T-1115, a coordinator refile after the draft died at land
(remaining gate families: DEBT/DEPR, SCOPE/
PREWORK, INV00x, TEST00x, DECISIONS, TICK00x, COMPLIANCE00x, SYS00x/
DOC00x, DUP00x, REL00x, FUZZ00x, DOCLINK/DOCANCHOR, PERF, run_gates
spine, and COV00x which T-1077 also left untouched) -- this ticket's
plan named ~15 families; doing all of them in one pass risked exactly
the kind of high-blast-radius diff T-0395 originally failed on, so this
land does one cohesive family (matching T-1072's own one-family-per-
land discipline) and hands the rest forward explicitly rather than
silently declaring the whole remainder done.

### Changed
```
 src/frob/gates/__init__.py  | 364 +---------------------------------------
 src/frob/gates/_todo_fmt.py | 396 ++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                  |  90 +++++++++-
 3 files changed, 486 insertions(+), 364 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_todo002_unbound_directive` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo001_bare_comment_in_touched_file` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo002_edge_to_closed_ticket` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo003_fires_after_version_bump_since_deferral_landed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_no_version_bump_since_deferral` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_ticket_closes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_directive_run_over_limit_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_ordinary_long_comment_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_long_code_line_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_untouched_line_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_short_directive_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
