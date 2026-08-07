## Done report

Changed:
- src/frob/strata/_report.py::render_report
- src/frob/strata/_report.py::summarize
- src/frob/strata/__init__.py (export render_report, summarize)
- docs/strata/kernel.md (## Verdict report section)
- tests/unit/strata/test_report.py (new)

Evidence:
- tests/unit/strata/test_report.py::TestCounterexamplePath::test_refuted_line_followed_by_exact_path_line
- tests/unit/strata/test_report.py::TestOrdering::test_refuted_sorts_first_regardless_of_input_order
- tests/unit/strata/test_report.py::TestSummarize::test_all_four_keys_always_present

Filed: none

Gates: `frob check --ticket T-0061` clean (exit 0; only pre-existing waived
PERF003 findings in frob-core/frob's own modules, unrelated to this
ticket's scope). `frob graph build` clean. pytest tests/unit/strata 72
passed. ruff format/check clean. ty check clean.
