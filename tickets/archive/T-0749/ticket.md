---
id: T-0749
title: 'evidence --accepts binding not persisted (at least via --path): acceptance
  stays unbound after CLI reports success'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: critical
parent: T-0572
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/**
- tests/test_tickets_acceptance.py
- src/frob/app/config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/config.py
  reason: root cause of the --accepts persistence bug is a missing field-copy line
    in AppConfig.from_external, not in ticket_runner.py/tickets/** as suspected
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_tickets_acceptance.py::TestAcceptsCliWiring::test_from_external_carries_accepts_from_parsed_argv
- tests/test_tickets_acceptance.py::TestAcceptsCliWiring::test_evidence_cli_binds_acceptance_via_path_flag
- tests/test_tickets_acceptance.py::TestAcceptsCliWiring::test_evidence_cli_binds_acceptance_in_repo_no_path_flag
- tests/test_tickets_acceptance.py::TestAcceptsCliWiring::test_close_time_verification_consumes_the_accepts_binding
designated_repro_test: null
acceptance:
- text: GIVEN frob ticket evidence X node --accepts 0 --path DIR WHEN the ledger is
    re-read THEN acceptance[0].evidence contains the node id
  evidence:
  - tests/test_tickets_acceptance.py::TestAcceptsCliWiring::test_from_external_carries_accepts_from_parsed_argv
  - tests/test_tickets_acceptance.py::TestAcceptsCliWiring::test_evidence_cli_binds_acceptance_via_path_flag
  - tests/test_tickets_acceptance.py::TestAcceptsCliWiring::test_evidence_cli_binds_acceptance_in_repo_no_path_flag
  - tests/test_tickets_acceptance.py::TestAcceptsCliWiring::test_close_time_verification_consumes_the_accepts_binding
threat: null
component: null
---
Field bug found landing T-0736 (the first close under T-0572s acceptance gate): frob ticket evidence <id> <node> --accepts N --path <dir> reports the evidence append but the criterion binding does NOT persist -- acceptance[N].evidence stays [] on read-back (reproduced 3x; the plain evidence list grows, the binding is dropped). Unblocked via a direct store-API write. Root-cause candidates: the accepts write path ignores --path, or the binding is applied to a copy the ledger write does not carry. Add a regression test binding via --path and reading back; audit the in-repo (no --path) path too -- T-0572s own tests bound in-repo and passed, so the --path leg is at least the broken one.