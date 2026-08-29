## Done report

Split both LARGE001-flagged files along genuine concern boundaries and
measured the split, not just moved lines around.

src/frob/__main__.py (882 -> 497 lines): moved the whole argparse
parser-construction concern (_SuggestingArgumentParser, did-you-mean
suggestion machinery, _GroupedHelpFormatter, _build_parser,
_add_analysis_subparsers/_add_workflow_subparsers) into a new sibling
module src/frob/_cli_parsers/_root.py (480 lines), mirroring the existing
src/frob/_cli_parsers/ package's own T-1076 split precedent.
frob.__main__ keeps only runtime dispatch (main/_dispatch*) and re-imports
the full prior surface (all _add_*_parser builders, _build_parser,
_did_you_mean, etc.) so every existing call site --
from frob.__main__ import _build_parser across ~20 test modules,
frob.toml's parser = "frob.__main__:_build_parser" entrypoint,
tests/unit/test_main_entry.py's main_module._VERB_GROUP_NAMES -- keeps
working unchanged.

src/frob/stats/_agentic.py (802 -> 450 lines): split the dispatch-cost
report family (DispatchRecord/MarginalRunDelta/DispatchCostReport,
dispatch_cost_report and its helpers) into a new sibling module
src/frob/stats/_agentic_dispatch.py (363 lines) -- a genuinely separate
concern from the time/category report family this module keeps
(agentic_report and friends). The telemetry-line/timestamp/completed-event
primitives both families need (_load_events, _parse_iso,
_completed_tool_events, TELEMETRY_REL) were pulled into a third, neutral
module src/frob/stats/_agentic_shared.py (74 lines) -- mirrors this repo's
deploy/_generate_common.py precedent (extract a shared concern into a
module both sides import) rather than a one-sided re-export that would
create an import cycle. frob.stats.__init__ needed no changes: _agentic.py
re-imports and re-exports the dispatch symbols so
from frob.stats._agentic import DispatchCostReport etc. keep resolving.

Both target files measured well under LARGE001's 800-line threshold after
the split (confirmed via a fresh frob check --only gates LARGE001 scan
that has zero findings against either file); both frob:debt LARGE001 and
frob:waive LARGE001 directives are gone from both files, and no REL001
finding cites T-3059 any more.

Repaired what the move broke: DRIFT002 (doc/test frob:describes/frob:tests
edges retargeted from __main__.py/_agentic.py to _root.py/
_agentic_dispatch.py in docs/commands/cli-vocabulary.md,
docs/modules/stats.md, tests/integration/test_interfaces.py,
tests/test_stats_agentic.py), DOC006 (docs/modules/app.md's prose pointer
to _build_parser's new home), COV001/COV002 (frob:doc/frob:ticket edges
added on every relocated public symbol in the two new modules), COV007
(frob:waive on _GroupedHelpFormatter matching this repo's existing
T-0524/T-0529 architecture-doc precedent), AFFECT001 (frob ack on the four
relocated symbols whose doc content is unchanged, plus a frob:waive on
_GroupedHelpFormatter once its COV007 waiver comment changed its body
digest), and REF002 (was a stale-graph-cache artifact -- resolved by a
clean cache rebuild, no code/doc change needed).

Evidence: pytest tests/unit/test_main_entry.py tests/test_stats_agentic.py
tests/integration/test_interfaces.py -q (exit=0, 68 passed); frob test
--base main (python suite, exit=0, 22 recorded); frob check --only gates
--ticket T-3059 --json with a cleared gate-cache.db/parse-artifacts.db and
no REPLAY in the log, LARGE001: zero findings against either target file.

Gates: frob check --only gates --ticket T-3059 clean for both target files
and every file this change touched, except one residual: SELFAUDIT001
(design/frob.strata's SYS100 fs.read via-list still names
src/frob/stats/_agentic.py, which no longer performs the fs.read that
moved to _agentic_shared.py) -- waived in code with
follow_up="T-3409" (see Filed). Could not fix design/frob.strata
directly: it was held by a live cross-worktree lease from T-3388 for this
ticket's whole work window.

Filed: T-3409 "Update design/frob.strata SYS100 fs.read
capability for stats/_agentic split" -- swap
src/frob/stats/_agentic.py -> src/frob/stats/_agentic_shared.py in the
SYS100 fs.read via-list once design/frob.strata's lease frees.

### Changed
```
 tickets/T-3059/done-report.md      | 88 +++++++++++++++++++++++++++++++++++++
 tickets/T-3059/ticket.md           | 90 +++++++++++++++++++++++++++++++++++++-
 tickets/T-3409/ticket.md | 29 ++++++++++++
 3 files changed, 205 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_suggests_closest_known_flag` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_verb_groups_listed_before_also_available_directly_section` (pytest node id, verified passing when recorded)
- `tests/test_stats_agentic.py::TestDispatchCostReport::test_empty_stream_yields_empty_report` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_version_flag_prints_version_and_exits_zero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 19 error(s), 4141 warning(s), 860 waived
- error-findings: CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC011@docs/modules/tickets.md, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REL001@src/frob/__init__.py, REL001@src/frob/app/check_runner.py, REL001@src/frob/app/ticket_runner/_land_cmd.py, REL001@src/frob/process/_reap.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
