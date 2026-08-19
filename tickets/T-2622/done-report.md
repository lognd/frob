## Done report

Unified, per the ticket's own proposed design: WAIVE006/007's existing
`_WAIVE006_BINDING_PHRASE_RES` phrase-extraction tuple in
`src/frob/gates/_waive_comments.py` is now the ONE shared mechanism for
BOTH the lease-premise class ("T-#### holds/holding/under a live lease")
and the pre-existing pending/blocked/waiting classes -- five new patterns
were added to the SAME tuple, not a second parallel checker. Once a
ticket id is extracted (regardless of which phrase matched), the
existing WAIVE006 (ERROR if the cited ticket is DONE/DROPPED) and WAIVE007
(WARN if it does not resolve at all) logic handles it identically to
every other binding phrase -- zero new gate wiring needed, and this
already runs inside `frob check` today (unlike T-2606's WAIVE009, which
still needs its own follow-up wiring per that ticket's own disclosure).

T-2606's own promise-phrase mechanism (`_reason_promises_followup`/
`_reason_ticket_ids` in `_waive.py`) was evaluated for the same merge and
NOT folded into this same tuple: it answers a structurally different
question ("does this reason promise a ticket will be filed" -- true even
with ZERO ticket ids present) versus WAIVE006/007's question ("does this
reason bind itself to a ticket id that already exists, and is that
ticket's claimed state honest"). Forcing both into one function would
mean a single set of capture-group regexes serving two different
downstream checks with two different pass/fail bars (WAIVE009 requires
an id AND treats its absence as the finding; WAIVE006/007 require an id
to have ANYTHING to check and are silent without one) -- a shared
extraction primitive across BOTH files was considered (one `_ticket_id_re`
constant, one generic "extract ids near an ticket-referencing phrase"
helper reused by both `_waive.py` and `_waive_comments.py`) and rejected
for this pass: `_waive.py` already has its own narrower `_reason_ticket_ids`
(bare-token extraction, deliberately wider than binding-phrase-only,
per its own docstring) and `_waive_comments.py`'s `_WAIVE006_TICKET_ID_RE`
is already the identical literal (`T-\d+`) -- the actual duplication risk
(two divergent notions of "what is a ticket id token") does not exist;
what remains different between the two files is the CLASSIFICATION logic
built on top, which genuinely differs in shape. This is the "legitimate
divergence" outcome the ticket explicitly allows for, disclosed here
rather than silently: the two GATE FAMILIES share one mechanism each
(WAIVE006/007 share their phrase-tuple; WAIVE009 has its own, smaller,
purpose-built promise-phrase tuple) rather than all three sharing one
undifferentiated regex list whose entries would mean different things
per caller -- exactly what the ticket says to avoid forcing.

Real-repo validation (the actual point of building this against live
data, not a fixture): running the extended WAIVE006 against this
repo's OWN current tree surfaced 13 genuinely stale waiver sites (the
cited ticket really is DONE) that the OLD phrase set could not see --
direct confirmation the gap T-2612's manual audit found by hand is now
mechanically detectable. All 13 are outside this ticket's declared scope
(`src/frob/gates/_waive.py`/`_waive_comments.py`,
`tests/test_waive_gate.py`); filed as T-2656 (renumbers at
land) rather than fixed here or silently left unaddressed.
`TestWaive006RealRepo`'s calibration test now encodes those 13 sites as
an explicit, ticket-linked allowlist (`_WAIVE006_KNOWN_DEBT_T2622`) so
the test still fails on any NEW/different stale site (the calibration
guarantee holds) while acknowledging the real, already-tracked backlog
instead of asserting a zero that is no longer true.

Positive/negative controls verified directly (not just unit-tested):
- `src/frob/gates/_waive.py`'s own top-of-file SCOPE001 waiver (cited
  T-1279, now DONE) was a live hit before this ticket reworded it to
  past-tense historical narration -- fixed in the same diff since it is
  inside this ticket's own scope file.
- An ordinary waiver making no ticket claim at all is untouched: none of
  T-2606's 54 pre-existing WAIVE009 tests, nor WAIVE006/007's existing
  ~30 tests, changed behavior.

Measured: `uv run pytest tests/test_waive_gate.py -p no:cacheprovider -q`
-- 62 passed, 0 failed (8 new binding-phrase-extraction tests, 2 new
comment-channel end-to-end tests, plus the RealRepo allowlist rewrite,
all green; every pre-existing WAIVE006/007/WAIVE009 test unchanged in
behavior). `uv run frob check --only lint --ticket T-2622` -- 0 new
errors from this diff; the 2 remaining errors/223 warnings are
pre-existing and outside this ticket's scope (same F401/claude-config-
drift/CRLF-reformat backlog T-2606's Done report already disclosed).

### Changed
```
 src/frob/gates/_waive.py           |  16 +++--
 src/frob/gates/_waive_comments.py  |  31 ++++++++
 tests/test_waive_gate.py           | 143 ++++++++++++++++++++++++++++++++++---
 tickets/T-2622/ticket.md           |  42 ++++++++++-
 tickets/T-2656/ticket.md | 107 +++++++++++++++++++++++++++
 5 files changed, 322 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_lease_premise_bound_to_done_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_lease_premise_bound_to_open_ticket_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_holds_a_lease_phrasing_is_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_holding_a_lease_on_phrasing_is_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_possessive_lease_phrasing_is_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_lease_held_by_phrasing_is_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_under_x_lease_phrasing_is_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_past_tense_was_holding_is_not_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_unexpected_errors_on_real_repo` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive007RealRepo::test_zero_findings_on_real_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-0779, COV003@tickets/T-1072, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, F401@/home/logan/projects/frob/.claude/worktrees/t2606-t2622/src/frob/app/ticket_runner/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2622, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WAIVE006@src/frob/gates/__init__.py, WAIVE006@src/frob/gates/_coverage.py, WAIVE006@src/frob/gates/_decisions_compliance.py, WAIVE006@src/frob/gates/_doclink_docanchor.py, WAIVE006@src/frob/gates/_mutation_evidence.py, WAIVE006@src/frob/gates/_sys.py, WAIVE006@src/frob/gates/_tickets_gate.py, WAIVE006@src/frob/gates/_todo_fmt.py, WAIVE006@src/frob/tickets/_draft_finalize.py, WAIVE006@src/frob/tickets/_evidence.py, WAIVE006@src/frob/tickets/_models.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
