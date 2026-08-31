## Done report

Built cross-file entity/architecture resolution: strata_core.parse_source
(grammar_core.rs::parse_architecture) no longer hard-fails SYS300 when an
architecture's `of ENTITY` name is absent from its own file -- it emits
the architecture with entity_resolved: false instead (SYS302's ceiling
check is skipped there too, since the ceiling is unknowable locally).
src/frob/strata/_design_load.py's new cross-file pass
(_resolve_cross_file_architectures, built on _build_entity_registry and
_check_one_architecture) builds one global entity registry from every
loaded design file, then resolves each unresolved architecture against
it: SYS300 if the entity is declared nowhere at all, SYS302 re-checked
against the now-known ceiling, and a new ambiguous-duplicate-entity-name
refusal (StrataError.DuplicateId) for the cross-file case that has no
single-file precedent. `binds MODULE` stays single-file, unchanged --
only entity resolution crosses files, per the ticket's own scope.
_parse_one_design_file's signature was deliberately left unchanged
(frob.gates._coverage_sites calls it directly, outside this ticket's
scope) -- _raw_architecture_facts re-reads the file itself instead.
docs/strata/entity_architecture.md's Scope-of-this-first-slice section
and its SYS300-303 table are updated to describe the new same-file/
cross-file split; the stale frob:until T-3529 directive is removed.
Two existing tests needed updating to match the new parse_source
behavior (kept their original names/evidence bindings where an existing
ticket's evidence cited them): strata-core/src/parse/mod.rs's SYS300
must-fire fixture, and
tests/unit/test_lang_strata_entity_arch.py::TestEntityArchitectureFixtures::test_architecture_referencing_undeclared_entity_is_refused.
Filed: none.
Gates: `frob check --ticket T-3529 --skip-tests` clean for this ticket's
touched set (gate:SCOPE 0 errors; ty/ruff-check/gate:ARCH/gate:COV all
back to their pre-existing repo-wide baseline, verified none of the
remaining findings touch this ticket's files). 203 strata-core `cargo
test --lib` tests pass; 21 Python tests across test_design_load.py and
test_lang_strata_entity_arch.py pass.

### Changed
```
 docs/strata/entity_architecture.md         |  72 ++++----
 src/frob/strata/_design_load.py            | 269 +++++++++++++++++++++++++++--
 strata-core/src/parse/grammar_core.rs      |  94 +++++-----
 strata-core/src/parse/mod.rs               |  45 ++++-
 tests/unit/strata/test_design_load.py      | 128 ++++++++++++++
 tests/unit/test_lang_strata_entity_arch.py |  23 ++-
 tickets/T-3529/ticket.md                   |  31 +++-
 7 files changed, 554 insertions(+), 108 deletions(-)
```

### Evidence
- `tests/unit/strata/test_design_load.py::TestCrossFileArchitectureResolution::test_architecture_resolves_against_a_sibling_files_entity` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_design_load.py::TestCrossFileArchitectureResolution::test_architecture_of_entity_declared_nowhere_is_sys300` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_design_load.py::TestCrossFileArchitectureResolution::test_cross_file_architecture_exceeding_ceiling_is_sys302` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_design_load.py::TestCrossFileArchitectureResolution::test_same_entity_name_in_two_files_is_ambiguous` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::architecture_of_entity_not_in_this_file_stays_unresolved_at_parse_time` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::architecture_of_unresolved_entity_skips_sys302_locally` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 26 error(s), 4133 warning(s), 894 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3529, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
