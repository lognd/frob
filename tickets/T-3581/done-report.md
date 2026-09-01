## Done report

Root cause: comprehension_id (T-3474) was never documented in the
normalized-code-model table; the waivers cited T-3481's live lease on
docs/modules/arch.md as the reason the row could not be updated at the
time. T-3481 is now done (verified via frob ticket show T-3481) and the
lease is clear, so this ticket does the deferred doc update directly
instead of converting to frob:debt.

Evidence:
- uv run frob check --only affect_drift (scoped read): before the fix
  WAIVE010 fired twice citing AFFECT001 on NormalizedCall/NormalizedBranch;
  after the fix neither WAIVE009, WAIVE010, nor AFFECT001 fire for this
  file (only a pre-existing, unrelated DOCARCH001 on NormalizedVariant
  remains).
- uv run pytest -p no:xdist tests/ -k normalized -q: 5 passed (3x rerun
  clean)
- uv run frob test: pre-existing unrelated failures only (stale
  docs/design/macos-portability.md DOC006 pointer; a shell-env-polluted
  frob-suggest test that passes standalone) -- neither touches this
  ticket's scope
- uv run frob check --ticket T-3581 --budget 300: all errors are
  repo-wide pre-existing (ratchet-lock WAIVE011 staleness, claude-config
  drift, unrelated DRIFT001/002) -- none reference _normalized.py or
  this ticket's scope

Filed: none

Gates: frob check --ticket T-3581 clean of anything attributable to this
diff (repo-wide pre-existing errors listed above, verified unrelated)

### Changed
```
 docs/modules/arch.md          |  4 ++--
 src/frob/arch/_normalized.py  |  8 --------
 tickets/T-3581/done-report.md | 45 +++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 47 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/arch_suite/test_lang_adapters.py::TestNormalizedModel::test_hand_built_python_snippet_shape` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 27 error(s), 4124 warning(s), 894 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC006@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_conftest_sigbreak_faulthandler.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_conftest_sigbreak_faulthandler.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
