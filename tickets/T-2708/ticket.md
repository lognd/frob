---
id: T-2708
title: 'make install-tool is broken on uv 0.11.19: uv tool install has no --extra
  flag, blocking the only sanctioned install path'
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- Makefile
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: Makefile
  reason: install-tool recipe fix
  actor: logan
  at: '2026-08-20'
- op: add
  glob: Makefile
  reason: install-tool recipe fix
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: regression test for install-tool recipe fix
  actor: logan
  at: '2026-08-20'
evidence:
- tests/unit/test_makefile_coverage.py::TestInstallToolUsesServeExtraPackageSpecNotUnsupportedFlag::test_install_tool_recipe_has_no_extra_flag
- tests/unit/test_makefile_coverage.py::TestInstallToolUsesServeExtraPackageSpecNotUnsupportedFlag::test_install_tool_recipe_uses_serve_extra_package_spec
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by a downstream consumer (aprog-public) 2026-08-20, and VERIFIED
AND FIXED by the coordinator -- the patch is written and proven, it just
needs landing from a leased worktree (a root commit was correctly refused
by the T-2071 agent-context guard).

## The bug

`Makefile:476`

    uv tool install --force --reinstall . --with ./strata-core \
        --with ./frob-core --extra serve

`uv tool install` has NO `--extra` flag. Measured on uv 0.11.19:

    $ uv tool install --help | grep -- --extra
          --extra-index-url <EXTRA_INDEX_URL>

    $ make install-tool
    error: unexpected argument '--extra' found
      tip: a similar argument exists: '--index-strategy'

Extras belong in the package spec.

## Why this is high priority despite being one line

`make install-tool` is the DOCUMENTED AND ONLY supported way to install
frob -- installing the PyPI `frob` name is a different, incomplete
package. A broken recipe leaves no supported install path at all. A
downstream consumer could not install with natives because of it.

It also CAUSED a second reported bug: their SYS004 "strata_core not
installed" stopped reproducing once this was repaired.

## The verified fix

    uv tool install --force --reinstall ".[serve]" --with ./strata-core \
        --with ./frob-core

Patch (including the stale comment above the recipe, which still described
`--extra serve`) is at:

    $CLAUDE_JOB_DIR/tmp/install-tool-fix.patch

Apply it in a leased worktree; do not retype it.

## Verified end to end, already

- `make install-tool` completes and reports "Installed 1 executable: frob"
- the tool env imports `mcp` (proving the serve extra actually applied --
  the whole point of the flag), plus `strata_core` and `frob_core`
- `frob check --only sys` in the consumer repo no longer emits SYS004;
  the .strata model parses and the gates report real findings

## Positive controls, both directions

- `make install-tool` exits 0
- the installed tool env imports `mcp` -- a fix that installs but silently
  DROPS the serve extra is a regression, and is exactly what a naive
  removal of the flag would produce