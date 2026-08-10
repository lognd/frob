---
id: T-2004
title: 'A CLI flag can be parsed, tested, and silently dropped by from_external''s
  allowlist: tested is not reached'
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED, 2026-08-10, T-1995/T-2002.

T-1995 added a `--ack-related` flag to `frob ticket new`. Every one of its
tests passed. The flag NEVER WORKED end-to-end: `AppConfig.from_external`
(`src/frob/app/_config_external.py`) copies fields through a static
allowlist, and the new field was not in it, so argparse's parsed value was
silently dropped on the floor before reaching the runner.

The tests all passed because they constructed `AppConfig` DIRECTLY, bypassing
argparse and bypassing `from_external` -- i.e. they tested the function and
skipped the wiring that connects it to the CLI. Caught only by accident, when
an unrelated TEST001 finding sent someone back into the file. Fixed in T-2002
with a real argparse-parsing regression test.

SECOND INSTANCE, same week, same class: T-1977 wired
`capability_ratchet_violations` into the self-audit gate. That agent
deliberately proved it fires by calling the REAL `sys_gate` entry point
rather than the function under test -- and that care is the only reason the
wiring was known-good. Wiring the detector immediately surfaced three real
drifts that had accumulated precisely because nothing had ever invoked it.
Both cases turn on the same question: does a test exercise the PRODUCTION
ENTRY POINT, or only the symbol?

The general defect: a symbol can be fully implemented, fully tested, and
completely unreachable from the CLI, with every gate green. This repo already
has a name for the adjacent failure -- "catalogued is not enforced" (registry
YAMLs read by zero code). This is its executable twin: TESTED IS NOT REACHED.

## Do not fix it this way
- Do NOT just add `--ack-related` to the allowlist and call it done. That
  fixes one field. The defect is that the allowlist can silently disagree
  with the parser at all, for any field, with no check.
- Do NOT replace the static allowlist with a blanket `**kwargs`/dynamic copy
  to "make it impossible". That trades a loud-but-narrow bug for a silent-
  and-wide one, and destroys the allowlist's actual purpose (an explicit
  boundary about what external input may set).
- Do NOT fix it with a review-checklist line or a playbook entry. Two agents
  hit this class in one week; a written rule is not an enforcement.

## Acceptance criteria
1. A check that FAILS FIRST on a reconstructed T-1995 state: a parser flag
   that exists in argparse but is absent from `from_external`'s allowlist
   must be reported. Assert the current tree passes it (so it is a real
   ratchet), then assert the reconstructed state fails it.
2. The check compares the ACTUAL parser surface against the ACTUAL allowlist,
   derived from both, not a third hand-maintained list -- a third list is a
   new desync source (see the T-2001 ratchet-lock instance for what a
   partially-synced obligation costs).
3. Report, as measurement rather than assumption, how many CURRENT flags
   across all `frob` subcommands fail this check. If the answer is zero,
   say so and show the denominator of flags examined; if nonzero, each is a
   live silently-dead flag and needs its own accounting.
