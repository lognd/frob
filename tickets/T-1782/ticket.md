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
land_commit: null
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

## Done report

Added ENV001 (`frob.gates._env_var_docs.env_var_doc_gate`, gate name
`env_var_docs`, WARN severity, waivable), mechanizing what T-1610's
docs-completeness sweep did by hand when it found
`FROB_WORKER_STDOUT_LOG_LEVEL` undocumented for two weeks: enumerates
every `FROB_*` string-literal constant ASSIGNMENT under
`src/frob/**/*.py` and requires either (a) a mention under `docs/` (by
the literal env-var string or by the owning Python constant name -- the
"documented by constant name" allowance T-1610's own audit already
established as adequate) or (b) a `frob:waive ENV001 reason="..."`
directive anywhere in the same source file (file-scoped, the same
granularity `_match_waiver`'s ordinary symref-less mode already gives
every other file-scoped rule in this package).

Wired into `src/frob/gates/__init__.py` (import, both stage-name lists,
the gate dispatch table, `__all__`) and `src/frob/gates/_waive.py`'s
`_KNOWN_GATE_RULES` registry. Documented in `docs/modules/gates.md`
(rule-catalog row plus a full "ENV001 (T-1782)" section).

Evidence protocol (BUG002/T-0756 new-gate-rule acceptance), same
recipe as the T-1784 sibling ticket in this series: committed
`TestEnvVarDocGate::test_undocumented_env_var_fires` alone first
(c7ade2651) -- at that commit `frob.gates._env_var_docs` did not exist,
so the test's local import fails with `ModuleNotFoundError`, confirmed
via `frob ticket evidence T-1782 --check-repro
tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires
--base-ref c7ade2651`: FAILED_AT_PARENT. The gate implementation +
wiring + docs + remaining 4 fixture tests landed in a separate commit
(6fb7e2d1f); a follow-up commit (8f29826e5) fixed the DOCENUM001 finding
the `frob:enumerates` catalog directive raised once ENV001 joined
`_KNOWN_GATE_RULES`. Acceptance criterion 0 added with explicit FAIL/PASS
markers per the T-0756 policy, bound via `--accepts 0`.

Verified:
- `uv run pytest tests/test_gates.py::TestEnvVarDocGate -o addopts=""
  -q`: 7 passed.
- `uv run pytest tests/test_gates.py -o addopts="" -q` (full file, all
  pre-existing tests plus these 7 new ones): 726 passed, 0 failed --
  `TestKnownGateRuleIds` drift-lock tests still pass with ENV001 added.
- `uv run frob ticket evidence T-1782 --check-repro ... --base-ref
  c7ade2651`: FAILED_AT_PARENT (genuine repro).
- `uv run frob check --ticket T-1782 --only gates-fast`: DOCENUM001
  fixed by the follow-up commit above. The remaining FAILs in that
  scoped run (`gate:COV`/`gate:TEST` findings on `src/frob/__main__.py`,
  `src/frob/tickets/_land_git_ops.py`, `.claude/hooks/*`,
  `frob-core/src/*.rs`; `gate:TICK` TICK004 ticket rot) are all in
  files this ticket's own diff never touches -- pre-existing repo-wide
  floor noise (per playbook 6c's own scope-note: `--ticket` does not
  filter these families to the ticket's scope), unrelated to ENV001.

Not folded in (out of scope, disclosed): the new rule's own file-scoped
waiver granularity means a file mixing one genuinely-internal FROB_*
constant with a real user-facing one cannot waive just the internal one
without splitting it into its own module -- noted in the module
docstring and docs/modules/gates.md as a known v1 limitation, not
attempted here. Also not attempted: running env_var_doc_gate against the
real repo to burn down any pre-existing undocumented FROB_* constants it
surfaces -- that is a measurement/burn-down pass outside this ticket's
own "add the rule" scope, left for a follow-up if the WARN volume
warrants one.

### Changed
```
 docs/modules/gates.md           |  37 ++++++++++-
 src/frob/gates/__init__.py      |   9 +++
 src/frob/gates/_env_var_docs.py | 142 ++++++++++++++++++++++++++++++++++++++++
 src/frob/gates/_waive.py        |   3 +
 tests/test_gates.py             |  89 +++++++++++++++++++++++++
 tickets/T-1782/ticket.md        |  58 +++++++++++++++-
 6 files changed, 334 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_documented_by_literal_string_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_documented_by_constant_name_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_file_scoped_waiver_covers_it` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_non_frob_env_prefixed_constants_are_ignored` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV001@src/frob/__main__.py, COV001@src/frob/tickets/_land_git_ops.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2098/src/frob/gates/_root_asset_dirs.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2098/src/frob/tickets/_land.py, SELFAUDIT001@design, TEST001@src/frob/__main__.py, TICK004@tickets.md
