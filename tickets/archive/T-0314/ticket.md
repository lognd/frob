---
id: T-0314
title: frob check <subdir> resolves frob:doc target files relative to the scoped path,
  not repo root
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/gates/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_check.py::TestCheckDocAnchorScopedVsUnscoped::test_scoped_docanchor_matches_unscoped
designated_repro_test: null
threat: null
component: null
---
FROBLEMS (lithos W2b): 'frob check --only gates python/regolith/realizer' resolves every 'frob:doc docs/modules/x.md#anchor' target relative to the scoped root (python/regolith/realizer) instead of the repo root the path text is relative to -> every frob:doc came back DOC002 'target file does not exist', while the identical directives are clean under unscoped 'frob check .'. Root cause named: check_runner.py::_dispatch_check_python root = cfg.check_path or Path('.') feeding _doc_anchor_slugs(root / docfile). Fix: frob:doc doc-file targets must resolve against the REPO ROOT (git/frob root), not the scoped check path; the scoped path should filter which findings are reported, not rebase directive path resolution. Test: a scoped gates run yields the same DOC002 result as the unscoped run for the same directive.