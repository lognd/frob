---
id: T-3304
title: FEATURE-kind implicit_scope hardcodes frob's own CLI-wiring paths in consumer
  repos
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- src/frob/app/ticket_runner/_query.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-028).

`frob ticket show` prints an `implicit_scope: [...]` line for FEATURE-kind
tickets (src/frob/app/ticket_runner/_query.py::_render_implicit_scope) built
from `CLI_WIRING_FILES` (src/frob/tickets/_models.py, T-0446/T-1848). That
constant is HARDCODED to frob's own package layout
(src/frob/__main__.py, src/frob/app/config.py,
src/frob/app/ticket_runner/__init__.py). In a consumer repo like diax, every
FEATURE ticket shows this exact same implicit_scope line naming paths that
DO NOT EXIST in that repo (diax's real CLI-wiring files are
src/diax/__main__.py, src/diax/app/config.py, etc.) -- the grant is not
resolved from the consumer project's own layout at all.

WHAT NOT TO DO: do not just make `CLI_WIRING_FILES` project-relative by
string substitution ("frob" -> the consumer package name) -- that assumes
every consumer project mirrors frob's own internal module layout
(app/config.py, app/ticket_runner/__init__.py), which is an accident of
frob's structure, not a general convention.

WHAT TO BUILD: resolve the FEATURE-kind CLI-wiring grant from the CONSUMER
project's actual entrypoint/config layout (e.g. via the project's declared
`[[refs.entrypoint]]` config, or by locating its actual `__main__.py`/CLI
parser module), falling back to frob's own hardcoded list only when checking
frob's own repo. Confirm in the Done report whether this needs new
project-level config or can be derived from what frob.toml already declares.

MUST-FIRE FIXTURE: `frob ticket show` on a FEATURE ticket in a consumer repo
with its own `src/<pkg>/__main__.py` -- implicit_scope must name that repo's
real CLI-wiring files, not frob's.

MUST-STAY-QUIET FIXTURE: run inside frob's own repo -- implicit_scope
unchanged from today.
