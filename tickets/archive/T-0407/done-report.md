## Done report

Unified `docs/design/registry/*.yaml` onto one typed model (`frob.registry._models`:
`Disposition`/`DispositionKind`, `RegistryEntry`, `RegistryFile`, `RegistryAudit`,
`load_registry_dir`, `parse_disposition`, `audit_registry_file`) instead of the
regex-based parser that lived inline in `frob.gates._registry_exhaustiveness`.
`registry_gate` (T-0343) was refactored onto this model rather than kept as a
second, duplicated parser -- it is now purely the policy layer (which
`DispositionKind` earns which `Violation`, verified against live gate-rule ids
and the ticket queue).

Closed two early-exit/partial-coverage holes the pre-unification gate silently
allowed (the ticket's own root-cause framing): REG006 (a list item that is not
a mapping, or has no string `id`, previously vanished from every count with a
silent `continue`) and REG007 (the same `id` defined by two-plus entries
anywhere in the registry -- a real collision, distinct from an intentional
`duplicate_of:` reference REG004 already governs). Both are wired into
`_KNOWN_GATE_RULES`.

New `frob registry audit` CLI subcommand (`src/frob/app/registry_runner.py`,
wired through `AppConfig`/`Subcommand`/`app.py`'s dispatch table the same way
every other uniform runner is) reports the per-file
handled/deferred/duplicate/out_of_scope/unaccounted/malformed accounting
against `total`, so "is this registry exhausted" is a direct read, not a
re-derivation from the violation list. Ran against the real registry: all 9
files report EXHAUSTED (matches T-0426's "backlog fully drained" claim).

Confirmed no early-exit/partial-coverage regression against the real
1950-entry registry: `frob check --ticket T-0407` on the live
`docs/design/registry/*.yaml` tree shows 0 REG violations of any kind
(REG001-REG007).

### Changed
(no changed files detected)

### Evidence
- `tests/test_registry_models.py::TestParseDisposition::test_handled_by` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestParseDisposition::test_deferred` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestParseDisposition::test_duplicate_of_underscore_and_hyphen` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestParseDisposition::test_out_of_scope_paren_form` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestParseDisposition::test_undispositioned_pending` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestParseDisposition::test_undispositioned_none` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestParseDisposition::test_undispositioned_bare_addressed` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestParseDisposition::test_undispositioned_unparseable` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestLoadRegistryDir::test_loads_typed_entries` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestLoadRegistryDir::test_absent_file_not_in_result` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestLoadRegistryDir::test_malformed_yaml_is_err` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestLoadRegistryDir::test_not_a_mapping_is_err` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestLoadRegistryDir::test_malformed_entry_counted` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestLoadRegistryDir::test_split_entries_key_total` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestAuditRegistryFile::test_counts_each_kind` (pytest node id, verified passing when recorded)
- `tests/test_registry_models.py::TestAuditRegistryFile::test_fully_dispositioned_file_is_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestMalformedEntry::test_malformed_entry_fails` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestMalformedEntry::test_entry_missing_id_fails` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestMalformedEntry::test_all_well_formed_entries_no_reg006` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestDuplicateId::test_duplicate_id_across_files_fails` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestDuplicateId::test_duplicate_id_same_file_fails` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestDuplicateId::test_no_duplicate_ids_no_reg007` (pytest node id, verified passing when recorded)
