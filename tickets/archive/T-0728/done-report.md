## Done report

T-0616 built the ARCH1xx SRP/cohesion family (check_lcom4/check_god_module/
check_mixed_concern_function, `frob.arch._srp`) but disclosed it as
invoked-by-nothing: no dispatch from `analyze_project`, no `[arch]`
frob.toml thresholds, no gate/waiver registration. This ticket wires all
three, without touching `_srp.py` itself (out of scope).

Changed:
- src/frob/arch/__init__.py: added `_run_srp_checks_python` (calls
  `PythonAdapter().adapt` to build a `NormalizedModule` for the current
  file, then `check_lcom4`/`check_god_module`/`check_mixed_concern_
  function` with thresholds threaded from `_Limits`), wired into
  `_run_python_checks` alongside the existing T-0617 OCP dispatch (same
  python-only-in-production posture as every other normalized-model check
  wired here today). `_Limits` and `analyze_project`'s signature both grew
  five new keyword thresholds (`lcom4_min_methods`,
  `lcom4_min_field_using_methods`, `god_module_min_exports`,
  `god_module_min_clusters`, `mixed_concern_min_decision_points`),
  defaulting to `_srp.py`'s own module constants.
- src/frob/app/config.py: `load_arch_config`'s `[arch]` frob.toml table now
  reads/defaults the same five keys (`ARCH_DEFAULT_LCOM4_MIN_METHODS` etc,
  all equal to `_srp.py`'s own defaults -- no separate calibration pass has
  been run on this repo's own SRP/cohesion numbers).
- src/frob/gates/_arch.py: `arch_gate` now channels `low-cohesion-class` /
  `god-module` / `mixed-concern-function` into `ARCH101`/`ARCH102`/
  `ARCH103` `Violation`s (via a category->rule dict), all at
  `Severity.WARN` matching the existing `ARCH001`/`long-function`
  precedent -- explicitly NOT wired to a `frob:enforces CHK-GATE-ARCH10x`
  directive, since docs/design/registry/check-coverage.yaml is out of this
  ticket's declared scope (disclosed below, per dispatch instructions --
  same posture T-0788's COMPLIANCE005 land left for its own registry row).
- src/frob/gates/__init__.py: registered ARCH101/ARCH102/ARCH103 in
  `_KNOWN_GATE_RULES` so `frob:waive ARCH10x reason="..."` is a real,
  non-ineffective directive (WAIVE002-checkable) and the rules show up in
  registry/waiver tooling.
- docs/modules/arch.md: added a "Wiring (T-0728)" paragraph to the SRP/
  cohesion checks section describing the new dispatch/gate/config wiring
  and its python-only-in-production scope, and five new
  `frob:describes`/config-table entries under the `[arch]` frob.toml
  section for the new keys.
- tests/unit/test_arch_srp.py: new `TestAnalyzeProjectWiring` (proves
  `analyze_project` itself, not just the bare check functions, produces
  ARCH101/102/103 findings over real parsed python fixture files),
  `TestArchGateSrpWiring` (proves `arch_gate` channels the same three into
  real `Violation`s with the right rule id, including a frob.toml-override
  fixture-fails-before/passes-after proof for ARCH101's threshold), and
  `TestArchConfigThresholds` (proves `load_arch_config` reads/defaults the
  five new keys).
- tests/unit/test_config.py (scope-added, minimal, reason on file):
  `test_reads_override` and `test_missing_toml_defaults` assert exact dict
  equality on `load_arch_config`'s return value; the five new SRP keys
  this ticket adds to that dict are a direct, unavoidable consequence of
  the in-scope config.py edit, so both assertions were extended to include
  the five new keys at their calibrated defaults (no behavior of the
  original five knobs changed).

Deviations / disclosures:
- docs/design/registry/check-coverage.yaml is untouched, per dispatch
  instructions -- the coordinator adds CHK-GATE-ARCH101/ARCH102/ARCH103
  rows (and bumps gate_rule_total) as a land obligation, mirroring T-0788's
  COMPLIANCE005 precedent (commit 49ac1a5d).
- Severity is WARN for all three new rules (matching ARCH001, not ERROR):
  the ticket's own acceptance criterion does not demand ERROR, and `frob.
  gates._arch`'s existing module docstring already carried that same
  design decision for ARCH001 -- T-0728 extends it rather than departing
  from it. Measured against main's own source (`analyze_project(Path("src"),
  **load_arch_config(Path(".")))` at calibrated defaults): 1
  low-cohesion-class, 21 god-module, 17 mixed-concern-function findings
  fire across this repo's own code today. Since all three channel at
  WARN (not ERROR), `frob check`'s exit code/gate-summary pass/fail is
  unaffected either way (`Severity`'s own docstring: "error fails frob
  check, warn does not") -- confirmed directly: `frob check --only
  gates-native --ticket T-0728` (which dispatches `gate:ARCH`) shows
  `pass gate:ARCH 0 errors, 57 warnings, 13 waived` (up from 42 warnings
  pre-change, all still 0 errors). No threshold tightening was needed to
  keep main green; this is disclosed rather than silently glossed over,
  per the dispatch's disclose-the-count instruction.
- `run_srp_checks` (T-0616's single-entry-point convenience wrapper) is
  left unchanged and unused by the new wiring -- `analyze_project` calls
  the three `check_*` functions individually instead, so each threshold
  can be threaded from `_Limits`/frob.toml independently; doc section
  updated to say so explicitly.
- Wiring is python-only in production (via `PythonAdapter`) -- the
  TypeScript/Rust/Kotlin adapters that already exist are not reached by
  `analyze_project`'s per-file dispatch for ANY normalized-model check
  today (T-0617's OCP family is the same way), so this is not a new gap
  introduced here, just not newly closed either.

Verification actually run:
- `uv run pytest tests/unit/test_arch_srp.py -p no:cacheprovider`: 23
  passed.
- `uv run pytest tests/unit/test_config.py tests/unit/test_arch.py
  tests/unit/test_arch_srp.py -p no:cacheprovider -q`: all green (no
  regressions in the two touched-adjacent suites).
- `uv run ruff check` / `ruff check` (both PATH and project-pinned) on
  every touched file: clean.
- `uv run ruff format --check` / `ruff format` (both): clean (one file
  needed a format pass, applied).
- `uv run ty check src/frob/arch/__init__.py src/frob/app/config.py
  src/frob/gates/_arch.py`: clean.
- `uv run frob check --only lint --ticket T-0728`: pass, 0 errors.
- `uv run frob check --only static --ticket T-0728`: pass, 0 errors (all
  `frob-exports` findings are pre-existing, unrelated to this ticket's
  scope).
- `uv run frob check --only gates-fast --ticket T-0728`: pass, 0 errors,
  1095 warnings, 158 waived (required a `frob ticket sweep T-0728` re-run
  after the tests/unit/test_config.py scope-add to clear a stale-PRE001
  transient).
- `uv run frob check --only gates-native --ticket T-0728`: pass, 0 errors
  (gate:ARCH 0 errors, 57 warnings, 13 waived).
- `uv run frob check --only gates-security --ticket T-0728`: pass, 0
  errors.
- `git diff main --diff-filter=D --stat`: empty.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring::test_two_cluster_class_fires_arch101` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring::test_cohesive_class_does_not_fire_arch101` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring::test_god_module_fires_arch102` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring::test_mixed_concern_function_fires_arch103` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_two_cluster_class_fires_arch101` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_cohesive_class_does_not_fire_arch101` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_god_module_fires_arch102` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_mixed_concern_function_fires_arch103` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_arch101_respects_explicit_frob_toml_override` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestArchConfigThresholds::test_reads_srp_overrides` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestArchConfigThresholds::test_srp_defaults_without_frob_toml` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 0 error(s), 1177 warning(s), 207 waived
