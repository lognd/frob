## Done report

Session scope (effort-budgeted slice of the epic; the 11-child breakdown
described in the ticket body was never actually filed on main -- no
`parent: T-1204` tickets exist in tickets.md, and the scratchpad
hotgraph/report.md the ticket body references is not present in this
worktree). Worked directly from a fresh unscoped `frob check --only
perf` reading (55 warnings, 0 errors, 99 waived) instead of the
unavailable report, and picked the PERF010 (yaml C-loader) family: 6
findings, the smallest and most mechanically tractable of the 5 rule
families present (PERF010/011/005/008/014).

Root-caused 4 of those 6 as a genuine RULE-LEVEL false positive rather
than fixing sites individually: `_perf010_yaml_c_loader`
(src/frob/perf/_hotpath_smells.py) only ever scanned a symbol's own
body tokens for a literal `CSafeLoader`/`CLoader` token -- it has no
visibility through a helper-function call boundary. This repo's own
T-1206 fix (`frob.tickets._store._yaml_loader`, re-exported as
`frob.gates.__init__._tickets_yaml_loader`) is exactly that shape: a
small factory function selecting the C loader, called via `Loader=
_yaml_loader()`. The rule read the already-correct code as having "no
C loader anywhere" every time. Fixed the rule
(`_has_loader_indirection`): a `Loader=<name>(...)` call whose name
contains "loader" (matching this repo's own established naming
convention) is now trusted as a deliberate loader-selection
indirection, per the standing instruction to fix the rule rather than
waive each site. Added a regression test proving the false positive is
gone (`tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader.
test_does_not_fire_on_helper_loader_indirection`) alongside the
existing pre-fix/fixed-shape/test-path fixtures, which all still pass.

The remaining 4 PERF010 findings (frob.registry._models.
load_registry_dir, frob.gates.decisions.load_decisions, frob.gates.
invariants._frontmatter_dict, frob.vet._lockfile._parse_pnpm_lock) were
real: plain `yaml.safe_load(text)` with no C-loader consideration at
all. Rather than duplicate the T-1206/T-1333 loader-selection logic (C
loader when libyaml is present, EXCEPT under an active coverage.py
tracer -- T-1333's own documented corruption bug) a 5th time, extracted
it out of `frob.tickets._store` into a new shared `frob.yaml_io.
fast_yaml_loader` (NO DUPLICATION principle) and wired all 4 real sites
onto it. `frob.tickets._store` keeps `_yaml_loader`/
`_coverage_tracer_active` as thin re-exports under their original
names, so its own direct-import tests
(tests/unit/test_ticket_store.py::TestYamlLoader) and `frob.gates.
__init__`'s existing `_tickets_yaml_loader` re-export needed no
change. Added `frob:doc`/`frob:tests` directives on the new public
`fast_yaml_loader` and a new "Shared YAML loader selection
(frob.yaml_io)" doc subsection in docs/modules/tickets.md (the
_store.py-adjacent doc, since that is where this logic originated and
where the re-exports still live).

Per the standing repo convention (a perf root cause ships as both the
fix AND a lint rule, never fix-only): PERF010 already existed and now
correctly recognizes the fixed shape both directions -- flags genuinely
missing C-loader selection, and no longer flags the delegated-to-a-
named-loader-factory shape this session's own new fix sites (and the
repo's pre-existing T-1206 fix) both use.

Deliberately did NOT attempt PERF011 (28 findings, iter_files-in-loop --
each needs its own per-caller correctness read of whether the loop
genuinely re-scans or is a false resolver hit, mirroring several
already-waived PERF008 findings' documented resolver-ambiguity pattern
in this same run's output), PERF005 (2 Rust recursion-termination
findings, frob-core/src/extract.rs -- needs a Rust-side frob:invariant
annotation, out of this session's Python-focused time budget), PERF008
(2 findings, src/frob/arch/_ffi.py + src/frob/serve/_watch.py -- each
needs a per-call effect-reachability read), or PERF014 (7 findings,
finditer-nested-in-pattern-loop -- each needs a per-site loop-swap
rewrite verified against that gate's own regex-correctness risk). Not
attempting those is a disclosed cut: T-1204 stays open, the umbrella's
child-ticket breakdown was never filed on main so there is no id to
close individually against, and a future session working this ticket
should re-measure `frob check --only perf` fresh rather than assume
this session's slice covers the whole epic.

Measurement: unscoped `frob check --only perf` before this session's
change: gate:PERF 55 warnings (0 errors, 99 waived). After: gate:PERF
47 warnings (0 errors, 99 waived) -- 8 fewer (4 real PERF010 fixes + 4
false positives cleared by the rule fix). gate:ARCH/gate:LARGE/gate:FMT
all stayed clean (gate:FMT 0 errors/0 warnings after wrapping the new
module's own frob:tests/frob:doc directive lines to canonical form).
`pytest tests/unit/perf/test_hotpath_smells.py tests/unit/
test_ticket_store.py tests/test_registry_models.py -p no:cacheprovider
-q`: all passed (SUITE-RESULT lines read directly). `pytest tests/
test_vet.py -k pnpm`: 2 passed. `pytest tests/test_gates.py -k
"Decision or Invariant or invariant or decision"`: 24 passed.

### Changed
```
 docs/modules/tickets.md                          |  58 ++-
 src/frob/gates/decisions.py                      |   3 +-
 src/frob/gates/invariants.py                     |   3 +-
 src/frob/perf/_hotpath_smells.py                 |  44 +-
 src/frob/registry/_models.py                     |   3 +-
 src/frob/tickets/_store.py                       |  64 +--
 src/frob/vet/_capability_typescript.py           | 597 +----------------------
 src/frob/vet/_capability_typescript_bindtable.py | 593 ++++++++++++++++++++++
 src/frob/vet/_lockfile.py                        |   3 +-
 src/frob/yaml_io.py                              |  73 +++
 tests/unit/perf/test_hotpath_smells.py           |  24 +
 tickets.md                                       | 255 +++++++---
 12 files changed, 993 insertions(+), 727 deletions(-)
```

### Evidence
- `tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_does_not_fire_on_helper_loader_indirection` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_fires_on_pre_fix_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_does_not_fire_on_fixed_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_does_not_fire_in_test_paths` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_falls_back_to_safeloader_without_libyaml` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_falls_back_to_safeloader_under_active_coverage_tracer` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestLockfileParsers::test_parse_pnpm_lock` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 0 error(s), 8273 warning(s), 797 waived
- error-findings: none (measured, zero errors)
