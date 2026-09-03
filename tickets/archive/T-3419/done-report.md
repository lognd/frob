## Done report

Investigation (per the body's "do not skip to a fix" ordering):

1. SELFAUDIT001 is present in the sweep's rule set but forms an unstable
   identity: `frob.gates._sys_selfaudit._selfaudit_violation` builds
   every SELFAUDIT001 `Violation` with `file=design_dir` (src/frob/gates/
   _sys_selfaudit.py:97, also :339 for the compliance sub-family) --
   `design_dir` is the constant `"design"` string (src/frob/gates/
   _sys.py:110), never the real offending file, so every SELFAUDIT001
   finding repo-wide collapses onto the single `("SELFAUDIT001",
   "design")` identity in `_error_finding_identity`
   (src/frob/app/ticket_runner/_verify.py, pre-fix). Confirmed with a
   MUST-FIRE fixture that fails on main: reverted the fix locally,
   re-ran the test, and `new_identities` came back `frozenset()` where
   it must equal `{("SELFAUDIT001", "src/frob/nodeid.py")}` -- restored
   after confirming.

2. Enumeration: searched every `Violation(...)` call site across
   src/frob/gates/*.py for a `file=` argument bound to a directory-shaped
   constant (no extension) shared across a LOOP producing more than one
   distinct violation -- the actual collapse-risk shape, as opposed to a
   single load-error violation genuinely anchored at one real config
   file (pyproject.toml/frob.toml/tickets.md/decisions/ -- those are
   real single-condition anchors, not per-item collapses). Found:
   - SELFAUDIT001 (src/frob/gates/_sys_selfaudit.py:97,339) -- FIXED here.
   - INV051 (src/frob/gates/_policy_weakening_gate.py:130) -- SAME
     shape, `file=design_dir` inside a loop over `find_policy_
     weakenings` results, but its message names policy ids, never a
     real file path, so this ticket's message-extraction mechanism
     cannot recover a distinguishing identity for it. Filed as a
     follow-up (T-3460), not fixed here -- a real fix needs
     resolving policy_id back to its declaring .strata file, the same
     `node_file` map pattern `frob.gates._vmodel._vmodel_violations`
     already uses for VMOD001 (T-3264), a bigger rule-specific change,
     not a surgical diff.
   - VMOD001 (src/frob/gates/_vmodel.py) had the identical shape and was
     ALREADY fixed one rule at a time via T-3264's `node_file` map
     (src/frob/gates/_vmodel.py:234) -- precedent for the per-rule
     approach this ticket's own body explicitly forbids repeating
     generically.

3. Fix: general, not per-rule-id. `_error_finding_identity`
   (src/frob/app/ticket_runner/_verify.py) now checks whether
   `diagnostic["file"]` LOOKS anchor-shaped (`_looks_like_shared_anchor`:
   no extension on its final path component, or a trailing `/`) -- a
   structural, filesystem-independent test (root is not threaded down
   this call chain) that flags ANY rule reporting this way, not one rule
   id. When anchor-shaped, it extracts the first repo-relative path
   token from the diagnostic's own `message`
   (`_real_file_from_message`/`_MESSAGE_PATH_RE`) and uses that as the
   identity's file component instead; when no such token is found (the
   INV051 case), it degrades unchanged to the pre-fix shared-anchor
   identity -- never raises, never drops the finding.

Both MUST-FIRE and MUST-STAY-QUIET fixtures committed
(TestErrorFindingIdentityOffFileAnchors in
tests/unit/test_ticket_runner_gate_findings.py), plus a control proving
an ordinary per-file finding is unaffected.

Filed: T-3460 (INV051's own instance of this class).

`frob check --ticket T-3419` and unscoped `frob test` both exceeded
their budgets under heavy fleet contention (multiple concurrent `frob
check` processes on the host); relying on the targeted pytest run
(11/11 passed, `-p no:xdist`, all 7 cited evidence node ids plus the 4
pre-existing sibling controls in the same module) instead, per the
standing instruction to rely on scoped runs past that point.

### Changed
```
 tickets/T-3419/ticket.md           | 10 +++++++++-
 tickets/T-3460/ticket.md | 30 ++++++++++++++++++++++++++++++
 2 files changed, 39 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_ticket_runner_gate_findings.py::TestErrorFindingIdentityOffFileAnchors::test_must_fire_new_selfaudit001_finding_not_deduped_against_unrelated_one` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestErrorFindingIdentityOffFileAnchors::test_must_stay_quiet_no_message_path_falls_back_to_shared_anchor` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestErrorFindingIdentityOffFileAnchors::test_ordinary_per_file_finding_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_blank_identity_diagnostic_is_dropped_not_added` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_drop_is_logged_naming_the_emitting_tool` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_a_diagnostic_with_only_file_set_is_kept` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_ty_and_gate_error_both_appear_in_parsed_set` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 13 error(s), 4461 warning(s), 861 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3419, REL001@src/frob/__init__.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
