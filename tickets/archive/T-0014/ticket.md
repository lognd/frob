---
id: T-0014
title: Annotate legacy modules (app/, check/, process/, etc) to flip COV001 back to
  error
state: dropped
kind: docs
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/**
- src/frob/check/**
- src/frob/process/**
- src/frob/map/**
- src/frob/outline/**
- src/frob/xref/**
- src/frob/cycle/**
- src/frob/dup/**
- src/frob/scaffold/**
- src/frob/bind/**
- src/frob/arch/**
- src/frob/gitlog/**
- src/frob/exports/**
- src/frob/docs/**
- src/frob/ast/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
COV001/TEST001/TEST002/TEST003/TEST005/TEST006 were fixed as ERROR in gates code (src/frob/gates/__init__.py has no per-rule severity override mechanism read from frob.toml -- see T for that gap) but fire thousands of times on legacy pre-gates modules. Since severity cannot be config-overridden today, real convergence on the legacy surface requires actually annotating (frob:doc/frob:tests) the legacy public API, module by module, not just the new core covered by this dogfood milestone.

DEFERRED BY DESIGN: annotate legacy to flip COV001 to error makes frob's OWN gates stricter. frob is
a churning 0.1.0a0 alpha; the feature (severity dial / convention
inference) ships and works -- adopting max strictness on frob itself is
a project-maturity decision for post-alpha, not a build task. Same
reasoning as not committing .frob-release.json.