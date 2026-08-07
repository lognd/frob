## Done report

Changed:
- tests/unit/strata/litmus/cwe_79_vuln.strata, cwe_79_hardened.strata (CWE-79, may "html_render")
- tests/unit/strata/litmus/cwe_89_vuln.strata, cwe_89_hardened.strata (CWE-89, may "sql")
- tests/unit/strata/litmus/cwe_exec_vuln.strata, cwe_exec_hardened.strata (CWE-78 + CWE-94 shared, may "exec")
- tests/unit/strata/litmus/cwe_918_vuln.strata, cwe_918_hardened.strata (CWE-918, may "fetch_url")
- tests/unit/strata/litmus/cwe_502_vuln.strata, cwe_502_hardened.strata (CWE-502, may "deserialize")
- tests/unit/strata/litmus/cwe_922_vuln.strata, cwe_922_hardened.strata (CWE-922, may "client_storage")
- tests/unit/strata/litmus/cwe_22_unfired.strata, cwe_352_unfired.strata, cwe_798_unfired.strata (design-finding: capability_kind=None, never fire under THREAT003 -- asserted explicitly, not skipped)
- tests/unit/strata/test_litmus_cwe.py (new, 27 tests: fixture-coverage drift-lock, out-of-scope exemption exactness, parametrized firing/discharge over the union catalog, shared-exec independence, capability_kind=None non-firing)
- docs/strata/threat.md#litmus-coverage (new section: fixture-pair convention, the shared-exec join, the three-id design finding, the out-of-scope boundary proof)

Evidence: 27 node ids recorded via `frob ticket evidence T-0145 <ids>` (tests/unit/strata/test_litmus_cwe.py, all classes) -- `uv run pytest tests/unit/strata/test_litmus_cwe.py -q` -> 27 passed. Full `tests/unit/strata/` suite (528 tests) also passes unchanged.

Filed: T-0149 (frob test: no [[test.runner]] for language=strata blocks touched-set selection on .strata fixtures -- `frob test --base main` errors NoRunner when new .strata files are touched; out of T-0145's declared scope, frob.toml is not in scope). No other out-of-scope findings.

Gates: `frob check --ticket T-0145` clean -- Tool summary all `pass` (ruff-check, ruff-format, ty, frob-cycle, frob-dup, frob-arch, frob-exports x17), gates line `pass  gates  87 violation(s), 57 waived` (main baseline: 87 violations / 55 waived; the +2 waivers are `frob:waive PERF003 reason="two set comprehensions over small fixtures, not a join"` on two new test methods in test_litmus_cwe.py, matching the identical waiver already used four times in test_threat.py for the same false-positive shape -- violation COUNT unchanged from baseline, no new unwaived violations). `frob test --base main` currently errors before running (NoRunner for language=strata, T-0149) -- a pre-existing tooling gap this ticket's fixtures exposed, not a regression from this diff; verified correctness instead via direct `uv run pytest`.
