---
id: T-4757
title: 'Scaffold: derived wrappers and [commands], green day one, facets with discoverable
  recommendations, web-service preset, style conformance'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-2964
tier: story
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the 14 child leaves are closed, when a fresh project of every registered
    type is rendered and git-initialised, then frob check is clean and no Makefile
    target contains anything but a single run-verb call plus bootstrap
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Story for the scaffold surface, from the 2026-09-19 template audit
(scratchpad SCAFFOLD-AUDIT.md, every claim rendered and measured) plus the
owner's binding decisions of 2026-09-19 19:00.

Measured starting state: 7 of 8 registered types render, all 7 are RED on a
fresh frob check (5-19 errors each); 6 of 7 ship a full make
format/lint/typecheck/test/check surface the owner forbids; 39 bare TODO
markers ship into every new project; four of five frob.toml templates lost
the [[refs.entrypoint]] block by forking shared/python, which alone accounts
for 11-12 REF001 per non-python type; typani is declared and never used;
the shipped logging module is never called; unity-project is unreachable
from the CLI.

Five decisions this story executes:

1. Wrappers are DERIVED, never authored. frob.toml gains a [commands] table
   mapping a name to a command; frob-native verbs are the defaults, so a
   Python project declares nothing and a cpp or cargo project declares
   build and test once. A planned run verb executes an entry and a planned
   build verb delegates to it. A planned scaffold apply regenerates Makefile
   and make.bat as managed blocks whose every target is a one-line call to
   the run verb, with bootstrap (uv sync, cmake configure) as the only
   hand-written target. A drift gate fails frob check when a wrapper target
   and the [commands] table disagree. This replaces every Makefile.j2.

2. Green on day one is a requirement, proven by a scaffold test that renders
   every type, runs git init, and requires a clean frob check.

3. typani floor rises to the latest published release, 0.2.3 (PyPI JSON,
   2026-09-19), and python-tool demonstrates it.

4. Logging is built in: the shared logging module is rendered with the
   PROJECT PACKAGE NAME as root logger name and config key, and the App
   template calls it at startup.

5. Facets before web-service. The managed-block engine
   (src/frob/scaffold/_managed.py) becomes a facet system per audit 6.1/6.2;
   types become presets; web-service is then a preset, not an eighth fork.

Deferred and dropped deliberately: python-monorepo deferred (audit 6.5 item
5, the facet-contributes-to-which-pyproject question is unanswered);
infra/terraform dropped (no house style exists for HCL); docs-site becomes a
facet, never a type; frob-plugin stays blocked on T-4661.

Parented under T-2964 because that epic is the consumer-facing portability
surface, and a scaffolded project is the first thing a consumer ever sees.
There is no scaffold-specific epic in the queue.
