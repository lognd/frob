---
id: T-0818
title: 'test_cli_check: TS/gitless fixture debt unrelated to T-0806 (LANG003 T-0329
  dangling ref, capsys/logging init-order flake)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/system/test_cli_check.py
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_check.py::TestCheckTypescript::test_clean_ts_passes_tsc
- tests/system/test_cli_check.py::TestCheckTypescript::test_type_error_fails_tsc
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_gitless_target_gates_warn_not_error
designated_repro_test: null
threat: null
component: null
---
While root-causing T-0806 (test_cli_check tmp fixtures broken on main),
two more failures in tests/system/test_cli_check.py were found -- neither
is related to T-0806's git-ls-files/JSON-pollution regression, and both
are pre-existing, unrelated debt:

1. TestCheckTypescript::test_clean_ts_passes_tsc -- once the fixture is a
   real git repo (fixed under T-0806), the run still fails on TWO
   unrelated issues:
   a. TEST001 ("src.ts::add is public with no unit test") and TEST006
      ("no coverage stamp found") fire because the fixture never sets a
      warn-severity frob.toml the way tests/system/test_cli_check.py's
      other python fixtures (_make_project) do.
   b. LANG003 fires unconditionally for any typescript project checked
      against this repo's own queue: "typescript facet 'arch' is
      known_gap ... tracked by T-0329 ... which does not exist in the
      loaded queue". T-0329 is referenced in the LANG003 known_gap
      declaration but does not exist as a real ticket -- this is a
      genuine product-side dangling reference (either T-0329 needs to be
      created/tracked, or the known_gap declaration needs a live ticket
      id), independent of any test fixture.

2. TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
   -- flaky/order-dependent: passes standalone and in some pairings, fails
   in others. Its docstring explains it reads frob's own stderr
   StreamHandler via `capsys` rather than `caplog` because
   `frob.logging.logger._init()` binds `ext://sys.stdout`/`ext://sys.stderr`
   ONCE, lazily, at the first `get_logger()` call in the whole pytest
   session/worker -- if that first call happens before this particular
   test's own `capsys` fixture is active (i.e. some earlier test in the
   file already triggered `_init()` first), the bound stream handler
   never observes THIS test's `capsys` wrapper, and `capsys.readouterr()`
   comes back empty regardless of what frob.gates._render_lint actually
   logged. This is a structural test-isolation gap: any in-process test in
   this file that wants `capsys`/`capfd` to observe frob's own logging
   output needs the process's first `frob.logging.get_logger()` call to
   happen AFTER capsys is installed, which pytest does not guarantee
   across a whole session/xdist worker. Needs either a fixture that resets
   `frob.logging.logger._initialized` and rebinds handler streams per
   test, or the assertion needs a different capture mechanism entirely.

Scope: tests/system/test_cli_check.py (both fixtures/assertions), and
possibly src/frob/gates/_lang_conformance.py or wherever the LANG003
known_gap detail for T-0329 lives (find via grep "T-0329").