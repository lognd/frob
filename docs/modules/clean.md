# frob.clean -- tiered, artifact-only workspace cleanup (T-0457)

One sentence: `frob clean` removes ONLY known build/test/cache artifacts --
never source, never a git-tracked file -- previewing what it would remove
by default and executing only with `-y`/`--yes`.

<!-- frob:invariant INV-008 -->

<!-- frob:describes src/frob/clean/_core.py::clean -->
```bash
frob clean               # tier 1 (SAFE): preview only, prints candidates
frob clean -y            # tier 1: execute
frob clean --all -y      # tier 2: + rebuildable build/test/lint artifacts
frob clean --deep -y     # tier 3: + frob's own .frob/ caches, FROBLEMS.md
frob clean --json        # machine-readable report, either tier
```

## Tiers

- **`CleanTier.SAFE`** (`frob clean`): fragments that are DEFINITELY never
  reused -- `.coverage.<host>.<pid>.*` parallel-run fragments, every
  `__pycache__` directory and stray `.pyc`, `.pytest_cache`, and stray
  `.playwright-mcp` session dumps. Safe enough to run unattended; `make
  coverage` runs it as a post-step so `.coverage.*` fragments never
  accumulate again (the concrete pain that motivated this ticket).
- **`CleanTier.ALL`** (`frob clean --all`): tier 1 plus rebuildable build/
  test/lint output -- `build/`, `dist/`, `*.egg-info/`, each crate's
  `target/`, `cmake-build-*/`, `.ruff_cache`, `.mypy_cache`, `htmlcov/`,
  `coverage.xml`, the combined `.coverage`. Everything here regenerates
  from a normal build/test run. `make clean` runs this tier.
- **`CleanTier.DEEP`** (`frob clean --deep`): tier 2 plus frob's own state
  -- `.frob/` (graph cache, prework sweeps, journal, pytest collection
  cache) and `FROBLEMS.md`. The "reset to a clean checkout" button. If this
  drops a native-extension build fingerprint, run `make core` afterward.

Every tier is a strict superset of the tier before it.

## Fail-safe design

`scan` only ever walks a KNOWN allowlist of glob patterns
(`frob.clean._rules.tier_patterns`, extensible per-project via
`frob.toml`'s `[clean]` table -- `extra_patterns = [...]`); it never
enumerates "everything untracked" and filters down. A matched candidate
that is git-tracked is skipped and surfaced in the report's
`skipped_tracked`, never removed. `clean(..., dry_run=False)` only ever
removes entries `scan` already reported -- there is no separate, broader
deletion path. A test (`tests/test_clean.py::test_clean_never_touches_src`)
asserts `git diff --stat` over `src/` is empty after running every tier,
and that a non-artifact untracked file survives all three.

`frob clean` never shells out to `git clean` -- that would remove untracked
SOURCE too, which is exactly what this command must never do.

## Public API

<!-- frob:describes src/frob/clean/_models.py::CleanTier -->
<!-- frob:describes src/frob/clean/_models.py::CleanError -->
<!-- frob:describes src/frob/clean/_models.py::ArtifactEntry -->
<!-- frob:describes src/frob/clean/_models.py::CleanReport -->
<!-- frob:describes src/frob/clean/_rules.py::tier_patterns -->
<!-- frob:describes src/frob/clean/_rules.py::extra_patterns_from_config -->
<!-- frob:describes src/frob/clean/_core.py::scan -->
<!-- frob:describes src/frob/clean/_core.py::clean -->
<!-- frob:describes src/frob/app/clean_runner.py::run -->

```python
class CleanTier(enum.IntEnum)     # SAFE=1, ALL=2, DEEP=3 -- each cumulative
class CleanError(ErrorSet)        # NotARepo, RemoveFailed
class ArtifactEntry(BaseModel)    # one matched candidate: path, tier, rule, size, is_dir
class CleanReport(BaseModel)      # entries removed/previewed + skipped_tracked, reclaimed_bytes/count properties

def tier_patterns(tier) -> tuple[str, ...]
def extra_patterns_from_config(root) -> tuple[str, ...]
def scan(root, tier, *, extra_patterns=()) -> Result[CleanReport, CleanError]
def clean(root, tier, *, dry_run=True, extra_patterns=()) -> Result[CleanReport, CleanError]
```

`frob.app.clean_runner.run(cfg)` is the CLI entry point: resolves the tier
from `--all`/`--deep`, calls `clean(..., dry_run=not cfg.clean_yes)`, and
renders the report through `frob.render.Renderer` (or a bare JSON dump for
`--json`).

## Relates

- T-0456 (`frob ticket reconcile`): removes abandoned WORKTREES specifically; a
  future integration lets reconcile call `frob clean` for the artifact half
  of its own cleanup, kept as a distinct command here.
- T-0464 (coverage combine setup): the `.coverage.<host>.<pid>.*` fragment
  pattern this ticket's tier 1 targets is a direct consequence of that
  ticket's `COVERAGE_PROCESS_START` parallel-coverage setup.
