## Done report

docs/audits/gates-accounting.md B6/E6: `_inferred_unit_cases` matches a
public symbol to a collected test by snake-cased leaf name alone, no
module/path binding. Repro: two `def parse()` in different files, one
`test_parse` -> both clear TEST001 even though it only exercises one.

Compat survey done FIRST (required per the ticket, "too large for the
T-0403 sweep budget" note), measured against this repo's own graph:
- 81 public, non-test symbols currently rely purely on the naming-
  convention fallback (no explicit `frob:tests` edge).
- A blanket "test file must share a top-level directory with the
  symbol's file" tightening breaks ALL 81 of them (0 survive) -- this
  repo's `tests/` tree (flat + `unit/`/`system/`/`integration/`
  subdirs) does not mirror `src/frob/<pkg>/` layout closely enough for
  that correlation to be sound as a default tightening. Confirms the
  ticket's own risk note.
- Narrowing the search to the ACTUAL B6 shape -- two or more DIFFERENT
  files' same-leaf-name public symbols, both relying only on the
  convention fallback, credited by at least one of the SAME collected
  test node ids -- found 5 real collision groups in this repo today:
  `main`, `format`, `as_text`, `as_json`, `run` (e.g.
  `src/frob/__main__.py::main` and `src/frob/perf/_harness.py::main`
  both credited by `tests/integration/test_interfaces.py::...
  test_main_cli_dispatches`).

Landed (sound, zero-regression): TEST014 (WARN), a new gate that makes
this exact ambiguity loud and auditable without changing what TEST001
credits -- mirroring TEST013's restraint (T-0552) for the identical
reason: withdrawing credit from all 5 collision groups outright, with no
verified per-case remedy, would ERROR-red real symbols across the repo
for a structural change alone, and the survey shows a blanket
module-correlation rule is unsound here. `_test014_ambiguous_convention`
groups convention-only-matched symbols by snake-cased leaf name, and for
every pair spanning 2+ distinct files that share a matched test node id,
emits one WARN naming both symbols and the shared test.

Split off (real fix + judgment call): T-draft-b7c57519 ("Resolve TEST014
name-collision cases: disambiguate or tighten TEST001 credit") -- to
actually resolve the 5 found collisions (explicit `frob:tests` edges or
renames) and design/validate a general tightening rule now that real
positive/negative examples exist to test it against.

### Changed
```
 CHANGELOG.md                |  19 ++++
 frob.lock                   |   2 +-
 pyproject.toml              |   2 +-
 src/frob/gates/__init__.py  | 159 ++++++++++++++++++++++++++--
 src/frob/gates/_coverage.py | 125 +++++++++++++++++++++-
 tests/test_gates.py         | 177 +++++++++++++++++++++++++++++++-
 tickets.md                  | 245 ++++++++++++++++++++++++++++++++++++++++++--
 uv.lock                     |   2 +-
 8 files changed, 708 insertions(+), 23 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_fires_on_cross_file_same_test_collision` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_silent_when_symbol_has_explicit_edge` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_silent_when_no_leaf_name_collision` (pytest node id, verified passing when recorded)
