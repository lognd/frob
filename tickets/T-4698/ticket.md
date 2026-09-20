---
id: T-4698
title: 'Ticket subverb tail: verdict per subverb (attach anchor flow plan board epic
  wave runs-last migrate archive reverify waive-audit review admin debt deprecated
  scope-ack worktree contention) -- keep with a cited consumer or delete with a shim'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4690
- T-4696
parent: T-4687
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/_cli_parsers/_ticket/_closeout_evidence.py
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/_cli_parsers/_ticket/_query.py
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/app/ticket_runner/_archive.py
- src/frob/app/ticket_runner/_attach_backfill.py
- src/frob/app/ticket_runner/_query.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/ticket_runner/_waive_audit.py
- tests/unit/test_ticket_subverb_tail.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.534.0
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 2338
  new_length: 2338
- mode: set
  reason: '2026-09-19 coordinator review: explore survives; pool/profile/debt/deprecated/parse
    reclassified out of the check --only fold; exports split check/scaffold; ordering
    vs hooks story'
  actor: logan
  at: '2026-09-19'
  old_length: 2338
  new_length: 4610
- mode: set
  reason: 'DOC006: planned CLI forms written as prose so unrelated lands are not refused'
  actor: logan
  at: '2026-09-19'
  old_length: 4610
  new_length: 4626
designated_repro_test: null
acceptance:
- text: Given the 20 tail subverbs, when the ticket closes, then the Done report carries
    one row per subverb with name, verdict, git grep hit count and the citing file:line,
    or the exact grep command that returned zero
  evidence: []
- text: Given a subverb whose verdict is KEEP, when its cited consumer is exercised
    by a test, then removing the subverb makes that test fail
  evidence: []
- text: Given a subverb whose verdict is DELETE, when the old spelling is invoked
    before its sunset date, then it prints the surviving spelling and exits 0, and
    after the sunset date exits non-zero
  evidence: []
threat: null
component: cli
labels:
- cli-debloat
- points-3
anchor: false
anchor_reason: null
land_commit: null
---
POINTS: 3. Parent story T-4687. blocked_by T-4690 (shim helper) and T-4696
(shares _cli_parsers/_ticket/__init__.py and app/ticket_runner/__init__.py).

THE TAIL. Of `frob ticket`'s 54 subverbs, 22 have ever been used in this fleet.
This ticket renders a VERDICT on each of the following 20, one at a time:
  attach  anchor  flow  plan  board  epic  wave  runs-last
  runs-last-parallel-safe  migrate  archive  reverify  waive-audit  review
  admin  debt  deprecated  scope-ack  worktree  contention

METHOD, per subverb, in this order:
1. `git grep -n "ticket <name>"` across src/, .claude/, docs/, scripts/,
   tests/. Record the hit count and the citing files.
2. Check .frob/telemetry.jsonl for a kind=cli row naming it. NOTE: today the
   subverb is NOT recorded (91% of rows have an empty `subcommand`; see T-4689)
   so an absence here is NOT evidence of disuse. Treat a telemetry zero as
   unknown, never as a verdict.
3. Verdict: KEEP (a real consumer exists -- name the file and line) or DELETE
   (with a T-4690 shim for one minor version).

KNOWN LOAD-BEARING, do not delete without an explicit argument in the Done
report: `plan` (state transition queued -> planned, part of the close dance),
`archive`, `anchor` (T-1856; T-1820 depends on anchors existing),
`waive-audit` (T-1614/T-2467), `contention` (the number that caps fleet
parallelism). `migrate` is a one-shot legacy converter and is the strongest
delete candidate. `debt` and `deprecated` duplicate the top-level verbs of the
same names that T-4692 is folding into frob check --only (planned) -- coordinate the
verdict with T-4692's outcome rather than deciding twice.

ACCEPTANCE IS THE VERDICT TABLE: the Done report must carry one row per subverb
with name, verdict, hit count, and the citing file:line (or "no consumer found"
with the exact grep command that was run). A verdict with no grep evidence is
not a verdict. Positive control: for at least one KEPT subverb, the cited
consumer is executed in a test that fails if the subverb is removed.

FILES (declared scope):
  src/frob/_cli_parsers/_ticket/__init__.py, _closeout.py,
  _closeout_evidence.py, _progress.py, _query.py, _new.py
  src/frob/app/ticket_runner/__init__.py, _archive.py, _attach_backfill.py,
  _query.py, _verify.py, _waive_audit.py, _lifecycle.py
  tests/unit/test_ticket_subverb_tail.py (new)

AMENDED 2026-09-19 (coordinator review): `parse` is added to this verdict table.
It was originally in T-4692's fold list, which misclassified it -- it is a
tool-output adapter (pytest/ruff/ty/clang/junit -> compact summary), not a gate
stage. It is a TOP-LEVEL verb, not a ticket subverb, so it is the one row in
this table that is not under `frob ticket`; it is here because this is the
story's verdict-rendering leaf.

PARSE, MEASURED 2026-09-19 (the grep evidence this table requires):
  `git grep -n "frob parse " -- src .claude docs scripts tests` -> 23 hits
    src/frob/_cli_parsers/_core.py      its own parser registration
    src/frob/app/parse_runner.py        its own implementation
    tests/unit/test_parse.py            its own test
    docs/commands/parse.md              its own doc page
    docs/design/cli-regrouping.md       the design doc being reverted by T-4690
  .claude/  0 hits
  scripts/  0 hits
  (the ~77 further hits of the string "frob parse" are prose -- "frob parses
  and analyzes source code" in docs/design/registry/weaknesses.yaml -- not
  invocations. Counting them would be the lexical-match error this repo's
  token/grammar directive exists to prevent.)
  RECOMMENDED VERDICT: DELETE with a shim. No consumer exists outside its own
  implementation, its own test, and its own documentation. If the implementer
  finds a consumer this grep missed, that is a KEEP and the citing file:line
  goes in the verdict table -- the recommendation is not the verdict.

`debt` and `deprecated` under `frob ticket`: T-4695 is simultaneously moving the
TOP-LEVEL `debt`/`deprecated` under frob explore (planned). Four names, two concepts.
Coordinate with T-4695 so only one ticket decides, and record the agreed
outcome in whichever of the two closes second.

SCOPE NOTE: `parse` lives in src/frob/_cli_parsers/_core.py and
src/frob/app/parse_runner.py, both outside this ticket's declared scope and
_core.py is contended with T-4690/T-4692/T-4695. Render the parse VERDICT here
(it is a documentation act), but execute the deletion in whichever of those
tickets still holds _core.py, or take the scope with `frob ticket scope T-4698
--add src/frob/app/parse_runner.py --reason ...` once _core.py is free. Say
which route was taken in the Done report.
