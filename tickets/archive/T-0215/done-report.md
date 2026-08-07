## Done report

Changed:
- src/frob/tickets/_models.py -- `TicketError.EvidenceKindNotAllowed`,
  `TicketError.EvidenceCmdFailed`
- src/frob/tickets/__init__.py -- `run_cmd_evidence` (raw run-and-digest
  primitive), `add_cmd_evidence` (kind-gated evidence write), both exported
  in `__all__`; `_CMD_EVIDENCE_ALLOWED_KINDS = frozenset({TicketKind.DOCS})`
- src/frob/tickets/_land.py -- `_validate_closeable`'s hint now names
  `--evidence-cmd` and the `## Done report` heading's location in
  tickets.md (kept consistent with the CLI close-failure hint, per T-0176
  precedent)
- src/frob/app/ticket_runner.py -- `_apply_cmd_evidence` (mirrors
  `_apply_evidence`'s Result-passthrough contract); `_close_failure_hint`
  (InvalidTransition-from-queued/planned names `frob ticket start <id>`;
  MissingEvidence names the `## Done report` heading under the ticket's
  own tickets.md section); `_close` wired to both; `_evidence` accepts
  `--evidence-cmd` and requires ids-or-cmd; `_start` hard-errors on an
  already-in-progress ticket, naming `frob ticket sweep <id>` as the
  remedy
- src/frob/app/config.py -- `ticket_evidence_cmd: str | None` field +
  `from_external` wiring
- src/frob/__main__.py -- `--evidence-cmd` added to `ticket close` and
  `ticket evidence` parsers; `ticket evidence`'s positional node-ids made
  `nargs="*"` (was `"+"`) since `--evidence-cmd` alone is now a valid call
- docs/modules/tickets.md -- error-type table, Public API block, CLI
  integration-points section updated for all of the above
- tests/test_tickets_cmd_evidence.py (new) -- 15 tests covering
  `run_cmd_evidence`, the kind gate (docs-only; explicit bug/feature/
  security-kind rejection tests, including the "bug-kind ticket cannot
  close on cmd evidence alone" precedent test the ticket plan calls for),
  the `evidence --evidence-cmd` path, the close-from-queued hint, the
  MissingEvidence hint, and the start-on-in-progress hint

Decision (item 3, start-on-in-progress): kept it a hard error rather than
an idempotent no-op refresh. `frob ticket sweep <id>` already exists as
the exact idempotent refresh mechanism (re-records dup/xref/scope-digest
for an in-progress ticket); making `start` silently do the same thing
would be a second entry point for one mechanism, which is the duplication
this repo's own engineering principles rule out. `_start` now checks
`ticket.state == IN_PROGRESS` up front and errors with `frob ticket sweep
<id>` named explicitly as the remedy, before touching state at all.

Evidence recorded via `frob ticket evidence T-0215 <node-id>...` --
`tests/test_tickets_cmd_evidence.py` (15 ids) plus the pre-existing T-0184
vacuous-pass precedent test `tests/system/test_cli_ticket.py::
TestTicketRoundTrip::test_close_without_evidence_fails`, re-verified
still green after the `MissingEvidence` hint text changed the log message
shape (still contains the literal `MissingEvidence` error name the T-0184
test greps for, plus the new tickets.md/`## Done report` hint appended
after it).

Gates: `uv run frob check --ticket T-0215` -- 1 unwaived error
(`COV003` on `tickets/T-0168`, a pre-existing evidence id unrelated to
this ticket -- see the T-0172/T-0158 Done reports above for the same
standing note); zero violations attributable to this diff. Confirmed by
diffing against a clean `main` checkout (`git stash` + `frob check`):
main alone already carries this same COV003 plus ~1200 other pre-existing
notes/warnings (mostly waived PERF00x), none newly introduced here.
`TEST006` (no coverage stamp) is the standing campaign-wide waiver, not
run per instruction.

Tests: `uv run pytest -q` -- full suite green (0 failures) after the
T-0215 diff and after a second `git merge main` mid-session (main
advanced from e510af0 to b2a91fa while this ticket was in flight; the
merge auto-resolved cleanly, `frob ticket sweep T-0215` re-recorded the
now-stale scope digest, and `git diff main --diff-filter=D --stat` is
empty -- no unowned deletions after landing).

`uv run frob test --base main` -- `[PASS] python exit=0` (10 selected
tests: the T-0215 test file plus the existing evidence-cli/tickets
integration tests it touches transitively).

Filed: none -- everything found in-scope for T-0215 was fixed directly;
no out-of-scope follow-up work was discovered.

## Round 2 (reviewer REJECT -- gate disconnection)

Reviewer reproduced end to end: `COV003`/`_evidence_collected` (src/frob/
gates/__init__.py) only ever matched pytest node ids, so every docs
ticket closed via `--evidence-cmd` unconditionally tripped a COV003 ERROR
at `frob check` -- round 1's "check clean" only held because T-0215 itself
closed on pytest evidence, and none of the 15 round-1 tests ran the gate
after `add_cmd_evidence`. Scope note: fixing this required touching
`src/frob/gates/__init__.py`, outside T-0215's original scope declaration
-- extended the ticket's `scope` to add it explicitly (single file, not
`src/frob/gates/**`) rather than fixing silently outside scope, since the
reviewer's rejection makes this fix integral to T-0215 itself, not a
separate concern.

Changed (round 2):
- src/frob/tickets/_models.py -- moved the cmd-evidence shape primitives
  here from `__init__.py` (`CMD_EVIDENCE_ALLOWED_KINDS`, `_CMD_EVIDENCE_RE`,
  new public `is_cmd_evidence`) so BOTH `frob.tickets.__init__` and
  `frob.tickets._land` (which `__init__.py` imports, so the reverse import
  is unavailable) can share ONE definition without a circular import.
  `frob.gates` also imports directly from `_models` for the same reason.
- src/frob/tickets/__init__.py -- `_transition_guard`'s DONE path now also
  refuses `Err(EvidenceKindNotAllowed)` when a non-docs-kind ticket carries
  any `cmd:`-shaped evidence entry (kind hand-edited after recording, or
  hand-pasted) -- re-checked at close time, not just at
  `add_cmd_evidence`'s write time.
- src/frob/tickets/_land.py -- `_validate_closeable` gets the same
  kind-consistency re-check as the land-time twin of the guard above,
  keeping close and land consistent (T-0176 precedent).
- src/frob/gates/__init__.py -- new `_evidence_valid_for_ticket` (teaches
  COV003 the cmd: format): a `cmd:` entry validates iff its ticket's kind
  is in `CMD_EVIDENCE_ALLOWED_KINDS`, purely by format+kind, never by
  re-running the recorded command (documented in the docstring as a
  deliberate limit -- the digest is record-time attestation, not
  something the gate re-verifies on every `frob check`). `_cov003` now
  reports which failure class hit (cmd:-wrong-kind vs id-not-collected).
  Also hoisted a `sorted()` call out of `_cov003`'s per-evidence loop
  (PERF004) surfaced by this change.
- tests/test_tickets_cmd_evidence.py -- 7 new tests: `is_cmd_evidence`
  shape coverage; the full record->close->gate path for a docs ticket
  (`TestCov003CmdEvidence.test_docs_ticket_closed_via_evidence_cmd_is_gate_clean`,
  the reviewer's requested end-to-end proof); a bug-kind ticket with a
  hand-pasted `cmd:` entry failing COV003
  (`test_bug_kind_ticket_with_hand_pasted_cmd_entry_fails_cov003`, doubles
  as the kind-flip protection test); a malformed-shape cmd: entry on an
  otherwise-permitted docs ticket still failing COV003; and
  `TestKindConsistencyAtClose`'s three tests covering the close-time
  kind-flip-after-recording case (`transition` refuses) and both
  `_land._validate_closeable` branches (hand-pasted non-docs cmd: entry
  refused, docs cmd: entry accepted).
- tickets.md -- T-0215's `scope` list extended with
  `src/frob/gates/__init__.py`.

Evidence added: `is_cmd_evidence` shape test plus the 6 new gate/
kind-consistency tests, via `frob ticket evidence T-0215 <node-id>...`
(23 evidence ids total now).

Gates: `uv run frob check --ticket T-0215` -- same 1 unwaived pre-existing
error as round 1 (`COV003` on `tickets/T-0168`) plus the standing
`TEST006`/pre-existing `_land.py:75` `PERF004` (unrelated line,
`splice_ledger`, confirmed pre-existing against a clean `main` in round
1's Done report). Zero violations attributable to round 2's diff after
fixing the `COV001`/`TEST001`/`PERF004` the new symbols themselves
triggered along the way.

Tests: `uv run pytest -q` -- full suite green. `uv run frob test --base
main` -- `[PASS] python exit=0`. `git diff main --diff-filter=D --stat`
empty.

Merge: `git merge main` picked up T-0161/T-0166 (and further commits that
landed while round 2 was in flight) with a clean auto-merge (ledger-only
conflict, resolved by git itself, no manual splice needed); re-ran
`frob ticket sweep T-0215` afterward since the scope digest went stale.
