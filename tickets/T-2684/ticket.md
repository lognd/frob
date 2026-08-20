---
id: T-2684
title: 'gates: QueueUnavailable manufactures an empty-rule-id finding against the
  retired tickets.md path'
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/_python.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2134 investigated whether the retired v1 `tickets.md` monofile path is
still live anywhere in code/config/gate logic, prompted by a real incident:
a `frob ticket land` was blocked twice by a ClaimDivergence citing a
finding with an EMPTY rule id against the path `tickets.md`, which exists
neither on disk nor in `git ls-files` (T-2356 already deleted the physical
monofile and its archive).

Root cause found and confirmed by direct code read (not the corrupt-ledger
cause that actually fired that day, but the SYMPTOM's manufacturing site):

`frob.check._python._gates_error_result` (src/frob/check/_python.py,
around line 1004) handles `GateError.QueueUnavailable` -- raised whenever
`frob.tickets._load_merged`/`load_queue` fails to load the ticket queue
for ANY reason under ledger v2 (a malformed `tickets/T-####/ticket.md`,
or -- per `_tick001_duplicate_ids`'s own docstring in
src/frob/gates/_tickets_gate.py -- a duplicate ticket id across active/
archive, exactly what actually happened the day this was hit) -- and
returns a hardcoded:

    Diagnostic(file="tickets.md", severity="error", message=...)

with no `code=` set at all. Two defects compound here:

1. `file="tickets.md"` names the RETIRED v1 monofile path unconditionally,
   even though ledger v2's real failing artifact is some `tickets/
   T-####/ticket.md` (or a cross-file duplicate-id condition with no
   single natural path). The path in the finding cannot exist on disk in
   this repo any more, which is exactly what sent this ticket's author
   looking for a stale/orphaned monofile instead of the real ledger
   corruption -- it cost four failed land attempts and a long
   misdiagnosis before anyone looked past the phantom path.
2. `code=` (the field `Diagnostic.as_text()` renders as the rule id) is
   never set on this Diagnostic, so the finding surfaces with an EMPTY
   rule id -- unwaivable by rule id, unsearchable by rule id, and
   indistinguishable from any other code-less diagnostic.

`frob.app._check_chunking._run_gate_chunks_stamping_progress` has the
same `GateError.QueueUnavailable` branch but only logs and exits; it does
not manufacture a Diagnostic, so it is not part of this defect.

Suggested fix direction (not implemented here -- out of this ticket's
`tickets.md`-only scope): `_gates_error_result` should name the actual
failing ledger artifact ferried up from `GateError`/the underlying
`TicketError` (e.g. the duplicate id and both its source paths, or the
malformed ticket dir), not a hardcoded v1 constant: and should set a real
`code=` (e.g. "QUEUE001" or similar) so the finding is waivable/
searchable like every other gate finding instead of surfacing with an
empty rule id.

Other `tickets.md` references surveyed and found NOT to be live defects:
- `src/frob/tickets/_models.py` `LEDGER_PATH = "tickets.md"` /
  `_store.py` `_LEDGER_NAME` -- used only as a scope-matching glob
  literal ("always in scope" pattern, T-0241) and as the (now-nonexistent)
  target path for `ledger_path()`. Harmless: the glob simply never
  matches a real file post-T-2356.
- `src/frob/graph/__init__.py`'s `is_ledger` doc-graph-exclusion check --
  dead in practice post-T-2356 (the file it excludes no longer exists at
  repo root) but not harmful.
- `src/frob/doctor.py` `scan_malformed_ticket_edges` -- already guards
  with `path.is_file()` before reading; a missing ledger contributes zero
  findings, not an error.
- `src/frob/refactor/_repointer.py` `_LEDGER_FILES` -- legacy-aggregator
  repointing logic, guarded by existence checks per its own comments.
