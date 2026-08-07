## Done report

Bucketed `frob check --only test` (post T-0583 merge) by rule against this
tree:

- TEST005/TEST012/TEST013/TEST015: 0 findings today. Not calibration debt --
  genuinely clean in this repo right now (TEST013's native-collector gap and
  TEST015's assertion-evidence gap simply have no matching symbols here).
  Extended T-0587's and T-0589's bodies with these counts so the next pass
  doesn't have to re-derive them; left both queued since their actual
  cross-cutting work (real vitest/ctest collectors, TEST001<->coverage
  wiring) is unaffected by there being 0 current findings.
- TEST014: 244 warnings, all pairwise fan-out from 4 distinct leaf-name
  collision groups (`run` x171 across 20 app/*_runner.py entrypoints,
  `as_json`/`as_text` x36 each, `format` x1) -- down from the 5 groups
  T-0588's own body describes (`main` no longer collides). None fixed this
  pass: disambiguating 20 runner modules' TEST001 credit is precisely
  T-0588's own declared scope (src/frob/gates/__init__.py) and outsized for
  a triage pass. Extended T-0588's body with the refreshed count/breakdown
  instead of duplicating the ticket.
- TEST003: 2 findings, both package-scoped interfaces with 0 integration
  tests. src/frob/doctor.py already carried an honest waiver (pre-existing
  T-0319 debt). src/frob/registry (genuinely no CLI/subprocess integration
  entrypoint, only unit-tested via its consuming gates) now carries the
  same honest waiver, disposed to 0 unwaived.
- TEST006: 1 finding ("no coverage stamp found; run: make coverage") --
  environmental noise in a fresh worktree per the agent playbook (6b: a
  dispatched sub-agent must not run `make coverage`; the coordinator stamps
  it at land). Not disposed here; expected to clear once the coordinator
  stamps coverage against the merged tree.

Net: gate:TEST is 0 errors both before and after this pass (244->245
warnings reflects only the TEST003 waiver's bookkeeping, not a new
finding). No detector calibration was needed -- no bucket showed dominant
noise requiring a rule-shape fix; T-0583 (COV006, a companion gate) is
where the actual detector fix in this mission landed.

### Changed
```
 src/frob/graph/callgraph.py | 27 +++++++++++++++++-
 tests/test_graph.py         | 25 ++++++++++++++++
 tests/test_lang.py          |  2 --
 tickets.md                  | 69 +++++++++++++++++++++++++++++++++++++++++++--
 4 files changed, 118 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_registry_models.py::TestParseDisposition::test_handled_by` (pytest node id, verified passing when recorded)
