## Done report

Per-capability precompiled alternation patterns (cached at load, registry
data untouched) + per-file short-circuit replace the per-candidate needle
loop; scan output proven byte-identical over all 594 files (matching md5)
and the hot path drops 33s -> 21s cumtime (full scan ~10.1s -> ~8.8s wall).

### Changed
```
 src/frob/vet/_capability.py |  50 +++++++++++++++++++--
 tickets.md                  | 107 +++++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 152 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScanBindingResolution::test_import_as_alias_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanBindingResolution::test_from_import_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanBindingResolution::test_from_import_as_detected_with_correct_kind` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanBindingResolution::test_import_as_alias_operation_names_registry_entry` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanBindingResolution::test_method_shadowing_import_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanBindingResolution::test_param_shadowing_import_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanBindingResolution::test_local_variable_shadowing_import_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanBindingResolution::test_bare_name_call_with_no_import_not_detected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 0 error(s), 1129 warning(s), 207 waived
