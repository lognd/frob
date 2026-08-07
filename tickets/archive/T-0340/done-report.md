## Done report

Mechanism chosen: (c) a Makefile guard, not a uv/pyproject declaration
change. `uv sync` (the `$(STAMP)` rule) reconciles the venv against ONLY
its own declared dependency set; the maturin-develop editable installs of
`strata_core`/`frob_core` cannot be declared there as a real
`[project.optional-dependencies]` extra (T-0133's Done report already
established why -- no published wheel, and a local relative-path extra
breaks for anyone installing outside this exact checkout), so option (a)
(a uv/pyproject setting that stops uv evicting them) is not available
without re-litigating that prior decision, which is out of this ticket's
scope. Option (b) (a shared CARGO_TARGET_DIR/wheel cache across worktrees)
remains investigated-not-built, same disposition T-0175 already recorded
-- restated in docs/guides/install.md's new section rather than
re-attempted here.

Implemented: `core` is `.PHONY`, so any target listing it as a
prerequisite re-runs `maturin develop` (a true no-op when nothing changed)
before that target's own recipe body executes. Every target whose recipe
actually needs the natives at runtime now depends on `core` instead of
the bare `$(STAMP)` sync-stamp target: `check`, `all`, `test`,
`test-fast`, `test-unit`, `test-integration`, `test-system`. (`install`
already depended on `core`; `coverage`/`coverage-fast` already called
`$(MAKE) core` explicitly inside their recipe bodies per T-0538 and were
left as-is, not touched, since they already self-heal and have their own
fail-loud `frob doctor` step baked in.) `format`/`lint-fix` (pure ruff, no
native import) were deliberately left on the bare `$(STAMP)` since they
never need the natives.

Measured rebuild cost: 14.582s real (cold, no cargo target-dir cache --
first `make core` in this fresh worktree) vs 0.613s real (warm cache,
identical `make core` re-run with nothing changed) -- i.e. the
always-run-`core` guard costs ~0.6s per invocation in the steady state,
not a repeated full compile.

Verification (simulated the actual failure mode): ran `touch
pyproject.toml && uv sync --extra serve` directly, confirmed via `uv run
python -c "import strata_core"` that this evicts the native (raises
`ModuleNotFoundError: No module named 'strata_core'`), then ran `make
test-unit` (one of the newly-`core`-gated targets) and confirmed (a) the
natives were silently rebuilt/reinstalled before pytest collected/ran (no
ModuleNotFoundError anywhere in output, ~12s wall including the ~0.6s
`core` re-run) and (b) a follow-up `uv run python -c "import strata_core,
frob_core"` succeeded, resolving to the venv's site-packages, proving the
Makefile guard restored what `uv sync` had just evicted, with zero manual
`make core` step required. The 3 test failures observed in that run
(`test_extending_guides_complete.py` x2,
`test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant`)
are pre-existing, unrelated to natives (SYS102 "unmodeled code"
src/frob/fleet, src/frob/registry -- a documented pre-existing gap class
per tickets-archive.md precedent, e.g. the T-0257 Done report describing
the identical failure shape for a different untracked directory), not a
regression introduced here.

Documented in docs/guides/install.md, a new section "`uv sync` evicts the
natives -- why every entrypoint self-heals (T-0340)" right after the
existing "Editable dev install" section: explains the eviction mechanism,
why (a)/uv.lock declaration is not available (cross-referencing the
existing "Why not pip install frob[strata]" section), the `.PHONY`
re-run-on-every-prerequisite mechanism and which targets were changed
vs deliberately left alone, the measured cost, and that cross-worktree
cargo-cache sharing (b) remains a separate not-yet-built follow-up per
T-0175's Done report.

### Changed
```
 Makefile               |  44 +++++++++++++++++----
 docs/guides/install.md |  44 +++++++++++++++++++++
 tickets.md             | 102 ++++++++++++++++++++++++++++++++++++++++++++++++-
 3 files changed, 181 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_reports_healthy_when_natives_present` (pytest node id, verified passing when recorded)
