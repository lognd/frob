## Done report

Root cause: T-1893's own land added `# ty: ignore[unresolved-import]` next
to the existing `# noqa: E402` on the `_shellscan` import line in both
hook scripts, to silence ty's unresolved-import complaint about the
sys.path-inserted local module. ty does not actually report
unresolved-import on either line (verified directly: `uv run ty check`
against both files reports zero unresolved-import diagnostics, and
instead flags `unused-ignore-comment` on the exact suppression added) --
so the added ty suppression was never live evidence, it was preventative
and wrong from the start. SUPPRESS001 correctly flags a suppression
comment with no matching unsuppressed diagnostic underneath it.

Fix: removed the stale `# ty: ignore[unresolved-import]` segment from
both import lines, keeping the still-live `# noqa: E402` (ruff genuinely
flags E402 there, confirmed separately). This fixes the underlying
mismatch rather than widening any waiver -- no frob:waive was added.

Verification: `uv run frob check --only suppress` read 2 errors
(SUPPRESS001 on both files) before the change and 0 errors after,
against the identical two-file scope. `uv run ruff check` and `uv run ty
check` both report clean on both files post-fix.

Real fail-then-pass proof: the existing repo-wide lock test
`tests/test_gates_suppress.py::TestSuppress001RepoWideLock::test_repo_is_currently_clean`
runs `suppress001_gate` against this actual repo tree (not a fixture).
At the parent commit (with the stale ty-ignore comments present) it
FAILS with exactly the two SUPPRESS001 violations this ticket names,
verified directly by reverting the fix with `git apply -R` and re-running
the test. With the fix applied it PASSES. Scope was widened by one
`frob ticket scope --remove` no-op cycle while confirming no new test
file was needed -- final scope is unchanged, the two hook files only.

### Changed
```
 tickets/T-1912/done-report.md | 36 ++++++++++++++++++++++++++++++++++++
 tickets/T-1912/ticket.md      | 24 +++++++++++++++++++++++-
 2 files changed, 59 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates_suppress.py::TestSuppress001RepoWideLock::test_repo_is_currently_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 784 warning(s), 697 waived
- error-findings: REG002@docs/design/registry/check-coverage.yaml
