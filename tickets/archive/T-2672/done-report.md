## Done report

Root cause found: `_file_regression_ticket` in
src/frob/app/ticket_runner/_rapid_sweep.py unconditionally named
`final_id` (the land that happened to spawn the detached post-land sweep)
as the filed ticket's cause whenever `attributed_ids` (T-2009's
multi-land disclosure) was empty -- i.e. the common single-land-window
case -- with NO check against what the per-finding symbolic attribution
(src/frob/verify/_attribution.py, T-1690) had already computed for the
same batch. `_attribution.py` itself is correct and needed no change: it
already reported every one of the six measured tickets' findings as
UNATTRIBUTED (`attribute_batch`/`_attribute_one` walk the reference call
graph via `build_reference_graph_module_scoped`, T-2156's own module-
scoped fix, and correctly found no reaching commit). The false "regression
from T-2197"-style titles were produced downstream of a correct
computation, by a label-construction step that never consulted it.

Callgraph's bare-short-name resolution (`build_reference_graph`,
T-0422's dead-symbol-gate consumer) is NOT involved -- `_load_snapshot_
and_call_graph` (src/frob/verify/_attribution.py) explicitly uses `build_
reference_graph_module_scoped` instead, specifically because T-2156 found
the bare short-name resolver fabricates false attributions for this exact
consumer. Ruled out directly by reading the call site, not inferred.

Fix: `_single_land_attribution_label` (new helper) only returns `final_id`
when at least one filed pair's own `Attribution.status == "attributed"`
AND `Attribution.commit_sha == commit_sha` (the sweep's own measured
head) -- i.e. the evidence this function already computed actually
implicates the land. Otherwise it returns "an unattributed source (sweep
spawned by <final_id>)", which cannot be confused with a causal claim and
still discloses which sweep noticed it. The `_REGRESSION_TITLE_PREFIX`
constant and its "post-land sweep regression from " text are unchanged --
`_parse_sweep_ticket_identities`'s prefix-match staleness parsing still
recognizes every filed ticket, causal or not. The T-2009 multi-land
branch (`attributed_ids` non-empty) is untouched -- it already disclosed
honestly ("filed against all of them rather than falsely pinned on X
alone").

Changed:
  src/frob/app/ticket_runner/_rapid_sweep.py::_single_land_attribution_label (new)
  src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket

Evidence:
  tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_unattributed_finding_does_not_name_the_spawning_land_as_cause
    (designated repro, --check-repro FAILED_AT_PARENT at b80bc0bc0
    -- the test-only commit before the fix)
  tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_causally_implicated_land_still_names_itself_as_the_cause
    (positive control: a genuinely reaching land is still named plainly,
    "unattributed" absent from its title)

Both-direction controls (T-2672's own requirement):
  - a finding in a file the blamed land never touched is NOT attributed
    to it -- reported unattributed instead, still filed: covered by
    test_unattributed_finding_does_not_name_the_spawning_land_as_cause
  - a finding in a file the land DID touch is still attributed to it:
    covered by test_causally_implicated_land_still_names_itself_as_the_cause
    (pre-existing test_attributed_to_closed_ticket_is_refiled already
    covered the filing half; this adds the title assertion)
  - an unattributed finding is still filed, with its unattributed status
    stated: both new tests assert `filed is not None`; the unattributed
    test additionally asserts "unattributed" appears in the title

Full test_rapid_sweep.py suite: 151 passed (0 failed) after the fix, both
pre- and post-merge-main. test_attribution.py: 14 passed, unchanged
(module not modified).

Gates: `frob check --ticket T-2672 --only scope --only prework --only
test --only tickets --only drift --only render_lint` (chunked per
playbook 3b): gate:SCOPE clean (0 errors after widening scope to include
_rapid_sweep.py and tests/unit/test_rapid_sweep.py -- the real fix
location, added via `frob ticket scope --add --reason-file`, see
tickets.md scope-change entries). gate:DRIFT: acked
_file_regression_ticket (the only DRIFT001 finding on a file this ticket
touched); the other 3 DRIFT001 findings (_add_ticket_new_parser,
_parse_error_findings_from_json, _doable_sort_key) and the 4 RENDER001
findings (release/_cli.py) are pre-existing, unrelated to this ticket's
scope, not introduced by it. gate:TEST/gate:TICK findings are repo-wide
pre-existing debt (hook TEST003 gaps, TICK004 ticket-age rot, TICK011
Done-report residue citations) -- none name _rapid_sweep.py,
_attribution.py, or test_rapid_sweep.py.

`frob check --land-parity`: 22 unscoped errors, none in this ticket's
touched files (ARCH103/CYCLE001/DRIFT001/PERF00x/PII012/SEC004/SEC110/
SELFAUDIT001/WIRE00x across unrelated modules) -- this IS the class of
pre-existing, unattributed repo debt T-2672 itself documents; not
introduced by this change.

Filed: none -- no out-of-scope defect found beyond what T-2672 itself
already described. The scope widening (adding _rapid_sweep.py and
tests/unit/test_rapid_sweep.py) was recorded via `frob ticket scope
--add --reason-file`, not a new ticket, since the work stayed inside
T-2672's own declared bug.

Time breakdown (rough): playbook read + ticket read ~10min; worktree
warm-up (worktree create, natives build, merge) ~5min; investigation
(reading _attribution.py, _rapid_sweep.py, tracing the false-blame
mechanism through _partition_findings_by_attribution and
_file_regression_ticket, reading a real filed ticket T-2591 to confirm
the title/attribution-status mismatch) ~25min; repro test + verify
FAILED_AT_PARENT ~10min; fix + positive-control test + local suite runs
~20min; scope widening + DRIFT ack + scoped gate runs ~15min; land-parity
check ~5min; coordinator-directed re-merge + done-report ~10min.

Gates: frob check --ticket T-2672 clean for this ticket's own touched
files (gate:SCOPE 0 errors, gate:DRIFT 0 errors on this ticket's symbols
after ack); land-parity's 22 unscoped errors are pre-existing debt in
files this ticket never touched.

### Changed
```
 frob.lock                                  | 20 +++++-
 src/frob/app/ticket_runner/_rapid_sweep.py | 66 +++++++++++++++++++-
 tests/unit/test_rapid_sweep.py             | 99 ++++++++++++++++++++++++++++++
 3 files changed, 183 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_unattributed_finding_does_not_name_the_spawning_land_as_cause` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_causally_implicated_land_still_names_itself_as_the_cause` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 45 error(s), 896 warning(s), 698 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2672, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
