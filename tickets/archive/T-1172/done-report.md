## Done report

T-1152's evidence-family split moved `_run_evidence_command` into
src/frob/tickets/_evidence.py without re-exporting it from the package --
tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell imports
it directly (`from frob.tickets import _run_evidence_command`, predating
the split) and broke with ImportError. Found via a broad `frob test
--base main` touched-set run while landing T-1165 in the same worktree.

Added `_run_evidence_command` to the `from frob.tickets._evidence import
(...)` re-export list in src/frob/tickets/__init__.py (with a noqa: F401
+ explanation comment matching the file's own established pattern for
package-attribute re-exports test files depend on directly).

This fix's code was carried into main as part of T-1165's land (same
worktree, same branch) -- no separate diff remains to land; closing this
ticket directly against main.

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_command_substitution_is_not_expanded` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
