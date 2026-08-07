## Done report

Completes the T-0373 story. src/frob/check/_python.py::_run_arch (the
non-gate tool-summary ARCH stage) now threads
frob.app.config.load_arch_config(scan_root) into analyze_project, matching
the T-0373 fix already applied to gates/_arch.py::arch_gate. Previously the
tool-summary view silently used analyze_project's bare 30-line default while
the ARCH001 gate used the calibrated 60-line default -- the two disagreed
over identical source (the exact dead-code/double-standard class T-0373 was
about, one level up).

Evidence (2 tests, pass): test_arch_stage_uses_calibrated_default_not_library_default
and test_arch_stage_respects_explicit_frob_toml_override (mirror
tests/test_gates.py::TestArchGateThresholds at the tool-summary level).
Implemented by the easy-wins sweeper, coordinator inline-reviewed (small,
mirrors the landed T-0373 gate fix) and landed via 3-way onto main.
