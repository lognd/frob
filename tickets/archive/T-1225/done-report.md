## Done report

Implemented all four PERF01x detectors named in the ticket, per the
established perf-findings-become-lint-rules pattern (detector function +
registry/obligation entry, both layers):

  PERF010: yaml.safe_load/yaml.load without a C-accelerated loader
           (CSafeLoader/CLoader) in non-test code -- mined from
           src/frob/tickets/_store.py's pre-T-1206 shape.
  PERF011: a repo-scan API (xref/exports_consumers/iter_files) called
           inside a loop over symbols -- mined from
           src/frob/gates/_debt_deprecated.py's pre-T-1207 shape.
  PERF013: more than one ast.walk(tree) pass over the SAME tree argument
           within one function -- mined from
           src/frob/gates/_pii_structural/__init__.py's pre-T-1209 shape.
  PERF014: a re.finditer call reachable inside 3+ nested for/while loops
           (a pattern-list loop nested inside a per-line loop, with the
           innermost consuming loop's own "for" counted separately from
           the two genuinely nesting loops) -- mined from
           src/frob/gates/_secrets.py's pre-T-1211 shape.

(PERF012 was already taken by frob.perf._dup_spawn, T-0919 -- used
PERF010/011/013/014 to avoid collision, skipping 012.)

New module: src/frob/perf/_hotpath_smells.py, wired into perf_rules() (the
live dispatch surface frob check's PERF gate actually consumes -- verified
with a dedicated test, TestHotpathSmellsWiredIntoPerfRules, so a future
wiring regression cannot hide behind the standalone function's own tests
staying green). Exported from frob.perf's public surface
(hotpath_smell_violations) matching the precedent recursion_rules/
redundant_computation_violations already set.

Each rule is proven against a MINIMAL regression-corpus fixture
reproducing the exact pre-fix shape mined from the four named files
(tests/unit/perf/test_hotpath_smells.py), plus a negative case per rule
proving the corresponding FIXED shape stays silent. Confirmed against the
real repo: `frob check --only perf` (unscoped, over the whole tree)
reports 0 errors and no NEW PERF010/011/013/014 findings anywhere in this
already-fixed codebase -- the four detectors are silent against the code
they were mined to catch a regression of, exactly as intended.

Registry/obligation layer: added CHK-GATE-PERF010/011/013/014 entries to
docs/design/registry/check-coverage.yaml (bumped gate_rule_total 281->285)
and the four rule ids to src/frob/gates/_waive.py's hand-maintained
_KNOWN_GATE_RULES literal (PERF001-009's own precedent -- PERF0xx ids live
outside frob.gates._rule_id_scan's SCANNED_BASES auto-detection, per that
module's own docstring, so they are hand-added the same way PERF001-009
already are). Both files were outside T-1225's original declared scope
(src/frob/perf/**); widened via `frob ticket scope --add` with a recorded
reason for each, per the ticket's own acceptance criterion requiring "a
registry entry" for each new rule id.

Filed: T-1539 (PERF012 was ALREADY missing its own
CHK-GATE-PERF012 registry entry before this ticket started -- a
pre-existing gap this ticket's own registry work surfaced, not introduced
by it; filed as a separate bug rather than folded into this ticket's own
scope).

No .strata design file exists for perf-specific obligations (design/*.strata
has no PERF references at all, for PERF001-009 either) -- the
docs/design/registry/*.yaml CHK-GATE entries are this repo's actual
obligation-layer convention for gate rule ids, which is what was added.

Gates: frob check --only test --only archgate --only coverage --only sys
--only registry --only prework --only wire --ticket T-1225 clean (0
errors) after: a WIRE001 fix (rewrote the four checks' dispatch from a
tuple-iteration loop to explicit named calls so the reachability text-scan
can see them -- the tuple form was genuinely invisible to a call-shaped
text scan, not a gate false positive), 2 test-only-helper WIRE001 waivers
(same T-1490 precedent used in T-1350), a SELFAUDIT fix via `frob sys
sync-interface`, and a TEST001 fix (frob:tests directive on
hotpath_smell_violations).

### Changed
```
 tickets.md | 23 +++++++++++++++--------
 1 file changed, 15 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_fires_on_pre_fix_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_does_not_fire_on_fixed_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_does_not_fire_in_test_paths` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_fires_on_pre_fix_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_does_not_fire_when_scan_is_hoisted` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf013RepeatedAstWalk::test_fires_on_pre_fix_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf013RepeatedAstWalk::test_does_not_fire_on_shared_index` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf013RepeatedAstWalk::test_does_not_fire_on_two_different_trees` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop::test_fires_on_pre_fix_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop::test_does_not_fire_on_whole_text_single_pass` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestHotpathSmellsWiredIntoPerfRules::test_perf_rules_includes_perf010_finding` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf011SkipsNonFunctionSymbols::test_module_level_constant_produces_no_findings` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
