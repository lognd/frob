---
id: T-0355
title: 'sweep: clean SIGINT message + PRE001 catch-22 on slow mounts + scope_digest
  content-keying'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/__main__.py
- src/frob/gates/**
- src/frob/tickets/**
- tests/test_prework_parity.py
- tests/unit/test_main_entry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_prework_parity.py
  reason: add regression tests for the SIGINT clean-message fix and the scope_digest
    content-portability contract
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: add regression tests for the SIGINT clean-message fix and the scope_digest
    content-portability contract
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130
- tests/unit/test_main_entry.py::TestMainSigint::test_normal_dispatch_is_unaffected
- tests/test_prework_parity.py::TestScopeDigestParity::test_digest_is_content_only_portable_across_checkouts
designated_repro_test: null
threat: null
component: null
---
found while working T-0240 (same origin ticket text, deliberately split out): T-0240 fixed the sweep's unbounded full-root xref walk and glob-stem xref terms, but three remaining items from the original malmberg report are NOT addressed by that fix and need their own design/scope: (1) SIGINT during a long sweep prints a bare KeyboardInterrupt traceback instead of a clean message -- __main__.py-level signal handling, out of T-0240's tickets/gates/dup scope. (2) PRE001 catch-22 on slow mounts: editing a ticket's scope demands a re-sweep, and if the sweep itself is what is slow on that mount the ticket can never get back into a checkable state -- needs a design decision (timeout + partial-sweep-ok state, or async sweep), not a bugfix. (3) scope_digest hashes snapshot file-hashes (path+content sha), so a recorded sweep cannot be transplanted between two checkouts with identical file content but different paths/timestamps-derived hashes -- consider keying on content-only digest so sweep records are checkout-portable. None of these are addressed by T-0240's fix.