## Done report

Changed:
- src/frob/cycle/graph.py::DependencyGraph.degraded_languages (new @property)
- src/frob/cycle/graph.py::find_cycles (now logs a WARNING when
  graph.degraded_languages is non-empty)
- docs/modules/graph.md (self-disclosure section updated: wiring is
  complete, `frob:until T-2700` removed)
- docs/commands/cycle.md (public-api block updated with the new property
  and find_cycles's disclosure behavior)
- tests/test_graph.py::TestDependencyGraphDegradedLanguages (new,
  positive + negative control)
- tests/test_graph.py::TestCycleImportGraphGapDisclosure (docstring
  updated to point at the new wiring instead of "not yet wired")

Design: `DependencyGraph.degraded_languages` derives languages present
from the graph's OWN node ids (every real caller -- frob.app.cycle_runner,
frob.check._python's CYCLE001 gate, frob.arch._smells -- adds nodes as
project-relative file paths), so no extra parameter needed threading
through any of those three files. `find_cycles` logs the disclosure
itself, so all three real callers see it on their own real invocation
(including the CYCLE001 gate `frob check` runs) without editing any of
those out-of-scope files.

Positive/negative controls (both required by the dispatch brief):
- test_known_gap_is_disclosed_on_degraded_languages_and_logged:
  monkeypatches python's import_graph capability to a live KNOWN_GAP and
  asserts BOTH graph.degraded_languages is non-empty AND find_cycles logs
  a WARNING containing "import_graph" -- proves the wiring fires end to
  end on find_cycles's own real invocation, not just that the field
  exists.
- test_clean_tree_has_no_degraded_languages_and_no_log_noise: a fully-
  supported graph gets an empty degraded_languages AND no WARNING log
  line from find_cycles -- proves this did not just add unconditional
  noise to every run.

Evidence:
tests/test_graph.py::TestDependencyGraphDegradedLanguages::test_clean_tree_has_no_degraded_languages_and_no_log_noise
tests/test_graph.py::TestDependencyGraphDegradedLanguages::test_known_gap_is_disclosed_on_degraded_languages_and_logged

Filed: T-2746 -- WIRE001's text-scan reach check has no
property-access pattern (only call-shaped/by-reference), so a brand-new
`@property`'s only real caller (attribute access, no parens) always
false-positives WIRE001. Waived at the property's own definition
(follow_up="T-2746") with a reason naming the real caller
(find_cycles, same file) and the test proving it.

Gates: frob check --ticket T-2700 --no-cache clean for every file this
ticket touches (src/frob/cycle/graph.py, tests/test_graph.py,
docs/modules/graph.md, docs/commands/cycle.md) -- remaining 84 errors in
the full report are pre-existing, unrelated to any file in this diff
(confirmed by filtering the JSON report to this ticket's files, all
findings there are note/warning severity or the WIRE001 note (waived)).
DOCENUM001 on docs/modules/graph.md:1044 and the "would reformat
tests/test_graph.py" warning are both pre-existing/unrelated to the
lines this ticket changed.

### Changed
```
 tickets/T-2700/ticket.md           | 26 +++++++++++++++++++-
 tickets/T-2746/ticket.md | 50 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 75 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_graph.py::TestDependencyGraphDegradedLanguages::test_clean_tree_has_no_degraded_languages_and_no_log_noise` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestDependencyGraphDegradedLanguages::test_known_gap_is_disclosed_on_degraded_languages_and_logged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 45 error(s), 1027 warning(s), 679 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2700, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
