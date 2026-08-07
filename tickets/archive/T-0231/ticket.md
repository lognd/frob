---
id: T-0231
title: 'small CLI/UX batch: --version flag, sys plan dry-run label, DOC001 hint for
  missing docs root'
state: done
kind: ux
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/__main__.py
- src/frob/app/**
- src/frob/gates/**
- src/frob/strata/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_version_flag_prints_version_and_exits_zero
- tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_dry_run_names_apply_flag_in_label
- tests/test_gates.py::TestDoclinkGate::test_orphan_hint_does_not_point_at_missing_docs_root
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gaps 16/17/18 batched: (a) frob --version -> argparse error; add version output from package metadata. (b) frob sys plan without --apply prints 'compiled 1 obligation ticket(s)' with no dry-run label and no --apply mention -- say DRY RUN and name the flag. (c) DOC001 hint says 'link it from docs/index.md' in repos with no docs/index.md (lithos x256) -- resolve the configured/existing docs root or suggest creating one. Three small fixes, one ticket, tests each.