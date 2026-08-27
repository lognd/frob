## Done report

frob ticket new already refuses (T-1995) on an exact/near-exact TITLE
match (>=0.8 difflib.SequenceMatcher.ratio(), --ack-related required to
override) -- verified still live and firing via a direct probe: filing
"DUPLICATE TITLE PROBE ZZZ TEST" twice in this worktree refused the
second attempt on a 100% title match. That mechanism is STRONGER than
this ticket's own acceptance asks (refuse, not just warn) and already
satisfies the "exact title match prints a warning naming the existing
id" criterion. Its existence contradicts the ticket's premise that
title is entirely unchecked; what T-1995 does NOT cover, and what this
ticket actually closes, is BODY similarity under a DIFFERENT title.

Added _body_similarity_warnings/_emit_body_similarity_warnings to
src/frob/app/ticket_runner/_new.py, wired into _new right after the
existing scope-overlap warning call. WARN only, never a refusal, per
this ticket's own acceptance -- deliberately weaker than T-1995's title
gate since a similar body is a weaker signal (tickets commonly share
boilerplate: a MEASURED preamble, an ACCEPTANCE section skeleton).
Threshold: 0.85 (difflib.SequenceMatcher.ratio(), same simple
deterministic comparison T-1995 already established, no fuzzy semantic
matching per this repo's standing directive), scoped to non-terminal
tickets (queued/planned/in-progress/blocked), matching
_scope_overlap_warnings' own terminal-state exclusion precedent one
function up.

WHY T-3063/T-3070 GOT THROUGH DESPITE T-1995 ALREADY EXISTING: their
titles were byte-identical too, which should have hit the T-1995 title
gate. Two plausible explanations, not disambiguated here (out of this
ticket's own scope to investigate further): the second filer passed
--ack-related without genuinely checking (override fatigue), or -- more
likely given this session's fleet scale -- a cross-worktree race: each
worktree's related_tickets() scan reads only its OWN local ledger view
(load_all(root)), so if both tickets were filed before either worktree
had merged/mirrored the other's new ticket, neither filer's local view
contained the sibling ticket at check time. This body-similarity check
has the identical race exposure (same load_all(root) read) and does not
close it -- flagging as a known gap rather than a silent one.

LEDGER-WIDE DUPLICATE SWEEP (the ticket's own "more valuable half"):
swept all 3019 tickets (309 active + 2710 archived) for (a) exact
lowercased-title matches -- O(n) via groupby, exhaustive -- and (b)
byte-identical bodies -- O(n) via sha256 groupby, exhaustive. Result:
62 exact-title duplicate PAIRS (many are groups of 3-4 tickets sharing
one title, e.g. T-1706/T-1712/T-1718/T-1731 all titled identically),
and 4 byte-identical BODY pairs (T-1274/T-1275, T-2512/T-2513,
T-2699/T-2701, T-3022/T-3023). T-3063/T-3070 itself is in the exact-
title list, confirming ground truth. This is NOT "T-3063/T-3070 was the
only one" -- the ledger carries a real backlog of title duplicates,
mostly historical/archived (post-land residue tickets, burn-down
batches, and TICK006 phantom-citation recoveries recur as a visible
sub-pattern: T-2247/T-2253, T-2459/T-2461, T-2590/T-2601,
T-2689/T-2699/T-2701 -- the same TICK006 false-positive class T-3108
addresses). Did NOT attempt a full fuzzy near-duplicate BODY sweep
(threshold 0.85, non-identical) at this scale: an exhaustive O(n^2)
difflib comparison over 3019 tickets did not complete inside a 200s
budget even with a length-bucket prefilter (~594k length-plausible
pairs remained after bucketing to within 18% length). The two
EXHAUSTIVE checks above (exact title, exact body) are complete and
cheap; a repo-scale fuzzy sweep would need a cheaper filter (minhash/
shingling) to be affordable -- noted as a gap, not silently skipped.

SCOPE NOTE: the ticket's declared scope named
src/frob/tickets/_setters.py, which has no new_ticket or scope-overlap
machinery at all. Corrected to
src/frob/app/ticket_runner/_new.py (the real _scope_overlap_warnings/
related_tickets/_refuse_unacknowledged_related_tickets home) before
touching any code, same pattern as T-3116's scope correction earlier in
this series.

### Changed
```
 src/frob/app/ticket_runner/_new.py                 |  75 ++++++++
 .../test_new_ticket_body_similarity_warning.py     | 189 +++++++++++++++++++++
 tickets/T-3124/ticket.md                           |  30 +++-
 tickets/T-3138/ticket.md                 |  32 ++++
 4 files changed, 324 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_new_ticket_body_similarity_warning.py::TestBodySimilarityWarnings::test_near_identical_body_different_title_warns` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_body_similarity_warning.py::TestBodySimilarityWarnings::test_genuinely_distinct_body_prints_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_body_similarity_warning.py::TestBodySimilarityWarnings::test_never_refuses_on_body_similarity_alone` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_body_similarity_warning.py::TestBodySimilarityWarnings::test_terminal_ticket_body_is_not_compared` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 78 error(s), 708 warning(s), 867 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bw/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3124, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
