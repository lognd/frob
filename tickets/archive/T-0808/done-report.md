## Done report

Added WAIVE007 (WARNING-tier): a waiver whose binding ticket ref
(`ticket=`/`ticket "..."` attribute, or WAIVE006's binding-phrase
extraction in the reason text) resolves to no ticket at all in the
active+archive ledger. Mirrors WAIVE006's two-channel shape
(`_waive007_comment_violations` for `frob:waive` comments,
`_waive007_strata_violations` for `.strata` `waive` clauses,
combined by `waive007_gate`), reusing `_waive006_binding_ticket_refs`
so the binding-vs-historical-mention calibration is not duplicated.

Exemption design: every `T-draft-*` id is exempt from WAIVE007
unconditionally -- the simpler of the two options the ticket offered,
chosen and documented in the module comment above
`_waive007_is_exempt_dangling_ref`. A narrower "exempt only if a live
worktree lease still claims this draft id" rule was considered and
rejected: it would make the gate depend on `frob.tickets._leases`
state that is worktree-local and routinely absent in the very runs
(a landed/merged checkout, CI, another agent's worktree) where the
gate needs to be trustworthy, making the exemption itself
environment-dependent. `T-draft-*` ids are worktree-local transients
by construction (minted only inside an active worktree, always
renumbered to a real `T-####` id at `frob ticket land`), so any
`T-draft-*` id a gate run observes is either still in-progress (not
a dangling reference) or was already renumbered away and is now
permanently unresolvable by design -- the same "out of scope" shape
WAIVE006 already applies to unresolvable ids generally.

Registered WAIVE007 in `_KNOWN_GATE_RULES`, wired `waive007_gate`
into the WAIVE00*-self-check group in `run_gates` (same dependency
shape as WAIVE006: snapshot waive edges + merged ticket queue only),
and exported `waive007_gate` from `__all__`.

Registry: added `CHK-GATE-WAIVE007` to
`docs/design/registry/check-coverage.yaml` (mirroring
`CHK-GATE-WAIVE006`) and bumped `gate_rule_total` 105 -> 106. This
file was added to T-0808's scope via `frob ticket scope --add
--reason-file` (not originally declared) since the new gate rule id
needs a registry entry to satisfy REG002 (`handled_by:<rule>` names
a rule id absent from the live gate set).

Tests: `tests/test_waive_gate.py` gained
`TestWaive007ExemptDanglingRef`, `TestWaive007CommentChannel`,
`TestWaive007StrataChannel`, `TestWaive007Registration`, and
`TestWaive007RealRepo` (15 tests total), mirroring the existing
WAIVE006 test classes' structure and fixture helpers exactly. The
real-repo calibration test (`test_zero_findings_on_real_repo`) is
the proof the ticket demanded: WAIVE007 fires zero findings against
this repo's own live `design/frob.strata` and `frob:waive` comments
-- main has no dangling binding refs left after the T-0803
draft-id retarget.

Verification: `uv run --frozen pytest tests/test_waive_gate.py
tests/test_gates.py -q` -> 74 passed (34 in test_waive_gate.py + 40
in test_gates.py). `uv run --frozen frob check --ticket T-0808`
chunked per section 3b/playbook (`--only prework`, `gates-fast`,
`gates-native`, `gates-security`, `lint`, `static`) -> every stage
group 0 errors; `gate:WAIVE` 0 errors throughout (no new WAIVE007
findings on the real repo, consistent with the calibration test).
`uv run --frozen ruff format` clean on both changed files after one
initial reformat of the test file.

Deviations: none from the ticket's plan. `docs/design/registry/
check-coverage.yaml` was added to scope via the CLI (see above)
since it was not in the ticket's originally declared scope but is
required by the "registry entry" plan item.

### Changed
```
 docs/design/registry/check-coverage.yaml |   6 +-
 src/frob/gates/__init__.py               | 157 +++++++++++++++++++++++
 tests/test_waive_gate.py                 | 212 +++++++++++++++++++++++++++++++
 3 files changed, 374 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)
