## Done report

Changed:
- src/frob/serve/_tools.py::frob_perf_hot
- src/frob/serve/_tools.py::_perf_hot_sort_key
- src/frob/serve/server.py::_register_perf_tool
- src/frob/serve/server.py::build_server
- src/frob/serve/__init__.py (re-export frob_perf_hot)
- docs/modules/serve.md#tools (frob_perf_hot describes edge + prose)
- tests/test_serve.py::TestPerfHot (4 new tests)
- tests/test_serve.py::TestBuildServer.test_registers_all_five_tools (tool-name set updated to include frob_perf_hot)

Evidence:
- tests/test_serve.py::TestPerfHot::test_empty_store_is_empty_list
- tests/test_serve.py::TestPerfHot::test_ranks_by_default_p50xcount
- tests/test_serve.py::TestPerfHot::test_by_p90_ranks_by_p90_instead
- tests/test_serve.py::TestPerfHot::test_top_truncates_results
- tests/test_serve.py::TestBuildServer::test_registers_all_five_tools
- tests/integration/test_interfaces.py::TestInterfaces::test_serve_tools
- full-file check: `uv run pytest -q tests/test_serve.py` -> 37 passed
- `uv run frob test --base main` -> python exit=0, 49.01s, all selected touched-set tests pass

Filed: none (no out-of-scope discoveries)

Gates: `uv run frob check --ticket T-0917 --only <stage>` clean (0 errors)
across all four stage groups (gates-fast, gates-native, gates-security,
lint) plus `static`; scope extended twice via `frob ticket scope --add`
(tests/test_serve.py, docs/modules/serve.md) with recorded --reason, the
second required by AFFECT001 (build_server/frob_perf_hot's affects()-closure
doc).
