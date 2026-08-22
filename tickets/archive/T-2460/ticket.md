---
id: T-2460
title: Bump capability-via-ratchet.lock.json ceilings for T-2390 series (gates fs.write
  37->40, testsuite exec 185->186, testsuite fs.write 345->348)
state: done
kind: docs
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:bash /tmp/t2460_verify.sh exit=0 sha256=054d8bbd1270
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 8db5ebed7b82dc49d393011b3f35b43ad3cd3df4
---
SELFAUDIT001 is flagging three ratchet-ceiling-vs-actual mismatches after
the T-2390 series (T-2435/T-2436/T-2437) and other recently-landed
tickets grew via-lists past the committed ceilings:

  gates::fs.write        37 -> 40 (delta +3)
  testsuite::exec        185 -> 186 (delta +1)
  testsuite::fs.write     345 -> 348 (delta +3)

Per-entry, every added via-list site is attributed to a specific
already-landed ticket (measured via `git show <before>..<after> --
design/frob.strata`, diffing the via-list file sets directly, not
assumed):

  gates::fs.write (+4 files vs the last measured baseline of 36,
  ceiling was already 37): _gates_schema.py (T-2435),
  _test_runner_schema.py (T-2436), _dup_graph_schema.py (T-2437),
  _port_selfcheck.py (T-2388, unrelated, landed earlier in this
  session).

  testsuite::exec (+3 vs baseline 183, ceiling was 185):
  tests/unit/test_process_reap.py (T-2443),
  tests/unit/gates/test_port_selfcheck.py (T-2388),
  tests/test_tickets_no_scope.py (T-2394).

  testsuite::fs.write (+5 vs baseline 343, ceiling was 345):
  tests/unit/gates/test_port_selfcheck.py (T-2388),
  tests/unit/test_process_reap.py (T-2443),
  tests/unit/test_gates_table_schema.py (T-2435),
  tests/unit/test_test_table_schema.py (T-2436),
  tests/unit/test_dup_graph_table_schema.py (T-2437).

Every added site traces to a real, already-landed ticket; no
unexplained remainder in any of the three deltas.

gates::fs.write is entangled with T-2457 (fs.write capability detector
matches bare open() regardless of mode): three of this bump's four new
sites (_gates_schema.py/_test_runner_schema.py/_dup_graph_schema.py)
are false declarations forced by that detector bug, not real writes --
when T-2457 lands and removes the seven false declarations (these
three plus four earlier T-2390 siblings already in the via-list), the
gates::fs.write via-list count will drop back down and this ceiling
should be lowered again at that time. Setting the ceiling to exactly
the current genuine count (40), not a padded number, so the eventual
drop is visible rather than absorbed.