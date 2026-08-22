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
