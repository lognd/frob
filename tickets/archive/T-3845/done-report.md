## Done report

Changed:
pyproject.toml::project.dependencies (frob-core, strata-core added, hard-pinned ==0.530.0)
pyproject.toml::project.optional-dependencies.native (kept, unchanged pins, comment updated)
pyproject.toml::tool.uv.sources (comment updated, mechanism unchanged)
docs/guides/install.md (rewritten install/degrade sections; historical sections marked resolved)

Pin decision: (c), with a hard == pin (not a floor pin). frob-core/strata-core
are now plain default dependencies AND still listed in the native extra
(kept only so VERSION001's exact-pin check and frob doctor's remediation
text, both outside this ticket's scope, keep working unchanged). Measured
release.yml's upload job before deciding: its three publish steps
(frob-core, strata-core, frob) run as separate steps in ONE job with no
continue-on-error set anywhere, so GitHub Actions' default step-abort-on-
failure applies -- a failed frob-core or strata-core publish stops the job
before the frob publish step ever runs. A reversed partial (frob published,
a core missing) cannot happen given that real behavior, which is what makes
a hard == pin safe: the worst case is cores published with frob's own
publish step failing, which leaves the previous frob release still
installable and simply does not ship the version bump yet -- nothing
regresses. A floor >= pin was rejected: these are ABI-coupled PyO3
extensions cut together at release time (T-2884's exact lesson), so a loose
pin invites unreproducible skew for no upside given the ordering guarantee.

T-0133 degrade path verified to survive: ran
tests/system/test_cli_native_missing.py (3 tests, real subprocess CLI,
PYTHONPATH-shadowed strata_core) -- all pass. A repo using .strata still
fails loudly (SYS004/NativeExtensionUnavailable) with natives absent; a
repo with no design/ dir is unaffected. Also ran frob doctor in the
worktree venv: reports "all native extensions available" with the new
defaults installed, so its native-extension reporting is unchanged and
accurate.

Path-source leak checked: built a wheel with uv build --wheel and inspected
its METADATA directly -- Requires-Dist carries only
frob-core==0.530.0 / strata-core==0.530.0 with no path information; the
tool.uv.sources path override is confirmed local-dev-only and does not
reach a consumer resolving frob from the index.

Side effect discovered and documented in install.md (not fixed under this
ticket, out of its Makefile-touching scope): making the cores real
lock-tracked dependencies means uv sync no longer evicts them from this
checkout's venv, which was the entire reason for T-0340's core-as-Makefile-
prerequisite self-heal machinery. Filed a follow-up ticket to re-verify
that across a fresh worktree/CI and simplify the Makefile if it holds.

Evidence: tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_fails_loud_with_sys004_when_strata_present
Filed: T-3850 (re-verify and simplify the Makefile core-prerequisite self-heal now that natives are lock-tracked deps).
Gates: frob check --ticket T-3845 clean except: gate:DOC (6 pre-existing errors, all in other tickets' bodies -- T-3807, T-3853, T-3855 -- none touch this ticket's scope, confirmed unrelated by content); gate:SCOPE SCOPE001 on uv.lock is a transient dev-sync artifact (uv run's own dependency resolution regenerates uv.lock locally; it is never committed here -- uv.lock is land-owned per T-0731's pre-commit hook and this worktree's actual commit touches only pyproject.toml and docs/guides/install.md, confirmed by git diff --stat main). ruff-format's repo-wide 6-file drift is pre-existing and untouched by this ticket (no .py files in this diff, confirmed by git diff --stat main -- '*.py' returning empty).

### Changed
```
 docs/guides/install.md   | 218 +++++++++++++++++++++++++----------------------
 pyproject.toml           |  87 +++++++++++++------
 tickets/T-3845/ticket.md |   2 +
 3 files changed, 181 insertions(+), 126 deletions(-)
```

### Evidence
- `tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_fails_loud_with_sys004_when_strata_present` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 4372 warning(s), 923 waived
- error-findings: DOC006@tickets/T-3807/ticket.md
