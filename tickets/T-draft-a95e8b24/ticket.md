---
id: T-draft-a95e8b24
title: Logging by project package name, App startup wiring, real AppConfig fields,
  and a docblocks commands entry
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4763
parent: T-4757
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/shared/python/logging/**
- src/frob/scaffold/data/types/python-tool/app/**
- src/frob/scaffold/data/types/python-tool/__main__.py.j2
- src/frob/scaffold/data/types/python-tool/frob.toml.j2
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given two projects rendered with different names, when their logging modules
    are loaded, then their root logger names differ and each equals its own package
    name
  evidence: []
- text: Given the rendered entry point is run, when logs are captured, then at least
    one record is emitted at startup
  evidence: []
- text: Given the rendered python-tool, when frob check runs, then FLAGCOV001 is measured
    rather than unresolved
  evidence: []
- text: Given the rendered AppConfig, when an unknown field is supplied, then the
    configured behaviour is observed, proving the model configuration is in effect
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The shipped logging module conforms to refs/logging.md and is never CALLED:
the generated App, its entry point and the config loader contain zero log
lines (audit conformance row LOG EVERYTHING). Worse, the root logger name
and the config key are fixed strings rather than the project's own package
name, so two scaffolded projects in one process would share a logger.

1. Render the shared logging module with the PROJECT PACKAGE NAME as the
   root logger name and as the config key -- never a fixed name.
2. The App template calls logging setup at startup, so a fresh project logs
   from line one, and instruments the branches that exist: startup,
   shutdown, config source chosen, and every error path.
3. AppConfig gets real fields and the pydantic v2 model configuration form
   per refs/pydantic.md, replacing today's field-less model that also
   carries no model configuration at all. Follow refs/python-app.md for the
   App and AppConfig split and for deferring heavy imports into the call
   method.
4. python-tool emits a docblocks commands entry so FLAGCOV001 is MEASURED
   rather than permanently unresolved -- python-tool is the only type that
   ships a CLI, so it is the only type where that gate can be satisfied.

Positive controls:
1. two projects rendered with different names produce different root logger
   names, asserted on the logger name string;
2. running the rendered entry point emits at least one record at startup,
   captured through a log-capture fixture;
3. the rendered python-tool reports FLAGCOV001 as measured, not unresolved,
   in frob check output;
4. the rendered AppConfig rejects an unknown field (or accepts it, per the
   configured behaviour) -- asserted, so the model configuration is proven
   to be in effect rather than merely present.
