---
id: T-3645
title: 'refactor split: per-symbol import carry-forward not merged into one top-level
  block when multiple classes land in same destination module'
state: done
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/**
- tests/test_refactor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_refactor.py
  reason: 'SCOPE002: test coverage closure for the src/frob/refactor package this
    fix touches pulls in the package''s own frob:tests suite file'
  actor: logan
  at: '2026-09-01'
evidence:
- tests/test_refactor.py::TestRunSplit::test_split_merges_carried_imports_into_existing_top_block
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3593 (split tests/test_vet.py into tests/vet_suite/*.py, reusing T-3586/T-3596's recipe).

frob refactor split carries an imported symbol's needed import statement forward ONCE PER SYMBOL rather than merging into a single deduped top-of-file block when several classes/functions moved in the same split batch (or across sequential split invocations targeting the same --into module) land in the same destination file. Each symbol's carried-forward import is inserted immediately above that symbol, dedented to column 0 -- valid Python (imports are idempotent, no runtime break) but violates ruff E402 (module level import not at top of file) and I001 (unsorted import block), and leaves duplicate import lines scattered through the file body instead of one clean top block.

Repro: split 4+ classes from one source module into the same destination module across separate frob refactor split invocations (or one combined invocation), where at least 2 of the classes need distinct imports not already present in the destination. Example from T-3593:
  uv run frob refactor split tests.test_vet --symbols TestLockfileParsers --into tests.vet_suite.test_lockfile --skip-check-delta
  uv run frob refactor split tests.test_vet --symbols TestAllowConfig --into tests.vet_suite.test_lockfile --skip-check-delta
  uv run frob refactor split tests.test_vet --symbols TestQuarantine --into tests.vet_suite.test_lockfile --skip-check-delta
  uv run frob refactor split tests.test_vet --symbols TestTyposquat --into tests.vet_suite.test_lockfile --skip-check-delta
-> tests/vet_suite/test_lockfile.py ends up with 4+ separate 'from pathlib import Path' / 'from frob.vet._X import Y' blocks scattered mid-file, each immediately above the class that needed it, instead of one merged top-level block.

Measured impact this session: 50 ruff E402/I001 findings across 12 of 13 new destination files in one split ticket (T-3593), all requiring a hand pass (script-assisted: collect all module-level Import/ImportFrom nodes after the top block, dedupe against the top block by exact statement text, consolidate) before the file was ruff-clean and landable.

Suggested fix: when split's carry-forward inserts a needed import into a destination module that ALREADY HAS a top-level import block (i.e. this is not the first symbol landing in that file), merge the new import into that existing top block (dedup by statement, insert in whatever order, let a subsequent ruff --fix sort it) instead of inserting a fresh import statement immediately above the newly-placed symbol.