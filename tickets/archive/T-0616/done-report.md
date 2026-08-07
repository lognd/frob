## Done report

New `src/frob/arch/_srp.py` (EPIC T-0329's ARCH1xx SRP/cohesion family)
implements all three checks from the plan, each written ONCE against
`frob.arch._normalized.NormalizedModule` (T-0609) so it fires identically
across every `LanguageAdapter` that exists (python/TypeScript/Rust/Kotlin)
with no per-language branch in the check itself:

- **ARCH101 `low-cohesion-class` (`check_lcom4`)**: builds a connectivity
  graph over each class's field-using methods (an edge when two methods
  share a `self.<field>` name), computed via a plain union-find, and flags
  classes whose methods partition into 2+ disjoint components. Thresholds
  (`LCOM4_MIN_METHODS=6`, `LCOM4_MIN_FIELD_USING_METHODS=4`) are keyword
  args with calibrated defaults.
- **ARCH102 `god-module` (`check_god_module`)**: clusters a module's
  top-level exports (free functions + classes) by BOTH a naming-prefix
  union (first `_`-token / leading capitalized run) AND a usage union
  (an edge when one export calls another by name), so two exports that
  call each other are never split into different clusters regardless of
  naming, and vice versa. Flags modules with `GOD_MODULE_MIN_EXPORTS=10`+
  exports splitting into `GOD_MODULE_MIN_CLUSTERS=3`+ clusters.
- **ARCH103 `mixed-concern-function` (`check_mixed_concern_function`)**:
  requires ALL THREE of an I/O-capability call (by callee-name proxy: I/O
  builtins, well-known I/O-surface module prefixes, or stream-verb method
  suffixes), a string-formatting call (`str`/`repr`, `.format`/`.join`),
  and >=2 of the function's own decision points (branches/loops) --
  STRONG-HALLMARK-ONLY, matching `frob.arch._patterns`'s existing posture.
  `severity="suggestion"` (softer than the other two's `"warning"`, since
  it is a heuristic name-based proxy).

`run_srp_checks(module) -> list[ArchSuggestion]` runs all three and is the
single entry point a future orchestration-wiring ticket will call per
parsed file.

**Scope discipline / out of scope, disclosed:** wiring these checks into
`analyze_project`'s per-file dispatch (`src/frob/arch/__init__.py`) and
threading the thresholds through `frob.toml`'s `[arch]` table
(`src/frob/app/config.py`) is NOT done here -- neither file is in this
ticket's declared scope (nor was `_python.py`'s existing `PythonAdapter`/
`TypeScriptAdapter`/etc. wired into anything beyond their own module
either, going by T-0610-0614's precedent). Every threshold is a plain
keyword argument with a calibrated module-level default, ready for that
follow-up wiring. New ARCH ids also required adding three categories to
`ArchCategory` (`src/frob/arch/_models.py`) -- in scope, done.

**Coordination (T-0615/T-0617 concurrently touch `tests/unit/test_arch.py`):**
per dispatch instructions, scope-added `src/frob/arch/_srp.py` (replacing
the originally-declared `_solid.py`, since the coordination directed the
final module name) and `tests/unit/test_arch_srp.py`, and did NOT touch
`tests/unit/test_arch.py` at all -- verified unchanged-green
(`uv run pytest tests/unit/test_arch.py`, 101 passed) alongside the new
suite.

**Cross-language proof** (T-0616's coordination requirement): `TestCross
Language` in `tests/unit/test_arch_srp.py` builds a real `NormalizedModule`
via `TypeScriptAdapter().adapt(...)` (from a hand-written `.ts` source
string parsed through `raw_tree`, mirroring `TestTypeScriptAdapter`'s
existing pattern in `test_arch.py`) and proves `check_lcom4` fires/does-
not-fire on it identically to the hand-built-`NormalizedModule` python
unit tests, with zero language-specific code in `_srp.py` itself.

**Test/gate numbers actually observed:**
- `uv run pytest tests/unit/test_arch_srp.py -p no:cacheprovider -q`:
  12 passed.
- `uv run pytest tests/unit/test_arch.py -p no:cacheprovider -q`:
  101 passed (unchanged, confirms no collision with T-0615/T-0617).
- `uv run ruff check` / `ruff check` (both PATH and project-pinned) on
  the three touched files: clean.
- `uv run ruff format` (initially reformatted `tests/unit/test_arch_srp.py`
  for line-length; applied, then clean).
- `uv run ty check src/frob/arch/_srp.py`: clean.
- `uv run frob check --ticket T-0616`: every gate `pass` except `gate:REL`
  (REL001, public-API version bump) -- per docs/guides/agent-playbook.md
  and prior land-workflow precedent (T-0699's Done report in this same
  ledger), `pyproject.toml`/`.frob-release.json`/`CHANGELOG.md` are
  outside this ticket's declared scope, so the version bump is the
  coordinator's job at land time, not addressed here.
- `git diff main --diff-filter=D --stat`: empty (no unintended deletions).

Filed: none -- no out-of-scope work discovered beyond the deferred
`analyze_project`/`frob.toml` wiring already disclosed above (which
mirrors the existing pattern for T-0609-0615's adapters, not a new gap).

### Changed
```
 docs/modules/arch.md        |  78 ++++++++
 src/frob/arch/_models.py    |   7 +
 src/frob/arch/_srp.py       | 431 ++++++++++++++++++++++++++++++++++++++++++++
 tests/unit/test_arch_srp.py | 329 +++++++++++++++++++++++++++++++++
 4 files changed, 845 insertions(+)
```

### Evidence
- `tests/unit/test_arch_srp.py::TestLcom4::test_disjoint_field_groups_trigger_lcom4` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestLcom4::test_shared_fields_do_not_trigger_lcom4` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestGodModule::test_unrelated_export_clusters_trigger_god_module` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestGodModule::test_related_exports_do_not_trigger_god_module` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestMixedConcernFunction::test_io_compute_and_formatting_together_trigger` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestMixedConcernFunction::test_single_concern_does_not_trigger` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestRunSrpChecks::test_combines_all_three_checks` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestCrossLanguage::test_lcom4_fires_on_typescript_adapter_output` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_srp.py::TestCrossLanguage::test_lcom4_does_not_fire_on_cohesive_typescript_class` (pytest node id, verified passing when recorded)
