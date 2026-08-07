## Done report

Split the conflated TODO001 rule into two per-failure-mode rule ids,
matching frob's own one-id-per-mode convention (WAIVE001/002, COV001-004,
TEST001-010, DUP001/002, PERF001-004):

- TODO001: a bare, wholly untracked TODO/FIXME comment in a diff-touched
  file (`_todo001_bare`/`_todo001_bare_comment`) -- work not accounted for
  at all.
- TODO002: a `frob:todo` edge bound to a non-open (closed or missing)
  ticket (`_todo002_edges`) -- work was accounted for once, but the
  reference is now dangling.

`_todo001` is now a thin dispatcher over both, `_KNOWN_GATE_RULES` lists
both ids, `docs/modules/gates.md`'s rule catalog and severity-defaults note
both cover TODO002, and `tests/test_gates.py` carries dedicated cases per
mode (bare-untracked, dangling-to-missing, dangling-to-closed) plus a
negative assertion that each case does NOT also fire the other rule id.
Swept the repo for other TODO001-only references (frob.toml has no
TODO001-specific entries to migrate; existing docs/tests already updated
in the same change).

Test results: `uv run pytest tests/test_gates.py -q` -- 186 passed.
`uv run pytest --collect-only -q` -- collects cleanly repo-wide, no errors.

Gates: `uv run frob check --ticket T-0425` -- 0 errors, 1 warning (TEST006,
no coverage stamp; coordinator-side), 91 waived, scope/prework/coverage all
clean for this ticket's scope. One unrelated pre-existing error remains in
the full check output: COV003 on already-closed T-0416, whose recorded
evidence node id no longer collects
(`tests/unit/strata/test_code_binding.py::TestBindCode::
test_nested_git_checkout_pruned_even_when_not_covered_by_exclude_globs`) --
confirmed out of T-0425's scope (src/frob/gates/, frob.toml,
docs/modules/gates.md, tests/test_gates.py) and pre-dates this change;
not filed as T-draft-5443bd5e (never refiled) rather than fixed here.

Not Filed: T-draft-5443bd5e (never refiled) (T-0416 evidence no longer collects, COV003) --
out-of-scope discovery, not fixed in this ticket.

### Changed
```
 docs/modules/gates.md      |  5 +--
 src/frob/gates/__init__.py | 44 ++++++++++++++++-------
 tests/test_gates.py        | 21 +++++++++--
 tickets.md                 | 87 ++++++++++++++++++++++++++++++++++++++++++++--
 4 files changed, 137 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_todo002_unbound_directive` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo001_bare_comment_in_touched_file` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo002_edge_to_closed_ticket` (pytest node id, verified passing when recorded)
