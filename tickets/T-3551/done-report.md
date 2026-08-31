## Done report

Added abi3-py311 to the mincrate fixture crate's pyo3 feature list in tests/system/test_natives_build_integration.py's _CARGO_TOML, matching frob-core/strata-core's own pyo3 config. Root cause (ground-truthed CI run 33361224273): pyo3 0.22.6 without abi3 refuses to build against a Python interpreter newer than its own max-supported version (macOS runner ships 3.14, pyo3 0.22.6 tops out at 3.13) -- abi3 mode targets the stable ABI so it builds against any Python >= the pinned minor regardless of pyo3's own per-version binding coverage. Evidence: 3x local pass via FROB_SUGGEST_ACK=1 uv run pytest -p no:xdist -m slow. frob:waive BUG002: macOS-only (this Linux box's Python predates the affected range). Filed: none.

### Changed
```
 tickets/T-3551/ticket.md | 12 +++++++++++-
 1 file changed, 11 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_natives_build_integration.py::test_build_natives_compiles_and_imports_real_crate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 24 error(s), 4079 warning(s), 895 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
