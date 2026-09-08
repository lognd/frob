---
id: T-4308
title: macOS fixture subprocess finds no pytest or ruff, cascading to 68 failures
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_check.py
- src/frob/__main__.py
- src/frob/process/parsers/ruff.py
- src/frob/process/parsers/common.py
- tests/unit/test_main_entry.py
- tests/unit/test_parser_failure_diagnostics.py
- docs/modules/app.md
- docs/modules/logging.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/__main__.py
  reason: 'T-4308 root cause: macOS launches frob via .venv/bin/python -m frob (T-4274)
    so VIRTUAL_ENV is never set, breaking every nested uv-run tool spawn''s active-venv
    fallback; fix is a single early os.environ set in __main__.py, plus distinguishing
    empty tool output from malformed output in the ruff JSON parser'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/process/parsers/ruff.py
  reason: 'T-4308 root cause: macOS launches frob via .venv/bin/python -m frob (T-4274)
    so VIRTUAL_ENV is never set, breaking every nested uv-run tool spawn''s active-venv
    fallback; fix is a single early os.environ set in __main__.py, plus distinguishing
    empty tool output from malformed output in the ruff JSON parser'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/process/parsers/common.py
  reason: 'T-4308 root cause: macOS launches frob via .venv/bin/python -m frob (T-4274)
    so VIRTUAL_ENV is never set, breaking every nested uv-run tool spawn''s active-venv
    fallback; fix is a single early os.environ set in __main__.py, plus distinguishing
    empty tool output from malformed output in the ruff JSON parser'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: 'T-4308 root cause: macOS launches frob via .venv/bin/python -m frob (T-4274)
    so VIRTUAL_ENV is never set, breaking every nested uv-run tool spawn''s active-venv
    fallback; fix is a single early os.environ set in __main__.py, plus distinguishing
    empty tool output from malformed output in the ruff JSON parser'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_parser_failure_diagnostics.py
  reason: 'T-4308 root cause: macOS launches frob via .venv/bin/python -m frob (T-4274)
    so VIRTUAL_ENV is never set, breaking every nested uv-run tool spawn''s active-venv
    fallback; fix is a single early os.environ set in __main__.py, plus distinguishing
    empty tool output from malformed output in the ruff JSON parser'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/__main__.py
  reason: 'T-4308 root cause: macOS launches frob via .venv/bin/python -m frob (T-4274)
    so VIRTUAL_ENV is never set, breaking every nested uv-run tool spawn''s active-venv
    fallback; fix is a single early os.environ set in __main__.py, plus distinguishing
    empty tool output from malformed output in the ruff JSON parser'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/process/parsers/ruff.py
  reason: 'T-4308 root cause: macOS launches frob via .venv/bin/python -m frob (T-4274)
    so VIRTUAL_ENV is never set, breaking every nested uv-run tool spawn''s active-venv
    fallback; fix is a single early os.environ set in __main__.py, plus distinguishing
    empty tool output from malformed output in the ruff JSON parser'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/process/parsers/common.py
  reason: 'T-4308 root cause: macOS launches frob via .venv/bin/python -m frob (T-4274)
    so VIRTUAL_ENV is never set, breaking every nested uv-run tool spawn''s active-venv
    fallback; fix is a single early os.environ set in __main__.py, plus distinguishing
    empty tool output from malformed output in the ruff JSON parser'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: 'T-4308 root cause: macOS launches frob via .venv/bin/python -m frob (T-4274)
    so VIRTUAL_ENV is never set, breaking every nested uv-run tool spawn''s active-venv
    fallback; fix is a single early os.environ set in __main__.py, plus distinguishing
    empty tool output from malformed output in the ruff JSON parser'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_parser_failure_diagnostics.py
  reason: 'T-4308 root cause: macOS launches frob via .venv/bin/python -m frob (T-4274)
    so VIRTUAL_ENV is never set, breaking every nested uv-run tool spawn''s active-venv
    fallback; fix is a single early os.environ set in __main__.py, plus distinguishing
    empty tool output from malformed output in the ruff JSON parser'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/process.md
  reason: AFFECT001 closure for parse_ruff_json/tool_no_output_result touched by this
    diff
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/process.md
  reason: 'reverted: switched to a frob:waive AFFECT001 instead of editing this shared
    doc, to avoid its large cross-ticket scope-closure fan-out'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/app.md
  reason: SCOPE002 closure for pre-existing main()/_apply_verbose_env_override() frob:doc
    targets in files this ticket must touch
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/logging.md
  reason: SCOPE002 closure for pre-existing main()/_apply_verbose_env_override() frob:doc
    targets in files this ticket must touch
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE MACOS LEG FAILS SIXTY-EIGHT TESTS MORE THAN THE LINUX LEG OF THE SAME COMMIT,
AND THE EXCESS TRACES TO THE FIXTURE SUBPROCESS FINDING NO TOOLS RATHER THAN TO
SIXTY-EIGHT DEFECTS.

WHAT THE LOG SHOWS, FROM A TEST WHOSE WHOLE PURPOSE IS THAT A CLEAN PROJECT EXITS
ZERO. Running the check verb against a freshly-created clean fixture project
reports two errors. The first is that the lint tool's output could not be parsed
as JSON because it was empty. The second is that test collection failed, and the
captured reason is explicit: the spawn of the test runner failed with "no such
file or directory", preceded by a warning that no interpreter requirement was
found in the workspace so a very new default was assumed. Neither error is about
the fixture's code, which is clean by construction.

WHY THIS CASCADES. Collection failing makes every Python evidence id unresolved at
once -- the coverage gate says so itself, naming one root cause rather than many.
That single failure propagates into the check CLI tests, the doctor tests (which
assert a healthy verdict), the daemon differential-parity tests, and more. Fixing
the spawn should retire the bulk of the excess in one change. Do not file or fix
the downstream assertions individually until the root cause is settled.

ESTABLISH WHY THE ENVIRONMENT DIFFERS BETWEEN THE TWO PLATFORMS, because that is
the actual question. The same tests pass on the linux leg of the same commit, so
something about how the temporary fixture project resolves its environment differs
on macos -- candidates include where the temporary directory lives relative to the
workspace, whether a fresh isolated environment is being created instead of
inheriting the outer one, and what interpreter version gets assumed when the
fixture declares none. Measure which of these is happening rather than picking
one; the log's "no interpreter requirement found in the workspace, defaulting"
warning is a strong hint and also appears on the passing platform, so it is not
by itself the discriminator.

TREAT THE EMPTY LINT OUTPUT AS ITS OWN DEFECT EVEN IF THE SPAWN FIX CLEARS IT.
Empty output from a tool that did not run is being reported as MALFORMED output,
which sends a reader looking for a parser bug when the real condition is that the
tool was never there. This project has been bitten repeatedly by an absent
measurement wearing the costume of a bad one. Make the message distinguish "the
tool produced nothing because it could not be run" from "the tool produced
something this parser cannot read", and cover it with a test that forces the
former.

VERIFY on macos specifically, since that is where it reproduces and where any
claim about it has to be measured. If you cannot reach a macos machine, say so
plainly and state exactly which conclusions are therefore inferred rather than
measured; do not present a linux run as evidence about a macos failure.
