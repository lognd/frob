## Done report

Added "protocol_summary" to the "gates-security" _STAGE_GROUPS alias in
src/frob/check/__init__.py. protocol_summary is a process-pool gate
(frob.gates._protocol_summary.protocol_summary_gate, dispatched via
_ProcessJob same as dead_symbol_gate) and dead_symbols is already the
process-pool sibling living in gates-security, so protocol_summary belongs
in the same bucket rather than gates-native (archgate/clones/perf) or
gates-fast (thread-pool/cheap gates).

Filed: none
Gates: frob check --ticket T-0824 clean; frob check --only gates-security
clean (protocol_summary=0.71s, in budget alongside dead_symbols=3.65s)

### Changed
(no changed files detected)

### Evidence
- `tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool` (pytest node id, verified passing when recorded)
