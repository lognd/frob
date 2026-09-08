---
id: T-4299
title: add a path-reporting verb naming the running frob's own interpreter/site-packages
  location
state: in-progress
kind: feature
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/__main__.py
- src/frob/app/__init__.py
- src/frob/_cli_parsers/_core.py
- src/frob/_cli_parsers/_root.py
- src/frob/_cli_parsers/__init__.py
- tests/unit/test_main_entry.py
- README.md
- docs/modules/app.md
- docs/modules/cli.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: 'measured exhaustively: frob agent/worktree/bind precedent shows a direct-dispatch
    verb registers its parser in _cli_parsers/_core.py, is wired into _add_analysis_subparsers
    in _cli_parsers/_root.py (for --help discoverability, T-3125 precedent), and is
    re-exported through _cli_parsers/__init__.py; __main__.py needs the dispatch branch.
    tests/unit/test_main_entry.py already has an exhaustive TestHelpListsDirectDispatchVerbs
    class this ticket extends; tests/system/test_cli_check.py is the every-verb-reachable
    coverage the ticket body names as a candidate to check'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/_cli_parsers/_root.py
  reason: 'measured exhaustively: frob agent/worktree/bind precedent shows a direct-dispatch
    verb registers its parser in _cli_parsers/_core.py, is wired into _add_analysis_subparsers
    in _cli_parsers/_root.py (for --help discoverability, T-3125 precedent), and is
    re-exported through _cli_parsers/__init__.py; __main__.py needs the dispatch branch.
    tests/unit/test_main_entry.py already has an exhaustive TestHelpListsDirectDispatchVerbs
    class this ticket extends; tests/system/test_cli_check.py is the every-verb-reachable
    coverage the ticket body names as a candidate to check'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: 'measured exhaustively: frob agent/worktree/bind precedent shows a direct-dispatch
    verb registers its parser in _cli_parsers/_core.py, is wired into _add_analysis_subparsers
    in _cli_parsers/_root.py (for --help discoverability, T-3125 precedent), and is
    re-exported through _cli_parsers/__init__.py; __main__.py needs the dispatch branch.
    tests/unit/test_main_entry.py already has an exhaustive TestHelpListsDirectDispatchVerbs
    class this ticket extends; tests/system/test_cli_check.py is the every-verb-reachable
    coverage the ticket body names as a candidate to check'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: 'measured exhaustively: frob agent/worktree/bind precedent shows a direct-dispatch
    verb registers its parser in _cli_parsers/_core.py, is wired into _add_analysis_subparsers
    in _cli_parsers/_root.py (for --help discoverability, T-3125 precedent), and is
    re-exported through _cli_parsers/__init__.py; __main__.py needs the dispatch branch.
    tests/unit/test_main_entry.py already has an exhaustive TestHelpListsDirectDispatchVerbs
    class this ticket extends; tests/system/test_cli_check.py is the every-verb-reachable
    coverage the ticket body names as a candidate to check'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/system/test_cli_check.py
  reason: 'measured exhaustively: frob agent/worktree/bind precedent shows a direct-dispatch
    verb registers its parser in _cli_parsers/_core.py, is wired into _add_analysis_subparsers
    in _cli_parsers/_root.py (for --help discoverability, T-3125 precedent), and is
    re-exported through _cli_parsers/__init__.py; __main__.py needs the dispatch branch.
    tests/unit/test_main_entry.py already has an exhaustive TestHelpListsDirectDispatchVerbs
    class this ticket extends; tests/system/test_cli_check.py is the every-verb-reachable
    coverage the ticket body names as a candidate to check'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: tests/system/test_cli_check.py
  reason: 'measured: this file tests frob check CLI flags only, no top-level verb
    enumeration relevant to whereis; not needed'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: README.md
  reason: 'gate:DOC DOC005/DOC012 findings: README command table + generated cli.md
    table + a dedicated Runners-section doc bullet for the new frob whereis verb'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/app.md
  reason: 'gate:DOC DOC005/DOC012 findings: README command table + generated cli.md
    table + a dedicated Runners-section doc bullet for the new frob whereis verb'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/cli.md
  reason: 'gate:DOC DOC005/DOC012 findings: README command table + generated cli.md
    table + a dedicated Runners-section doc bullet for the new frob whereis verb'
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4150 (frob exports a public Python API no consumer can import) named a
path-reporting verb -- one that prints the interpreter/site-packages path
of the frob actually running -- as its third acceptance criterion, but
T-4150's own coordinator note deliberately excluded building it from that
ticket's scope:

"The wiring for the path-reporting verb is NOT in scope yet, because the
number of places a new verb must be registered is not obvious from
outside: this repository has already had a defect where a verb was added
and missed several of the lists that enumerate verbs, so guessing the
file set here would either over-claim leases or under-claim them. Measure
what the verb actually needs, then widen with a recorded reason."

This ticket picks that up as its own dedicated unit of work. Per
docs/modules/gates.md's "Registering a new gate" section (T-4163) and the
analogous verb-registration lists frob.app's dispatch table uses, measure
EVERY place a new top-level verb (name + subcommand parser + dispatch
entry + help text + any enumeration list) must be registered before
touching any of them -- do not guess the file set from outside. Candidates
to check, not to assume complete: `src/frob/__main__.py` (top-level
argparse wiring), `src/frob/app/__init__.py` (the `_RUNNER_RUN_MODULES`
dict and `_import_runner_run_module`'s closed if/elif chain -- see T-4297,
filed the same day, for a live example of exactly this class of
registration-list defect), any `--help`/usage-string enumeration, and
`tests/system/test_cli_check.py`-style "every verb is reachable" coverage
tests if one exists for the top-level command table (not just `--only`
stage groups).

The verb itself: print `sys.executable` and/or `site.getsitepackages()`
(or the frob package's own `__file__`/install location) for the CURRENTLY
RUNNING frob -- not a hardcoded assumption -- since this repo already
warns elsewhere that the invoked binary's source identity may not match a
given checkout (the CLI-surface-skew warning `frob --version` alone
cannot detect, per the frob-usage reference). This turns a consumer's
fragile `shutil.which`-based tool-venv shim (the real-world workaround
T-4150's report describes) into a supported one-liner.

Acceptance:
- The verb reports the running frob's own interpreter/site-packages path,
  verified by invoking it from two different installs and asserting they
  report different paths.
- The verb is reachable from every enumeration/dispatch list a new verb
  needs (measured exhaustively first, not assumed).
