## Done report

## Done report

Changed:
- src/frob/gates/__init__.py -- `WAIVE006` (new stale-waiver-detection
  gate rule): `_waive006_binding_ticket_refs` (binding-phrase extraction),
  `_waive006_stale_ticket` (ledger+archive resolution), `_waive006_violation`
  (shared Violation constructor), `_waive006_comment_violations` (the
  `frob:waive` comment channel), `_STRATA_WAIVE_RE`/`_strata_waive_sites`
  (regex-scan of `.strata` `waive "RULE" reason "..." [ticket "..."]`
  clauses under the design dir), `_waive006_strata_violations` (the
  `.strata` channel), `waive006_gate` (public entry point, wired into
  `_assemble_gate_report` alongside the other WAIVE00* self-checks).
  `WAIVE006` added to `_KNOWN_GATE_RULES` (waivable -- deliberately NOT
  added to `_UNWAIVABLE_RULES`).
- docs/design/registry/check-coverage.yaml -- `CHK-GATE-WAIVE006` entry
  (`handled_by:WAIVE006`), `gate_rule_total` 104 -> 105. Required by the
  same change (REG008/REG009 red main on the new `frob:enforces` edge
  otherwise); scope was extended to cover this file via `frob ticket
  scope T-0779 --add docs/design/registry/check-coverage.yaml`.
- tests/test_waive_gate.py -- new file, 19 tests across binding-phrase
  extraction, the comment channel, the strata channel, waivability/
  registration, and a real-repo zero-false-positive proof.

Rule design: WAIVE006 fires when a waiver (either a `frob:waive` code
comment or a `.strata` `waive "RULE" reason "..." ticket "..."` clause)
BINDS ITSELF to a ticket id that is DONE or DROPPED in the merged
active+archive ledger (`frob.tickets.load_queue`, the same source
DEBT002 already resolves against). "Binds itself" is deliberately
narrower than "mentions": an explicit `ticket=`/`ticket "..."` attribute
is always binding; absent that, only two conservative reason-text
phrasings count as binding ("pending T-####[...]" and "T-#### is the
follow-on ticket") -- a bare id mention in build-history prose (e.g.
"(T-0200/T-0778)" or "T-0200 built a real kill switch") is never
extracted. An unresolvable ticket id (typo, not-yet-landed draft) is
silently skipped -- that is a different honesty gap, not WAIVE006's.

Calibration / real-repo result: `TestWaive006RealRepo::
test_zero_errors_on_real_repo` runs `waive006_gate` against this repo's
OWN live snapshot+queue (via `_load_inputs`) and asserts zero violations
-- verified passing. This specifically proves the T-0778 case the ticket
called out: `design/frob.strata`'s five current LINT004 waivers cite
`ticket "T-draft-8cd37914"` (open) while their `reason` text mentions the
long-closed T-0200 only as build-history narration ("kill-switch
mechanism exists (T-0200/T-0778) but ... -- tracked in
T-draft-8cd37914") -- WAIVE006 does not fire on that. The full `frob
check --only <stage>` chunked loop (lint/static/gates-fast/gates-native/
gates-security, `--ticket T-0779`, `FROB_AGENT=1` set so REL001's
bump/changelog half is suppressed per the worktree-agent posture) is
clean: `gate:WAIVE` reports 0 errors in every stage that runs it.

Evidence: 19 node ids recorded via `frob ticket evidence T-0779`, all
resolving under `pytest --collect-only`:
tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::{test_pending_phrasing_is_binding,
test_is_the_follow_on_ticket_phrasing_is_binding,
test_bare_historical_mention_is_not_binding,
test_built_a_real_kill_switch_narration_is_not_binding,
test_no_ticket_mention_at_all_is_not_binding},
TestWaive006CommentChannel::{test_ticket_attr_bound_to_done_ticket_fires,
test_ticket_attr_bound_to_dropped_ticket_fires,
test_ticket_attr_bound_to_open_ticket_is_silent,
test_binding_reason_phrase_bound_to_done_ticket_fires,
test_historical_mention_of_done_ticket_is_silent,
test_unresolvable_ticket_id_is_silent},
TestWaive006StrataChannel::{test_strata_ticket_attr_bound_to_done_ticket_fires,
test_strata_binding_phrase_bound_to_dropped_ticket_fires,
test_strata_open_follow_on_with_historical_mention_is_silent,
test_no_design_dir_is_silent},
TestWaive006Registration::{test_waive006_is_a_known_gate_rule,
test_waive006_gate_combines_both_channels,
test_waivable_via_frob_waive_comment},
TestWaive006RealRepo::test_zero_errors_on_real_repo.

`uv run pytest tests/test_waive_gate.py tests/test_gates.py -q`: 19 + 253
passed (both files, no failures). `uv run frob check --only lint/static/
gates-fast/gates-native/gates-security --ticket T-0779` (FROB_AGENT=1):
each stage 0 errors.

Filed: none.

Gates: `frob check --ticket T-0779` clean across all five `--only`
stage-groups (0 errors each). No waivers taken on this ticket's own
changes.

Deviations: the ticket's scope glob (src/frob/gates/**,
tests/test_waive_gate.py) did not cover the one-line registry companion
entry every new gate rule id needs (docs/design/registry/
check-coverage.yaml) -- extended scope via `frob ticket scope T-0779
--add ...` rather than silently touching an out-of-scope file, per the
SCOPE001 finding's own suggested remedy. `.strata` waive-clause detection
uses a plain single-line regex scan (`_STRATA_WAIVE_RE`) rather than a
`strata_core` parse -- every live `waive` clause in this repo today is
single-line (T-0778's own rewrite), so this is a documented, not a
silent, limitation; a clause split across lines is simply not matched.

### Changed
```
 tickets.md | 69 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 66 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_pending_phrasing_is_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_is_the_follow_on_ticket_phrasing_is_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_bare_historical_mention_is_not_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_built_a_real_kill_switch_narration_is_not_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_no_ticket_mention_at_all_is_not_binding` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_done_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_dropped_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_open_ticket_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_binding_reason_phrase_bound_to_done_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_historical_mention_of_done_ticket_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_unresolvable_ticket_id_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_ticket_attr_bound_to_done_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_binding_phrase_bound_to_dropped_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_open_follow_on_with_historical_mention_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006StrataChannel::test_no_design_dir_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006Registration::test_waive006_is_a_known_gate_rule` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006Registration::test_waive006_gate_combines_both_channels` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006Registration::test_waivable_via_frob_waive_comment` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo` (pytest node id, verified passing when recorded)
