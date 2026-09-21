"""Touched-set test selection and execution across languages (docs/modules/testing.md).

`frob test` is the single entry point that computes what was touched (diff
vs base), selects every test obligated to those symbols via the obligation
graph (`frob.graph`), and runs them through per-language runners -- so "run
the right tests" is one command in any repo, any language, any worktree.
This is the executable counterpart of the TEST gate family: the gates prove
the bindings exist, `frob test` runs the bound tests.
"""

from __future__ import annotations

from frob.testing._collect import (
    LANGUAGE_COLLECTORS,
    collect_cpp_tests,
    collect_csharp_tests,
    collect_kotlin_tests,
    collect_python_tests,
    collect_rust_tests,
    collect_ts_tests,
    drop_collection_cache,
    python_collection_failure_detail,
    python_collection_missing_natives,
)

# frob:ticket T-4579
# frob:tests tests/unit/test_exports.py::TestFrobExportsPolicyResidue.test_all_nine_packages_report_zero_missing_symbols kind="unit"  # noqa: E501
from frob.testing._collect_csharp import parse_csharp
from frob.testing._coverage_cache import (
    fill_from_cache,
    load_file_cache,
    update_file_cache,
)
from frob.testing._coverage_refresh import (
    CoverageRefreshError,
    native_coverage_refresh,
    pytest_load_initial_conftests,
)
from frob.testing._coverage_wait import (
    CoverageLockUnavailable,
    CoverageWaitError,
    CoverageWaitOutcome,
    SharedCoverageResult,
    coverage_lock_path,
    run_coverage_wait,
    shared_state_dir,
    tree_digest,
)
from frob.testing._dotnet_runner import run_dotnet_tests
from frob.testing._incremental_coverage import python_coverage_targets
from frob.testing._models import (
    CollectedTests,
    NativeSpec,
    RunnerOutcome,
    RunnerSpec,
    SelectConfig,
    SelectionReport,
    TestRunReport,
)
from frob.testing._runners import (
    TestingError,
    load_natives,
    load_runners,
    run_selected,
)
from frob.testing._select import extension_language, select_tests
from frob.testing._stability import (
    DEFAULT_REGRESSION_TAIL_K,
    FlakeError,
    StabilityEntry,
    capture_python_outcomes,
    evaluate_gate,
    flaky_node_ids,
    hard_regression_alarms,
    is_flaky,
    is_hard_regression,
    lift_quarantine,
    load_stability,
    quarantine,
    quarantine_alarms,
    quarantined_node_ids,
    record_outcomes,
    track_python_stability,
)
from frob.testing._stackdump import (
    STACKDUMP_ENV,
    dump_all_thread_stacks,
    install_stackdump_handler,
    write_stack_dump,
)
from frob.testing._unity_batchmode import (
    UnityBatchmodeError,
    parse_unity_batchmode_xml,
    resolve_unity_editor,
    run_unity_batchmode,
)

__all__ = [
    "CollectedTests",
    "CoverageLockUnavailable",
    "CoverageRefreshError",
    "CoverageWaitError",
    "CoverageWaitOutcome",
    "DEFAULT_REGRESSION_TAIL_K",
    "FlakeError",
    "LANGUAGE_COLLECTORS",
    "NativeSpec",
    "RunnerOutcome",
    "RunnerSpec",
    "SelectConfig",
    "SelectionReport",
    "STACKDUMP_ENV",
    "SharedCoverageResult",
    "StabilityEntry",
    "TestRunReport",
    "TestingError",
    "UnityBatchmodeError",
    "capture_python_outcomes",
    "collect_cpp_tests",
    "collect_csharp_tests",
    "collect_kotlin_tests",
    "collect_python_tests",
    "collect_rust_tests",
    "collect_ts_tests",
    "coverage_lock_path",
    "drop_collection_cache",
    "dump_all_thread_stacks",
    "evaluate_gate",
    "extension_language",
    "fill_from_cache",
    "flaky_node_ids",
    "hard_regression_alarms",
    "install_stackdump_handler",
    "is_flaky",
    "is_hard_regression",
    "lift_quarantine",
    "load_file_cache",
    "load_natives",
    "load_runners",
    "load_stability",
    "native_coverage_refresh",
    "parse_csharp",
    "parse_unity_batchmode_xml",
    "python_collection_failure_detail",
    "python_collection_missing_natives",
    "python_coverage_targets",
    "pytest_load_initial_conftests",
    "quarantine",
    "quarantine_alarms",
    "quarantined_node_ids",
    "record_outcomes",
    "resolve_unity_editor",
    "run_coverage_wait",
    "run_dotnet_tests",
    "run_selected",
    "run_unity_batchmode",
    "select_tests",
    "shared_state_dir",
    "track_python_stability",
    "tree_digest",
    "update_file_cache",
    "write_stack_dump",
]
