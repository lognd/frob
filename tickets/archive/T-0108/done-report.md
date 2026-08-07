## Done report

Changed:
- src/frob/gates/__init__.py::scope_gate (new optional `root`/`queue` kwargs)
- src/frob/gates/__init__.py::_blame_shas (new, private)
- src/frob/gates/__init__.py::_commit_subject (new, private)
- src/frob/gates/__init__.py::_commit_exempts_file (new, private)
- src/frob/gates/__init__.py::_hunk_exempt (new, private)
- src/frob/gates/__init__.py::_scope_exempt_file (new, private)
- src/frob/gates/__init__.py: `_build_jobs`'s "scope" job now passes `root=st.root, queue=st.queue` to `scope_gate`

Chosen semantics: a file that fails a ticket's own `scope` glob match is
re-checked hunk by hunk (`git blame --porcelain` via the existing public
`frob.gitio.run_argv` seam -- no new module, since `frob.gitio` is outside
this ticket's declared scope). A hunk is exempt only if every line is
already committed (no `UNCOMMITTED_SHA`/all-zero sha -- a ticket's own
in-progress dirty edit is never exempt) and every covering commit's subject
matches `T-\d{4}` for a ticket other than the one being checked, where that
other ticket exists in the queue and its own `scope` covers the file. A file
is exempt only if every hunk touching it clears this bar; a file mixing A's
committed work with B's own dirty edit still flags SCOPE001 for B. The old
unconditional (`root=None`, `queue=None`) behavior is preserved for direct
callers/tests, so `run_gates` is the only call site that opts in.

Evidence:
- tests/test_gates.py::TestScopePrework::test_scope001_exempts_file_committed_by_earlier_ticket
  (reproduces the T-0108 false positive end-to-end with two real git commits
  on a feature branch and asserts both the old false-positive behavior with
  no root/queue, and the fix with root/queue)
- tests/test_gates.py::TestScopePrework::test_scope001_still_flags_uncommitted_out_of_scope_edit
  (guards against the exemption swallowing a ticket's own dirty edit)
- tests/test_gates.py::TestScopePrework::test_scope001_does_not_exempt_when_referenced_ticket_lacks_scope
  (guards against granting an exemption when the referenced ticket doesn't
  declare the file in its own scope)
- Existing tests/test_gates.py::TestScopePrework::test_scope001_out_of_scope_file,
  test_scope001_passes_in_scope, test_scope_unrestricted_when_no_scope_declared
  still pass unchanged (old-signature callers keep old behavior)
- `uv run pytest tests/test_gates.py -q`: 86 passed
- `uv run frob test` (touched-set): 1 runner, python exit=0

Filed: none. First pass filed T-0128 (a standalone docs ticket) and left
docs/modules/gates.md's scope_gate entry stale under its own `frob:doc
docs/modules/gates.md#public-api` edge. Reviewer correctly rejected this:
changing a public symbol's signature under an existing `frob:doc` edge
without re-acking is DRIFT001 regardless of whether a follow-up ticket
exists to eventually update the prose. Fixed by widening this ticket's own
`scope` to include `docs/modules/gates.md`, updating the `scope_gate` entry
under Public API in place (new `root`/`queue` kwargs + a 3-line description
of the cross-ticket commit exemption), and running `frob ack
src/frob/gates/__init__.py::scope_gate` to clear the stale digest. T-0128 is
now `dropped` with reason "absorbed into T-0108" (see its own Dropped
section). Also folded 6 duplicated local `import fnmatch` statements
scattered across gates/__init__.py (2 of them mine) into one top-level
`import fnmatch`.

Gates: first pass's claim that "no findings touch gates/__init__.py" was
false -- `frob check --ticket T-0108` had an unwaived DRIFT001 on
`src/frob/gates/__init__.py::scope_gate` (sig digest moved since ack, 6
dependents) that the reviewer caught. That is now resolved: scope widened,
docs/modules/gates.md updated, `frob ack` run, confirmed clear (see below).
`uv run ruff check`, `uv run ruff format --check`, `uv run ty check` all
clean on src/frob/gates/__init__.py, tests/test_gates.py, and
docs/modules/gates.md. `frob check --ticket T-0108` now shows no unwaived
findings on any file this ticket touches (src/frob/gates/__init__.py,
tests/test_gates.py, docs/modules/gates.md); the only remaining SCOPE001 is
on tickets.md itself (an artifact of `frob ticket start`/evidence editing
tickets.md, not something this ticket's code change introduced), plus
repo-wide baseline noise (ty unresolved-import on `strata_core`/`frob_core`
native extensions not built in this worktree, 2 unrelated strata files
needing `ruff format`) predating this change. `frob ticket evidence T-0108
...` could not run its automatic `pytest --collect-only` binding step
because collection itself fails repo-wide on the 22 `tests/unit/strata/**`
files that import the unbuilt `strata_core`/`frob_core` native modules
(pre-existing, unrelated to T-0108); evidence ids above were verified
manually via `uv run pytest tests/test_gates.py -k scope001 -q` (5 passed)
and recorded directly in this ticket's `evidence` field. `_commit_exempts_file`,
`_scope_exempt_file`, and the new test's two `any(v.file == ... for v in ...)`
assertions each tripped `perf_gate`'s PERF003 heuristic (two-or-more `for`
headers plus an `==` anywhere) despite being single-pass, non-nested code --
same false-positive shape as the pre-existing waived PERF003s elsewhere in
this file (e.g. `src/frob/logging/quiet.py`'s "two single-pass loops, not
nested"); waived all three with `frob:waive PERF003 reason=...` rather than
contorting the code to dodge a coarse token heuristic.
