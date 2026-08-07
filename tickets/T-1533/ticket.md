---
id: T-1533
title: CorpusError needs a dedicated write-failure member
state: queued
kind: bug
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/registry/_corpus.py
- src/frob/app/registry_runner.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1359 made src/frob/registry/_staleness.py::sync_gate_rule_entries's
write crash-safe via frob.tickets._store.atomic_write, but on the
(should-never-happen) I/O failure path it has to reuse
CorpusError.FileNotFound as a stand-in -- not semantically accurate --
because CorpusError (src/frob/registry/_corpus.py) has no dedicated
write-failure member, and the two call sites that key a message dict on
CorpusError (frob.app.registry_runner._CORPUS_ERROR_MESSAGES,
frob.app.ticket_runner._land_cmd's synced.danger_err logging) sit
outside T-1359's declared scope (src/frob/gates/_fmt_directives.py,
src/frob/registry/_staleness.py, src/frob/release/**).

Add a CorpusError.WriteFailed member in src/frob/registry/_corpus.py,
have sync_gate_rule_entries return it instead of the FileNotFound
stand-in, and update _CORPUS_ERROR_MESSAGES (src/frob/app/registry_runner.py)
plus any other CorpusError-message dict to cover it so no caller KeyErrors
on the new variant.