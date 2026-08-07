## Done report

Consolidated the "at least 9 gates modules each define their own
_tracked_files-shaped git-ls-files scan" duplication T-1082 specifically
called out: 5 of them (_opaque.py, _exclude_hazard.py, _refs.py,
_secrets.py, _cve_fingerprint_scan.py) had a byte-for-byte identical
`_tracked_files(root) -> tuple[str, ...]` private helper (git ls-files,
root-relative POSIX paths, degrade-to-() on any git failure). Extracted
one shared `frob.gates._tracked_files.tracked_files(root, *, caller)`
(new module) and inlined every one of the 5 call sites directly against
it, deleting all 5 per-file wrapper functions entirely (not left as thin
wrappers -- the arch detector clusters by signature, and a same-named,
same-signature wrapper in each file would still have counted as the
"N functions share this signature" abstraction-opportunity finding even
with identical bodies collapsed to a one-line delegate).

Two of the five (_exclude_hazard.py, _cve_fingerprint_scan.py) logged at
ERROR on a git failure; the shared helper standardizes on WARNING
(matching the majority -- _opaque.py/_refs.py/_secrets.py already used
WARNING) -- a disclosed, minor severity harmonization, not a behavior
change to the scan itself (still degrades to `()`, never raises).
_opaque.py's/_secrets.py's extra "N tracked file(s)" debug log line was
dropped rather than preserved via a wrapper, for the same signature-
collapse reason above -- disclosed, not silently lost (it was DEBUG-tier
and untested).

tests/test_secrets_gate.py::TestTrackedFilesGitFailure's two tests
monkeypatched `frob.gates._secrets.run_argv` directly (the old
module-local seam) -- repointed to `frob.gates._tracked_files.run_argv`
(the new, real seam) since that name-level fixup is a direct, mechanical
consequence of the consolidation itself, not new test-writing.

Did NOT attempt: the other 29 findings T-1082 (and T-1067 before it)
named (19 in gates/__init__.py, 1 each in _baseline.py,
_cve_fingerprint_scan.py's own OTHER cluster, _docblocks.py,
_fmt_directives.py, _gate_cache.py, _waive.py/_waive_lease.py,
invariants.py, 3 in _pii_structural.py), nor the wider
`_tracked_python_files`-shaped duplication (_walk_lint.py,
_pii_structural/_tracked.py, _docblocks.py, _docptr.py) the ticket
flagged as likely undercounted, nor the small new cluster this
consolidation itself surfaced (the new shared `tracked_files` now shares
a `(Path, str) -> tuple[str, ...]` signature with 4 unrelated functions
in src/frob/dup/_pipeline/_callgraph.py -- out of gates/ scope). Filed:
T-1114 (remeasure before starting -- other tickets may have
moved the count).

git diff main --diff-filter=D --stat: empty (no unintended deletions;
the initial run before this ticket's final `git merge main` transiently
showed tests/test_coverage_wait_shared.py as a 231-line deletion --
main had advanced past what this worktree last merged, past T-1095's
landing of that file; a fresh `git merge main` picked it up cleanly and
the deletion-filter check is now empty, confirmed).
tests/test_gates.py + test_secrets_gate.py + test_vet.py: 693 passed.
frob check --ticket T-1082 --only arch: 0 errors; grep-confirmed
"tracked_files" no longer appears in ANY abstraction-opportunity finding
for the 5 consolidated modules. 17 pre-existing warnings + 235
suggestions (one net-new suggestion: the dup/_pipeline/_callgraph.py
cross-package cluster noted above, disclosed, filed as part of the
residue ticket's scope-note rather than fixed out-of-scope here).
frob check --ticket T-1082 --only drift/--only test: 0 errors both runs.

### Changed
```
 src/frob/gates/_cve_fingerprint_scan.py | 21 ++----------------
 src/frob/gates/_exclude_hazard.py       | 19 ++---------------
 src/frob/gates/_opaque.py               | 27 ++---------------------
 src/frob/gates/_refs.py                 | 21 ++----------------
 src/frob/gates/_secrets.py              | 29 +++----------------------
 src/frob/gates/_tracked_files.py        | 38 +++++++++++++++++++++++++++++++++
 tests/test_secrets_gate.py              |  8 +++----
 tickets.md                              |  2 +-
 8 files changed, 54 insertions(+), 111 deletions(-)
```

### Evidence
- `tests/test_secrets_gate.py::TestTrackedFilesGitFailure::test_spawn_error_yields_no_tracked_files` (pytest node id, verified passing when recorded)
- `tests/test_secrets_gate.py::TestTrackedFilesGitFailure::test_nonzero_exit_yields_no_tracked_files` (pytest node id, verified passing when recorded)
- `tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_repo_is_clean` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
