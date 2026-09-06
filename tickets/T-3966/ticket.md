---
id: T-3966
title: 'ENVVAR003: config constructed outside its designated site'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-3942
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a settings/config class instantiated directly outside its designated
    from_external/from_env construction site and outside test files, when frob check
    runs, then ENVVAR003 fires naming the construction site
  evidence: []
- text: given a construction call inside the designated site or a test file, when
    frob check runs, then the rule stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-182 (T-3942 item 8). Distinct from the first audit's ENVVAR002 (T-3919 item 8, filed separately: "every AppConfig field has a non-test reader"). This one is about CONSTRUCTION, not reading: a config field read off a LOCALLY-CONSTRUCTED default instance (e.g. `Settings()` built inline somewhere instead of the one true `from_external`/`from_env`-produced instance) is itself a finding, independent of whether the field is read anywhere.

WHY THIS MATTERS OUT OF PROPORTION TO ITS SIZE (the consumer's own framing): it SILENTLY DEFEATED A LANDED SECURITY FIX, and it passes BOTH the existing env-var sync gate and the first audit's proposed ENVVAR002 -- neither of those rules would have caught it, because both check that the field is documented/read somewhere, not that every live code path actually goes through the one construction site meant to apply real config.

FINDING THIS WOULD HAVE CAUGHT: a settings/config class instantiated directly (bare `Settings()` or equivalent) at a call site outside `from_external`/`from_env`/test fixtures, so a security-relevant default (rather than the real deployed value) silently governs behavior. Narrow and mechanical per the consumer: flag any construction of the settings/config class found outside its designated construction path(s) and test files. frob's own AppConfig/from_external (src/frob/app/config.py) is a reference shape for what "the one true construction site" looks like, useful as a positive-control fixture when building the detector, even though the rule itself targets consumer code shapes generically.
