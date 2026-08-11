---
id: T-1782
title: 'New rule: every FROB_* env var needs a doc anchor or an explicit waiver'
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
- tests/test_gates.py
- src/frob/gates/_env_var_docs.py
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'narrow package glob to the exact files this ticket touches: new gate module,
    its __init__.py wiring, the _KNOWN_GATE_RULES registry, docs, and tests'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/gates/_env_var_docs.py
  reason: 'narrow package glob to the exact files this ticket touches: new gate module,
    its __init__.py wiring, the _KNOWN_GATE_RULES registry, docs, and tests'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'narrow package glob to the exact files this ticket touches: new gate module,
    its __init__.py wiring, the _KNOWN_GATE_RULES registry, docs, and tests'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'narrow package glob to the exact files this ticket touches: new gate module,
    its __init__.py wiring, the _KNOWN_GATE_RULES registry, docs, and tests'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/modules/gates.md
  reason: 'narrow package glob to the exact files this ticket touches: new gate module,
    its __init__.py wiring, the _KNOWN_GATE_RULES registry, docs, and tests'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tests/test_gates.py
  reason: 'narrow package glob to the exact files this ticket touches: new gate module,
    its __init__.py wiring, the _KNOWN_GATE_RULES registry, docs, and tests'
  actor: logan
  at: '2026-08-11'
evidence:
- tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires
- tests/test_gates.py::TestEnvVarDocGate::test_documented_by_literal_string_is_silent
- tests/test_gates.py::TestEnvVarDocGate::test_documented_by_constant_name_is_silent
- tests/test_gates.py::TestEnvVarDocGate::test_file_scoped_waiver_covers_it
- tests/test_gates.py::TestEnvVarDocGate::test_non_frob_env_prefixed_constants_are_ignored
designated_repro_test: tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires
acceptance:
- text: given a FROB_* env var constant with no docs/ mention, when frob check runs,
    then ENV001 fires -- FAIL before this rule existed (frob.gates._env_var_docs.env_var_doc_gate
    did not exist, ModuleNotFoundError), PASS after (env_var_doc_gate reports ENV001
    for the fixture constant)
  evidence:
  - tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1611 classification: T-1610's docs-completeness sweep found
FROB_WORKER_STDOUT_LOG_LEVEL (T-0806) undocumented anywhere in docs/ for
~2 weeks (docs/audits/docs-completeness-2026-08-06.md, gap 1).

Classified as NO RULE EXISTS for this obligation, not a misfire of an
existing rule. Checked SEC110 specifically since it DOES fire on this
exact env-var read (src/frob/gates/__init__.py:6616,
`os.environ.get(_WORKER_STDOUT_LOG_LEVEL_ENV)`) -- but SEC110 asks "is
this env var a secret needing a std.secrets registry mapping", a
different question than "does this operational env var have user-facing
documentation". It fired and was correctly waived ("worker log-level
marker, not a secret") for its own question; that waiver does not cover
the doc-coverage obligation at all. COV001/COV007 also do not apply: the
constant is a private symbol (`_WORKER_STDOUT_LOG_LEVEL_ENV`), and this
repo's own convention (COV007) is that private symbols normally do NOT
carry a `frob:doc` anchor -- so an operationally user-facing `FROB_*` env
var implemented as a private constant is structurally invisible to every
existing doc-coverage gate.

Add a rule (next free id) that: enumerates every `FROB_*` string-literal
constant assigned in `src/frob/**/*.py` (same enumeration T-1610 did by
hand) and requires each to either (a) appear literally or by its owning
Python constant name in some file under `docs/`, or (b) carry an
explicit `frob:waive <RULE-ID> reason="..."` if it is genuinely internal/
not user-facing (e.g. a test-only or worker-internal flag). Model the
"documented by constant name, not literal string" allowance the T-1610
audit already established as adequate for FROB_PARSE_ARTIFACT_CACHE.

This is docs/modules/gates.md's own registry init: register the new rule
id there in the same change that implements it.