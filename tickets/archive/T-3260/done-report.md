## Done report

Real split of both LARGE001-flagged files, closing the seam T-3079's waiver
already identified.

vmodel.rs (993 lines) -> vmodel/mod.rs (schema/constants) + vmodel/closure.rs
(the five structural closure rules). grammar_core.rs (833 lines) sheds
parse_vmodel_node/parse_vmodel_edge into a new grammar_vmodel.rs fragment,
spliced back into Parser via parse/mod.rs's existing include! mechanism
(same pattern every other grammar-family fragment already uses, so no new
pub(crate) leakage).

All four resulting files are under the 800-line threshold; the
frob:debt/frob:waive LARGE001 directives on both original files are
removed, clearing REL001 for this ticket's files (release-blocking debt).

Relocated symbols kept their coverage: frob:tests path references updated
from vmodel.rs to closure.rs/mod.rs, COV002 satisfied via frob:ticket
T-3260 directives on every moved symbol, AFFECT001 satisfied via `frob ack`
(32 refs, pure relocation, no behavior change) plus doc-anchor location
notes added to docs/strata/vmodel.md so the docs actually reflect the new
file layout.

Verified: cargo build/test/fmt/clippy(-D warnings) all clean; 202/202
strata-core lib tests pass. `frob natives build` succeeds and
`import strata_core; strata_core.vmodel_check` still resolves (the PyO3
surface src/frob/gates/_vmodel.py calls is untouched -- lib.rs was not
modified). `frob check --ticket T-3260 --only gates`, cache cleared
beforehand, 0 REPLAY, shows zero in-scope errors -- the remaining
repo-wide findings (REL001 on other tickets' debt, TICK004, DOC003/011,
etc.) are pre-existing and unrelated to this ticket's files.

### Changed
```
 docs/strata/vmodel.md                              |  31 +-
 frob.lock                                          | 587 +++++++++++++++++++++
 .../src/graph/{vmodel.rs => vmodel/closure.rs}     | 372 +++----------
 strata-core/src/graph/vmodel/mod.rs                | 322 +++++++++++
 strata-core/src/parse/grammar_core.rs              | 126 +----
 strata-core/src/parse/grammar_vmodel.rs            | 129 +++++
 strata-core/src/parse/mod.rs                       |   6 +-
 tests/unit/strata/test_vmodel_check.py             |   6 +-
 tickets/T-3260/ticket.md                           |   8 +
 9 files changed, 1150 insertions(+), 437 deletions(-)
```

### Evidence
- `tests/unit/strata/test_vmodel_check.py::TestVmodelCheckClosureSemantics::test_mutual_satisfies_pair_with_zero_requirements_now_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_vmodel_check.py::TestVmodelCheckClosureSemantics::test_genuine_four_level_chain_is_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_vmodel_check.py::TestVmodelCheckClosureSemantics::test_satisfies_cycle_fires_through_vmodel_check` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_vmodel_check.py::TestVmodelCheckNodePayload::test_artifact_node_missing_code_ref_is_a_construction_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_vmodel_check.py::TestVmodelCheckNodePayload::test_test_node_missing_runnable_is_a_construction_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_vmodel_check.py::TestVmodelCheckNodePayload::test_supersedes_edge_missing_reason_is_a_construction_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_vmodel_check.py::TestVmodelCheckNodePayload::test_payload_present_on_every_kind_stays_quiet` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 31 error(s), 4064 warning(s), 896 waived
- error-findings: CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC006@tickets/T-1382/ticket.md, DOC011@docs/modules/tickets.md, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PRE001@tickets/T-3260, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/app/check_runner.py, REL001@src/frob/app/ticket_runner/_land_cmd.py, REL001@src/frob/process/_reap.py, REL001@src/frob/stats/_agentic.py, REL001@tests/unit/test_conftest_suite_result_status.py, SELFAUDIT001@design, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
