## Done report

T-1576: frob scaffold defaults new repos to profile=rapid.

Changed:
- src/frob/scaffold/data/{shared/python,shared/cpp,types/pyo3-library,
  types/pybind11-library,types/python-tool,types/web-app}/frob.toml.j2:
  each now writes [profile]\nprofile = "rapid" right after the existing
  check_base = "main" line, with a short comment pointing at
  docs/modules/tickets.md's profiles section. These 6 templates cover
  all 7 registered project types (cpp-library and cpp-tool share
  shared/cpp/frob.toml.j2).
- tests/unit/test_scaffold_project.py: new
  test_render_project_all_types_default_to_rapid_profile, looping every
  frob.scaffold.project.list_project_types() entry and asserting its
  rendered frob.toml contains [profile] / profile = "rapid".
- docs/modules/tickets.md: added a short "frob scaffold defaults new
  repos to rapid (T-1576)" paragraph to the existing Development
  profiles section, explicitly noting existing repos are unaffected
  (absent [profile] key still means standard, per configured_profile's
  own documented default -- unchanged by this ticket).

Note: T-1576's ticket-filed scope (src/frob/app/**,
src/frob/_cli_parsers/**, docs/**, tests/**) did not include
src/frob/scaffold/**, where the actual frob.toml.j2 templates live --
added via `frob ticket scope T-1576 --add
"src/frob/scaffold/data/**/frob.toml.j2"` before editing.

Evidence: 1 pytest node id bound via the ticket evidence CLI, observed
passing (12 passed total in the file, including this one) under a
targeted pytest run of tests/unit/test_scaffold_project.py.

Gates: a repo-wide (not --ticket-scoped) run of invariant/prework/wire/
test/coverage stage groups shows zero findings naming any scaffold
template or the new test -- only cosmetic "no grammar registered for
extension '.j2'" WARNING lines (expected, .j2 is not a recognized
source language) and pre-existing, already-waived findings elsewhere.

Filed: none -- no new out-of-scope work discovered (the scope gap was
closed via `frob ticket scope --add`, not a new ticket).

### Changed
```
 docs/modules/tickets.md                            | 147 +++++++-
 src/frob/_cli_parsers/_ticket/_progress.py         |  18 +
 src/frob/app/_config_external.py                   |   2 +
 src/frob/app/config.py                             |   6 +
 src/frob/app/ticket_runner/_land_cmd.py            |  78 +++-
 src/frob/scaffold/data/shared/cpp/frob.toml.j2     |   8 +
 src/frob/scaffold/data/shared/python/frob.toml.j2  |   8 +
 .../data/types/pybind11-library/frob.toml.j2       |   8 +
 .../scaffold/data/types/pyo3-library/frob.toml.j2  |   8 +
 .../scaffold/data/types/python-tool/frob.toml.j2   |   8 +
 src/frob/scaffold/data/types/web-app/frob.toml.j2  |   8 +
 src/frob/tickets/_land.py                          | 101 ++++--
 src/frob/tickets/_mutation_sweep_queue.py          | 399 +++++++++++++++++++++
 src/frob/tickets/_profile.py                       | 354 ++++++++++++++++++
 tests/unit/test_mutation_sweep_queue.py            | 179 +++++++++
 tests/unit/test_profile.py                         | 123 +++++++
 tests/unit/test_scaffold_project.py                |  19 +
 tickets.md                                         | 342 +++++++++++++++++-
 18 files changed, 1777 insertions(+), 39 deletions(-)
```

### Evidence
- `tests/unit/test_scaffold_project.py::test_render_project_all_types_default_to_rapid_profile` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 7891 warning(s), 787 waived
- error-findings: none (measured, zero errors)
