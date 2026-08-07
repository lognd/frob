## Done report

Changed:
- src/frob/app/perf_runner.py::run (dispatch to collect)
- src/frob/app/perf_runner.py::_collect
- src/frob/app/perf_runner.py::_collect_body
- src/frob/app/perf_runner.py::_collect_stacks
- src/frob/app/perf_runner.py::_print_decile_rows
- src/frob/app/config.py::AppConfig (perf_file/perf_format/perf_sampler/perf_interval_s/perf_max_depth fields)
- src/frob/__main__.py::_add_perf_collect_parser
- src/frob/__main__.py::_add_perf_parser (wires collect subparser)
- src/frob/perf/_collectors.py::detect_collector_format
- src/frob/perf/_collectors.py::parse_collector_format
- src/frob/perf/_collectors.py::build_index_for_files
- src/frob/perf/_hotgraph.py::LanguageDecileRow
- src/frob/perf/_hotgraph.py::language_deciles
- src/frob/perf/_harness.py (refactored to reuse build_index_for_files, dropping the duplicate private `_sampled_section_index`)
- src/frob/perf/__init__.py (new exports)

Evidence:
- tests/unit/perf/test_collectors.py::TestDetectCollectorFormat (3 cases)
- tests/unit/perf/test_collectors.py::TestParseCollectorFormat::test_dispatches_to_the_matching_adapter (parametrized, 3 cases)
- tests/unit/perf/test_collectors.py::TestBuildIndexForFiles (2 cases)
- tests/unit/perf/test_collectors.py::TestLanguageDeciles (3 cases)
- tests/system/test_cli_perf.py::TestPerfCollect (4 cases, real CLI subprocess dispatch, covering perf-script/v8-cpuprofile autodetect/no-input-error/json-output)
- Measured: `uv run pytest tests/unit/perf/test_collectors.py tests/system/test_cli_perf.py::TestPerfCollect -q` -> 33 passed
- Measured: `uv run pytest tests/system/test_cli_perf.py::TestPerfProfileAndHeat -q` -> unaffected, still green (regression check on the sibling perf profile/heat CLI commands after the _harness.py refactor)

Filed: none

Gates: `uv run frob check --ticket T-0765 --only lint`, `--only gates-fast`, `--only gates-native`, and `--only gates-security` all clean within T-0765's scope (src/frob/app/**, src/frob/perf/**, docs/modules/perf.md, plus tests/system/test_cli_perf.py and tests/unit/perf/test_collectors.py, added via `frob ticket scope --add` since the ticket's declared scope had no tests/ globs). gates-security's one FAIL (gate:SELFAUDIT, src/frob/arch/_logging_checks.py, from T-0625) is pre-existing debt entirely outside this ticket's scope -- confirmed via `git log --oneline -1 -- src/frob/arch/_logging_checks.py` (last touched by T-0625, unrelated to perf).

Also fixed, all within declared scope, while driving the ticket-scoped gate check clean:
- added missing frob:ticket edges (COV002) on `__main__.py`'s `_add_perf_parser`
- fixed two DRIFT002 findings: `language_deciles`'s frob:tests directive pointed at the wrong test file (test_hotgraph.py instead of test_collectors.py, where its test class actually lives); `_collect_body` had a redundant source-side frob:tests directive that a subprocess-spawned system test can never satisfy via call-graph reachability -- removed it, since this repo's established convention for CLI system tests is the test-side `# frob:tests <source>::run` comment already present in the test method (matching the existing `TestPerfProfileAndHeat` precedent), not a source-side one
- added `kind="unit"` tags to TEST002-flagged class-level frob:tests directives in `_collectors.py` (both the pre-existing T-0748 ones and this ticket's new ones)
- waived INV006's exclusivity-vocabulary false positive on the perf module docstrings using this repo's established T-0585 disposal pattern (5 files: `_harness.py`, `_sampler.py`, `_collectors.py`, `_hotgraph.py`, `perf_runner.py`)
