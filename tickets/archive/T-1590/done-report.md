## Done report

Three real suite failures, all "code moved, declaration did not":

1. tests/unit/test_extending_guides_complete.py: the secrets-scan-providers
   inventory row (docs/guides/extending/registry_of_registries.json) and
   the drift-lock test's own _REGISTRY_PROBES table both still named
   src/frob/gates/_secrets.py::_SecretPattern as the anchor, but
   _SecretPattern actually lives in src/frob/security/_redact.py (imported
   into _secrets.py, not defined there) -- and that module already carries
   the correct frob:doc anchor back to the guide. Retargeted both the
   inventory row's anchor_file and the test's probe entry to
   src/frob/security/_redact.py; no source or guide prose changed.

2. tests/unit/test_exports.py::TestFrobExportsPolicyResidue: src/frob/doctor.py
   grew LiveLandProcess/scan_live_land_processes (T-1515) without adding
   them to src/frob/__init__.py's re-export block and __all__. Added both,
   alphabetically placed alongside the package's existing doctor.py
   re-exports; both symbols already carry their own docstrings.

3. tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known:
   two rule-id literals the T-1010 static scan now finds were never
   registered:
   - "E501" (src/frob/gates/_fix_engine.py's targeted-ruff-format
     land-merge auto-fix, T-1547) is a real, legitimately emitted rule
     literal -- added to _KNOWN_GATE_RULES (src/frob/gates/_waive.py).
     frob check --only registry then flagged REG010 (no CHK-GATE-E501
     registry entry) and REG008 (no frob:enforces edge) for the new id;
     resolved with `frob registry audit --sync-gate-rules` plus a
     `frob:enforces CHK-GATE-E501` directive on
     fix_e501_merge_introduced.
   - "TIERBDEMO001" (src/frob/gates/_fix_engine_tier_b.py) already carries
     an explicit WIRE001 waiver stating it must never be registered as a
     real gate rule (T-1481, purely a synthetic Tier-B wiring demo id).
     Since the drift-lock test requires every id the scan finds to be
     either known or retired, added it to
     frob.gates._rule_id_scan.RETIRED_RULE_IDS (the documented mechanism
     for "kept out of the generated set on purpose") rather than pasting
     it into _KNOWN_GATE_RULES, which would have contradicted its own
     waiver comment.

Verification: targeted pytest runs for all three failing files/classes
(6+1+6 = 13 node ids, all now pass), `frob check --only test --ticket
T-1590` (0 errors), `frob check --only doclink --only docanchor --only
registry --ticket T-1590` (0 errors after the registry sync + enforces
edge). Did not run the full unscoped suite (playbook 3b/3c budget) --
that is T-1591's job and the coordinator's land-time job.

### Changed
```
 tickets.md | 10 ++++++++--
 1 file changed, 8 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_row_anchor_file_exists_and_mentions_guide` (pytest node id, verified passing when recorded)
- `tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_anchor_fragment_resolves_to_guide_h1` (pytest node id, verified passing when recorded)
- `tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_probe_still_matches_source` (pytest node id, verified passing when recorded)
- `tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_probe_table_and_inventory_agree` (pytest node id, verified passing when recorded)
- `tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 6836 warning(s), 785 waived
- error-findings: none (measured, zero errors)
