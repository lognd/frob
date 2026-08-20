---
id: T-2707
title: SYS004 replaces the real ImportError with a hardcoded not-installed message,
  misdirecting diagnosis
state: queued
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
- src/frob/strata/_parse.py
- src/frob/strata/_facts.py
- src/frob/strata/_errors.py
- src/frob/strata/_design_load.py
- src/frob/gates/_sys.py
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_parse.py
  reason: capture+propagate the real strata_core ImportError through DesignLoadError
    into the SYS004 message, instead of only ever printing the fixed not-installed
    hint
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/strata/_facts.py
  reason: capture+propagate the real strata_core ImportError through DesignLoadError
    into the SYS004 message, instead of only ever printing the fixed not-installed
    hint
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/strata/_errors.py
  reason: capture+propagate the real strata_core ImportError through DesignLoadError
    into the SYS004 message, instead of only ever printing the fixed not-installed
    hint
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/strata/_design_load.py
  reason: capture+propagate the real strata_core ImportError through DesignLoadError
    into the SYS004 message, instead of only ever printing the fixed not-installed
    hint
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/gates/_sys.py
  reason: capture+propagate the real strata_core ImportError through DesignLoadError
    into the SYS004 message, instead of only ever printing the fixed not-installed
    hint
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/strata/surface.md
  reason: sys004 message-detail doc anchor already lives here
  actor: logan
  at: '2026-08-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by a downstream consumer repo (aprog-public) on frob 0.530.0,
2026-08-20.

## Symptom

    SYS004: design/aprog-public.strata failed to load (The strata_core
    native extension is not installed (a standalone `uv tool install frob`
    with no natives) ...)

The reporter demonstrated strata_core WAS installed and importable, then
reinstalled with natives and saw no change. The hardcoded explanation sent
them down the wrong path entirely.

## Verified masking site

`src/frob/strata/_parse.py:15-22`

    try:
        strata_core: ModuleType | None = importlib.import_module("strata_core")
    except ImportError:                      # <-- exception discarded
        strata_core = None

Both guards (`_parse.py:47` and `_facts.py:554`) then test only
`strata_core is None` and return the fixed string
`StrataError.NativeExtensionUnavailable` from `_errors.py:119`.

So ANY ImportError -- including a symbol/ABI mismatch or a failing
SECONDARY import inside the module, which also raise ImportError -- is
reported as "you installed without natives". The one cause named in the
message displaces every other cause.

## Status of the reporter's immediate symptom

Their SYS004 no longer reproduces after `make install-tool` was repaired
(the recipe was broken outright on uv 0.11.19 -- see the install-tool
ticket). So the proximate cause was a broken install path.

That does NOT close this ticket. The diagnostic-masking defect is real,
independently verified in code above, and it is what made a
straightforward environment problem cost a wrong-path debugging session.
Fix the masking.

## Fix direction

Capture the caught exception and report it ALONGSIDE the friendly hint,
rather than replacing it. The hint is useful -- it is the common case --
but it must not be presented as the only possibility. Preserve the typed
`Result` contract; this is about the message and the log, not about
raising.

## Positive controls, both directions

- strata_core genuinely absent: message still names the missing-natives
  case (the common, useful hint is not lost)
- strata_core present but raising a DIFFERENT ImportError (e.g. a stubbed
  module whose own import fails): the message reports THAT exception, and
  does not claim the extension is uninstalled
- a successful import: no error, no log noise
