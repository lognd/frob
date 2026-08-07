---
id: T-0719
title: 'check: COV002/SCOPE001/TODO001 hard-error on a genuinely git-less root, not
  just a real repo''s bad diff'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gitio.py
- src/frob/gates/__init__.py
- tests/test_gates.py
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: regression tests for COV002/SCOPE001/TODO001 git-less-root split
  actor: logan
  at: '2026-07-23'
- op: add
  glob: frob.lock
  reason: frob ack coverage_gate after adding diff_load_no_repo param regenerates
    the lock's digest entry
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestGatesDegradeWithoutDiff::test_diff_dependent_gates_block_loudly_on_failed_diff
- tests/test_gates.py::TestGatesDegradeWithoutDiff::test_diff_dependent_gates_pass_quietly_on_a_genuinely_gitless_root
designated_repro_test: null
threat: null
component: null
---
Found while working T-0705. `_load_diff`'s diff_load_failed classification (T-0550) does not distinguish 'root is not a git repository at all' (GitError.NotARepo-shaped, e.g. a one-off frob check <path> on a plain filesystem directory) from 'a real git repo's working_diff genuinely failed' (bad --base, detached HEAD). Both currently hard-error COV002/SCOPE001/TODO001 identically. This dominates ~9 of T-0705's originally-reported ~12 system-test failures in tests/system/test_cli_check.py (test_clean_code_exits_zero, test_skip_ruff, test_skip_exports, test_check_skip_from_frob_toml, test_scoped_docanchor_matches_unscoped, test_only_gates_reports_violation_with_remedy, test_clean_ts_passes_tsc) -- these fixtures never call git init, so working_diff fails not because a real diff is broken but because there is no repo at all. T-0705's scope (the 4 named git-ls-files gates) was fixed and does not touch this gitio.py/T-0550 mechanism; this ticket tracks whether a genuinely-no-repo root should be treated as an empty/clean diff (skip diff-gates) rather than the loud diff_load_failed violation, without weakening the T-0550 protection against a REAL git failure inside an actual repo.