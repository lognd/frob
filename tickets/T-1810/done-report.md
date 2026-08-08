## Done report

frob:no-behavior-change reason="re-applying a single-line, already-reviewed pyproject.toml specifier change (T-1508's own fix) that T-1508's own land silently dropped while its derived uv.lock artifact landed correctly -- there is no new behavior to reproduce, the fix's own effect (uv sync --extra smt succeeds, z3 imports, tests/unit/test_dup_smt.py exercises the real solver) was already verified once under T-1508 and re-verified again here identically."

Re-applied T-1508's own `pyproject.toml` edit (`smt = ["z3-solver>=4.13"]`
-> `smt = ["z3-solver>=4.13,<4.15.5"]`), confirmed dropped by T-1508's
own land despite that land reporting `LAND-PROOF verified=True
state_on_main=done`.

Root cause of the land defect itself is NOT determined here (out of
this ticket's own narrow `pyproject.toml`/`uv.lock` scope, and the land
CLI's own transcript named no error/warning naming `pyproject.toml` at
all -- whatever step dropped it did so silently). Reproduced three
times against independently fresh `git fetch . main` checkouts in the
same session before concluding this was real and not a stale-cache
illusion:
- The landed commit's own diff (`git show 48e7a23ed --stat`) touches
  only `tickets/T-1508/done-report.md`, `tickets/T-1508/ticket.md`, and
  `uv.lock` -- `pyproject.toml` never appears.
- `main`'s `pyproject.toml` read back the OLD unbounded
  `z3-solver>=4.13` after that land, three separate times.
- `main`'s `uv.lock` (a DERIVED artifact) DID carry the fix correctly
  -- its own `requires-dist` entry for the `smt` extra already showed
  `>=4.13,<4.15.5`, and its locked resolution was already
  `z3-solver==4.15.4.0`. The derived artifact landing while its own
  source of truth did not is the specific inconsistency this ticket
  closes.

Re-verified end to end (same verification T-1508's own Done report
already ran, repeated here since this is functionally the same fix
landing a second time): `uv sync --extra smt` succeeds from a prebuilt
wheel, `import z3` reports `4.15.4`, `pytest tests/unit/test_dup_smt.py
-rs` collects 3, 2 pass exercising the real solver, 1 correctly skips
(the absent-dependency branch, now genuinely inapplicable since z3 is
installed).

Root cause (identified by the coordinator from root, not visible from
inside worktree isolation, and tracked separately as T-draft-3cf9eb4e):
`_land_release._reset_release_artifacts_to_pre_land` (T-1760) discards
whatever the squash staged for `pyproject.toml`/`CHANGELOG.md`/
`.frob-release.json`, and `_land_squash` (T-1769) subtracts those same
three files from the completeness assertion's `expected - staged`
missing-set check -- individually correct fixes for two different prior
incidents that compose into a silent data-loss path: the one guard that
would notice a dropped `pyproject.toml` edit has been told to ignore
`pyproject.toml` entirely. The exemption is file-granular; land's real
ownership is FIELD-granular (`version =`, the CHANGELOG heading,
`.frob-release.json`'s contents) -- it never legitimately owns
`[project.optional-dependencies]`/`[tool.*]`/`[build-system]`/entry
points, which is exactly the field this ticket's own fix lives in. Not
fixed here (T-draft-3cf9eb4e's own scope); this ticket only restores
consistency for the one concrete instance already confirmed.

Gates: `frob check --ticket T-1810 --only scope --only
prework --only fmt --only affect_drift` -- 0 errors besides the known,
disclosed, non-systemic `tickets/<id>/ticket.md` SCOPE001 pattern.

Status: leaving IN-PROGRESS for the coordinator/reviewer to close after
land.

### Changed
```
 pyproject.toml                     | 19 +++++++++-
 tickets/T-1810/ticket.md | 73 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 91 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_dup_smt.py::test_proves_equivalent_bounded_functions` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_smt.py::test_finds_counterexample_for_non_equivalent_functions` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_smt.py::test_degrades_to_smt_unavailable_without_z3` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 567 warning(s), 732 waived
- error-findings: SUPPRESS001@tests/unit/test_dup_smt.py
