## Done report

B8 fix: `_load_diff` (src/frob/gates/__init__.py) now returns
`tuple[Diff, bool]` -- the second element is `True` only when
`working_diff` genuinely failed (bad --base, no merge-base, git error),
never for an honestly clean/empty diff. `_GateInputs` carries this as
`diff_load_failed`. `coverage_gate` gained an optional
`diff_load_failed: bool = False` param: when set, COV002 and TODO001 (both
diff-driven) are each replaced with one loud `_diff_load_failed_violation`
instead of being evaluated against a diff known to be a failure
placeholder. `_build_ticket_scoped_jobs`'s "scope" job does the same for
SCOPE001, following the same loud-blocking-condition pattern T-0541 (B9)
already established for "no active ticket" via `_no_active_ticket_violation`.

Counterexample: a repo with no git history at all (working_diff has no
merge-base, fails outright) used to silently degrade to an empty Diff, so
`frob check --gates coverage` against a fresh public/undocumented/untested
symbol reported ZERO COV002 violations -- the exact failure-looks-like-
clean-tree bug B8 describes. Post-fix, COV002 fires with a message
containing "failed to load" instead of silently passing
(`test_diff_dependent_gates_block_loudly_on_failed_diff`).

`coverage_gate` is a public symbol; its new optional trailing param is a
non-breaking but signature-changing addition, so `frob ack
src/frob/gates/__init__.py::coverage_gate` was run and `pyproject.toml`
bumped 0.63.0 -> 0.64.0 (`frob release stamp`), scope-added
(pyproject.toml/.frob-release.json/frob.lock/uv.lock) with a recorded
`scope_changes` reason.

Not Filed T-draft-f5d48e02 (never refiled) (out-of-scope discovery): the T-0214/T-0320
closed-ticket COV002 grace window checks only the ticket's exact
`<!-- ticket:ID -->` marker LINE against the diff's unified=0 hunks, which
does not always fall inside a hunk even when the ticket's own state
transition plainly is in the diff (hit this directly when checking T-0550
right after committing/closing T-0549 on this same stacked, unmerged
branch) -- waived the resulting 4 spurious COV002 findings on T-0549's own
already-covered test methods with a reference to that new ticket, rather
than silently working around it.

### Changed
```
 src/frob/gates/__init__.py |  98 ++++++++++++++++++++++++++++++++++--
 tests/test_gates.py        | 122 +++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                 |  40 ++++++++++++++-
 3 files changed, 254 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestGatesDegradeWithoutDiff::test_diff_dependent_gates_block_loudly_on_failed_diff` (pytest node id, verified passing when recorded)
