## Done report

DOC006 burn-down, decompose-then-execute: 771 findings clustered by shape; five matcher false-positive classes fixed at the matcher (enumeration lists, unit ratios, hostname/DOI rejection, directory-prefix and module-relative resolution, multi-manifest config refs), the tickets-archive verbatim-history exclusion killed the single largest cluster, and 26 genuinely illustrative citation sites got reasoned waivers -- 771 to 133, remainder fragmented across ~30 files and filed as a precise round-2 child. DOC006 stays WARN with the count evidence recorded; promotion revisits after round 2.

### Changed
```
 docs/audits/gates-quality.md               |  65 ++++++++
 docs/design/capability-evasion-taxonomy.md |  38 ++---
 docs/modules/gates.md                      |  12 +-
 src/frob/gates/_docptr.py                  | 232 ++++++++++++++++++++++++++---
 tickets.md                                 | 219 +++++++++++++++++++++++++++
 5 files changed, 521 insertions(+), 45 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006FilePath::test_missing_path_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FilePath::test_real_path_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FilePath::test_unrecognized_prose_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006FilePath::test_dot_frob_runtime_path_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006DocAnchor::test_missing_anchor_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006DocAnchor::test_real_anchor_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Cli::test_nonexistent_subcommand_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Cli::test_nonexistent_flag_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Cli::test_real_command_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_real_section_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Symbol::test_nonexistent_symbol_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Symbol::test_real_symbol_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Symbol::test_module_dunder_init_and_all_pass` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Symbol::test_class_attribute_chain_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Waive::test_waive_suppresses` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_double_separator_target_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_single_separator_target_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 18 passed (from 18 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
