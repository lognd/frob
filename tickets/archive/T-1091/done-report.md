## Done report

_coverage_totality_scan_prefix now unconditionally returns None -- the
_PACKAGE_ROOT ("src/frob") carve-out T-0667 shipped for SYS103 is
dropped entirely, not just modeled around. T-1079 already proved (via
TestCoverageTotality::test_repo_unrestricted_scan_is_clean, monkeypatching
the prefix to None) that an unrestricted scan against the real repo tree
and the real design/frob.strata model returns zero SYS100/SYS101/SYS102/
SYS103 findings, now that tests/**, scripts/**, frob-core/src/**, and
strata-core/src/** are modeled as real nodes (testsuite, scripts_ops,
frob_core_native, strata_core_native). This ticket makes that the LIVE
gate's own behavior: SELFAUDIT001 (frob check --only sys / frob sys
audit) now scans the whole repo on every run, frob's own tree included,
with no restriction.

Verification:
- The monkeypatch-based test.test_repo_unrestricted_scan_is_clean keeps
  passing (its monkeypatch is now a no-op against the new default, kept
  so the test still pins the claim independently of the function's
  current implementation, per its updated docstring).
- TestRealGateGreen.test_repo_design_and_declarations_are_self_conformant
  (no monkeypatch) now exercises the production, unrestricted path
  directly and still returns zero violations.
- TestCoverageTotality.test_fires_outside_src_frob_layout (a fake repo
  under tmp_path with no src/frob/ at all) is unaffected -- this
  function's prefix was always None outside frob's own tree, so this
  case's behavior is unchanged.
- Docs: docs/modules/strata.md's SYS-COV section gets a new "Restriction
  dropped for real (T-1091)" subsection, and the "Why SYS103, not just
  SYS102" intro is reworded from "EXCEPT on frob's own tree" to
  "INCLUDING frob's own tree, as of T-1091". Module docstring
  (_selfconform.py) and _coverage_totality_violations's own docstring
  updated to match.

Full test suite (tests/unit/strata/test_selfconform.py): 68 passed
(uv run pytest tests/unit/strata/test_selfconform.py -q).

Gate verification (all foreground, chunked):
- uv run frob check --ticket T-1091 --only gates-native: 0 errors.
- uv run frob check --ticket T-1091 --only gates-security: 0 errors.
- uv run frob check --ticket T-1091 --only gates-fast: 3 remaining
  errors, all pre-existing and unrelated to this ticket's scope --
  COV001 on src/frob/gates/_tracked_files.py (untouched by this diff),
  INV006 on src/frob/app/ticket_runner/_mutate.py (untouched), TICK006
  on T-1114's own phantom draft citation (a different, already-landed
  ticket's residue). The AFFECT001 finding this change originally
  tripped on _coverage_totality_scan_prefix itself is resolved by the
  docs/modules/strata.md update above (no waiver needed).
- uv run frob check --ticket T-1091 --only static: 0 errors.
- uv run frob check --ticket T-1091 --only lint: 0 errors in this
  ticket's own files; the 6 remaining ruff-check errors are pre-existing
  in src/frob/vet/_capability.py and src/frob/vet/_supplychain.py,
  outside scope.
- git diff main --diff-filter=D --stat: empty (verified AFTER merging
  main -- main had advanced with T-1099's strata-core/src/parse.rs split
  since this worktree's prior merge; merging main again and rebuilding
  natives (make core) before this check was required to avoid a false
  deletion-filter trip against files this worktree's stale merge-base
  did not yet have).

Security-kind TEST016 mutant-killing check runs automatically at `frob
ticket land`/`frob ticket close` time (frob.gates._mutation_evidence);
no separate manual invocation needed.

Filed: none new by this ticket.

### Changed
```
 docs/modules/strata.md                | 28 +++++++++--
 src/frob/strata/_selfconform.py       | 94 ++++++++++++++++++-----------------
 tests/unit/strata/test_selfconform.py | 55 ++++++++++----------
 tickets.md                            | 12 ++++-
 4 files changed, 113 insertions(+), 76 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_fires_outside_src_frob_layout` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
