## Done report

Root-caused and fixed the suspected root cause from the ticket body: a
plain `git merge` conflict-resolution commit's default subject ("Merge
branch '...'") carries no ticket reference at all, yet `git blame` can
attribute a reconciled hunk to that merge commit sha directly (when the
resolved content differs from every parent -- a real conflict-resolution
edit, not a pass-through). `_commit_exempts_file`
(src/frob/gates/__init__.py) previously required THAT commit's own
subject to carry a ticket reference naming a ticket whose scope covers
the file; a merge commit with no ticket reference of its own therefore
always failed the exemption, even though its content is just reconciling
its parents' own already-scoped work.

Fix: new `_commit_parents` helper (`git log -1 --format=%P`); when a
commit has more than one parent AND its own subject carries no ticket
reference, `_commit_exempts_file` now also searches its PARENTS'
subjects for the reference that actually attributes the reconciled
content, before concluding the touch is unattributed. A merge commit
whose OWN subject does carry a ticket reference is unaffected (parents
are only consulted as a fallback, never override an explicit reference);
a non-merge commit (single parent) is entirely unaffected.

Regression test added: `tests/test_gates.py::TestScopePrework::
test_scope001_merge_commit_with_no_ticket_ref_falls_back_to_parent`
builds a real merge-commit fixture (two branches diverge from main both
editing the same file's same lines under ticket T-0001, merged with
`git merge --no-ff` producing a genuine conflict, resolved and committed
with a default no-ticket-reference merge message) and asserts the
resulting SCOPE001 check for an unrelated ticket T-0002 does not flag the
merged file.

Scope was widened by three files: `tests/test_gates.py` (`frob ticket
scope --add`) to add the regression test to the existing gates test
file's `TestScopePrework` class rather than a new untracked file; and
`src/frob/graph/dsl.py` + `tests/unit/graph/test_dsl.py` (the T-0108/
T-0412 cross-ticket-exemption precedent) because one of T-0526's own
commit subjects in this sequential single-worktree flow did not carry a
`T-0526` reference, so those two already-committed files kept showing as
out-of-scope in T-0527's own `frob check --ticket` diff-vs-main run.

Gates: `uv run frob check --ticket T-0527 --json` -> 0 errors (567
pre-existing warnings/118 waivers repo-wide, unrelated to this ticket's
touched files). `ruff check`/`ruff format --check` clean on both touched
files under both the PATH `ruff` and `uv run ruff`. `uv run pytest
tests/test_gates.py -q` -> 253 passed (full file, not just the scope001
subset, to rule out a regression elsewhere in the same module).

### Changed
```
 src/frob/gates/__init__.py   |  64 ++++++++++----
 src/frob/graph/dsl.py        |  97 +++++++++++++++++++++
 tests/test_gates.py          |  70 ++++++++++++++++
 tests/unit/graph/test_dsl.py |  57 +++++++++++++
 tickets.md                   | 196 +++++++++++++++++++++++++++++++++++++++++--
 5 files changed, 463 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestScopePrework::test_scope001_merge_commit_with_no_ticket_ref_falls_back_to_parent` (pytest node id, verified passing when recorded)
