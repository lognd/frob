---
id: T-0837
title: 'docs: port the frob review channel section for T-0571, repoint its frob:doc
  anchors'
state: done
kind: docs
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/tickets.md
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner.py
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/integration/test_interfaces.py
  reason: docs-ticket evidence test file, per playbook section 5
  actor: logan
  at: '2026-07-26'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
T-0571's salvage port (frob review: structured adversarial review channel
as first-class evidence) landed without its docs section --
docs/modules/tickets.md was outside the port's six-file scope, so the
donor's #structured-review-channel-t-0571 section was never ported and
two frob:doc anchors were repointed at #public-api as a disclosed
workaround. Write the section (CLI usage: frob ticket review with
--verdict/--reviewer/--findings-file/--commit, close --strict,
require_review_for_close frob.toml key, ReviewEntry evidence shape) and
repoint the two anchors in src/frob/tickets/__init__.py /
src/frob/app/ticket_runner.py back at the new section.