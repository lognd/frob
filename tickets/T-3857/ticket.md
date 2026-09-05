---
id: T-3857
title: 'frob serve is broken against mcp 2.x: the serve extra pins mcp unbounded,
  so a fresh resolve ships a failing import'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- pyproject.toml
- docs/guides/release.md
- tests/unit/test_dependency_pins.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: pyproject.toml
  reason: bound mcp pin in serve extra + dev group; decision doc; fixture for unbounded-pin
    regression
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/guides/release.md
  reason: bound mcp pin in serve extra + dev group; decision doc; fixture for unbounded-pin
    regression
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_dependency_pins.py
  reason: bound mcp pin in serve extra + dev group; decision doc; fixture for unbounded-pin
    regression
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported as stpone FROBLEMS F-001. CONFIRMED, and it is already breaking real
sessions -- including this coordinator session, whose system prompt reported the
frob MCP server as `frob (CONNECTION_CLOSED): "Connection closed"` at startup.
That failure had been recorded as a generic connection problem; F-001 gives it a
cause.

THE DEFECT. pyproject.toml declares an unbounded lower-bound pin in two places:

    pyproject.toml:50    serve = ["mcp>=1.28.1"]
    pyproject.toml:128   "mcp>=1.28.1",          (dev group)

mcp 2.x RENAMED FastMCP to MCPServer. The serve adapter imports
`mcp.server.fastmcp`, so any environment that resolves mcp to 2.x gets:

    ERROR: serve: mcp SDK not installed: No module named 'mcp.server.fastmcp'.
    This is mcp 2.x, where FastMCP was renamed to MCPServer ...

The reporter's tool environment holds mcp 2.1.1 and `frob serve` exits 1.

WHY THIS REPO DOES NOT SEE IT: measured here 2026-09-05, this checkout resolves
mcp 1.28.1, so `frob serve` works locally and every gate is green. The break is
invisible from inside the repo and appears only in a freshly-resolved
environment -- which is exactly what a user installing the published `[serve]`
extra gets. THAT MAKES IT A RELEASE BLOCKER FOR THE ALPHA: the extra ships an
import that fails against the current mcp release.

THE FIX, per the reporter and it is right: bound the pin.

    serve = ["mcp>=1.28.1,<2"]

and the same bound in the dev group, until the adapter is ported to the 2.x API.
Do BOTH; a dev-group-only fix leaves the published extra broken, and a
published-extra-only fix means CI never exercises what users get.

DECIDE AND STATE, do not just add the bound:
  - Is porting the adapter to mcp 2.x in scope for the alpha, or explicitly
    after it? The rename (FastMCP -> MCPServer) suggests a small port, but do
    not assume the rest of the 2.x surface is compatible -- check before
    promising either answer. If it is deferred, file the port with the bound
    cited as its trigger.
  - Should the error message stay? It is GOOD: it names the exact cause and the
    rename rather than a bare ImportError. Keep it even after the pin, because
    a user can still force mcp 2.x. This is the rare case where a clear failure
    message earned its keep -- say so rather than deleting it as dead code once
    the pin makes it unreachable in normal resolution.

THE WIDER QUESTION, worth one measurement rather than a guess: how many other
dependencies carry an unbounded lower-bound pin whose next major could break an
import the same way? pyproject's `dependencies` list is short. Enumerate the
unbounded ones and report which have had a major release since their floor. Do
NOT bulk-add upper bounds -- that creates resolution pain for consumers and is a
real cost -- but a list of "unbounded and upstream has moved a major" is the
input to deciding which deserve one.

MUST-FIRE FIXTURE:   an environment resolving mcp 2.x is refused at resolution
                     time by the pin, rather than failing at import.
MUST-STAY-QUIET:     mcp 1.x still installs and `frob serve` starts.

ACCEPTANCE
- Both pins bounded.
- The port-now-or-later decision stated, with the 2.x surface actually checked.
- The unbounded-dependency enumeration reported.
- Fixtures committed.
- Verify against a CLEAN resolve, not this checkout -- this checkout already
  holds 1.28.1 and will pass either way, which is precisely why the break was
  invisible.
