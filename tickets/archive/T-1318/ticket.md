---
id: T-1318
title: 'perf: telemetry redact_command pulls in the whole frob.gates package via frob.gates._secrets'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/telemetry.py
- src/frob/gates/_secrets.py
- src/frob/security/**
- tests/unit/security/**
- tests/test_telemetry.py
- tests/test_secrets_gate.py
- docs/guides/extending/secrets-scan-providers.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/security/**
  reason: 'T-1318''s fix requires extracting the secret-redaction engine (_SecretPattern,

    _PATTERNS, _redact, _scan_line, and their fake-marker/entropy helper deps)

    out of src/frob/gates/_secrets.py into a NEW lightweight module outside the

    frob.gates package tree -- exactly what the ticket''s own body proposes

    ("extract ... into a lightweight module outside frob.gates (e.g.

    frob.security._redact or similar)"). Widening scope to the new package

    (src/frob/security/**) plus one new regression test proving the import-cost

    fix (an import-graph assertion: frob.gates must never end up in

    sys.modules after importing frob.security._redact or calling

    frob.app.telemetry.redact_command), the acceptance criterion''s own explicit

    ask ("verify with an import-cost or import-graph assertion test").

    '
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/unit/security/**
  reason: 'T-1318''s fix requires extracting the secret-redaction engine (_SecretPattern,

    _PATTERNS, _redact, _scan_line, and their fake-marker/entropy helper deps)

    out of src/frob/gates/_secrets.py into a NEW lightweight module outside the

    frob.gates package tree -- exactly what the ticket''s own body proposes

    ("extract ... into a lightweight module outside frob.gates (e.g.

    frob.security._redact or similar)"). Widening scope to the new package

    (src/frob/security/**) plus one new regression test proving the import-cost

    fix (an import-graph assertion: frob.gates must never end up in

    sys.modules after importing frob.security._redact or calling

    frob.app.telemetry.redact_command), the acceptance criterion''s own explicit

    ask ("verify with an import-cost or import-graph assertion test").

    '
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/test_telemetry.py
  reason: 'T-1318''s fix requires extracting the secret-redaction engine (_SecretPattern,

    _PATTERNS, _redact, _scan_line, and their fake-marker/entropy helper deps)

    out of src/frob/gates/_secrets.py into a NEW lightweight module outside the

    frob.gates package tree -- exactly what the ticket''s own body proposes

    ("extract ... into a lightweight module outside frob.gates (e.g.

    frob.security._redact or similar)"). Widening scope to the new package

    (src/frob/security/**) plus one new regression test proving the import-cost

    fix (an import-graph assertion: frob.gates must never end up in

    sys.modules after importing frob.security._redact or calling

    frob.app.telemetry.redact_command), the acceptance criterion''s own explicit

    ask ("verify with an import-cost or import-graph assertion test").

    '
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/test_secrets_gate.py
  reason: 'T-1318''s fix requires extracting the secret-redaction engine (_SecretPattern,

    _PATTERNS, _redact, _scan_line, and their fake-marker/entropy helper deps)

    out of src/frob/gates/_secrets.py into a NEW lightweight module outside the

    frob.gates package tree -- exactly what the ticket''s own body proposes

    ("extract ... into a lightweight module outside frob.gates (e.g.

    frob.security._redact or similar)"). Widening scope to the new package

    (src/frob/security/**) plus one new regression test proving the import-cost

    fix (an import-graph assertion: frob.gates must never end up in

    sys.modules after importing frob.security._redact or calling

    frob.app.telemetry.redact_command), the acceptance criterion''s own explicit

    ask ("verify with an import-cost or import-graph assertion test").

    '
  actor: logan
  at: '2026-08-04'
- op: add
  glob: docs/guides/extending/secrets-scan-providers.md
  reason: 'T-1318''s fix requires extracting the secret-redaction engine (_SecretPattern,

    _PATTERNS, _redact, _scan_line, and their fake-marker/entropy helper deps)

    out of src/frob/gates/_secrets.py into a NEW lightweight module outside the

    frob.gates package tree -- exactly what the ticket''s own body proposes

    ("extract ... into a lightweight module outside frob.gates (e.g.

    frob.security._redact or similar)"). Widening scope to the new package

    (src/frob/security/**) plus one new regression test proving the import-cost

    fix (an import-graph assertion: frob.gates must never end up in

    sys.modules after importing frob.security._redact or calling

    frob.app.telemetry.redact_command), the acceptance criterion''s own explicit

    ask ("verify with an import-cost or import-graph assertion test").

    '
  actor: logan
  at: '2026-08-04'
evidence:
- tests/unit/security/test_redact.py::TestRedactModuleImportGraph::test_importing_redact_module_never_loads_frob_gates
- tests/unit/security/test_redact.py::TestRedactCommandImportGraph::test_calling_redact_command_never_loads_frob_gates
- tests/unit/security/test_redact.py::TestRedactCommandImportGraph::test_redact_command_still_redacts_a_real_looking_token
- tests/unit/security/test_redact.py::TestGatesSecretsStillWorksViaTheExtractedModule::test_secrets_gate_module_still_exposes_redact_and_scan_line
- tests/unit/security/test_redact.py::TestGatesSecretsStillWorksViaTheExtractedModule::test_severity_round_trips_through_the_plain_string_boundary
- tests/test_secrets_gate.py::TestRedact::test_never_returns_the_token
designated_repro_test: null
threat: null
component: null
---
found while working T-1216: after T-1216 removed frob.app's eager
deploy/strata/vet/gates import chain, one gates import still survives on
EVERY CLI invocation regardless of subcommand: `frob.app.telemetry.
timed_call`'s `finally` block always calls `record_cli_event`, which calls
`redact_command`, which does `from frob.gates._secrets import _redact,
_scan_line` -- and `frob.gates._secrets`'s own parent package,
`frob.gates/__init__.py`, eagerly imports its entire stage roster (pii,
arch, dup, vet._capability, testing, ...) as a side effect of that single
submodule import. Measured on `frob ticket list --state queued`: this
residual chain alone costs ~257ms cumulative importtime (frob.gates line
in `python -X importtime`), all AFTER the command's real output has
already been produced (it fires in telemetry's post-command bookkeeping,
not the command itself).

Root cause: redaction-worthy secret-scanning logic
(`_redact`/`_scan_line`) lives inside `frob.gates._secrets`, a submodule
of the heavy `frob.gates` aggregator package, rather than in a small
<!-- frob:waive DOC006 reason="'frob.security' is a hedged 'e.g. ... or similar' example naming one possible location for a not-yet-extracted module -- this ticket proposes the extraction, it has not happened, so no such module can exist yet to resolve against" -->
standalone module with no heavy siblings. Fix: extract `_redact`/
`_scan_line` (or whatever subset `redact_command` actually needs) into a
lightweight module outside `frob.gates` (e.g. `frob.security._redact` or
similar) that both `frob.gates._secrets` and `frob.app.telemetry` import,
so telemetry's per-invocation redaction never drags in the rest of the
gates stage roster. Out of T-1216's scope (src/frob/app/__init__.py,
src/frob/app/app.py only) -- filed as a follow-up.